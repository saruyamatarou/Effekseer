from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from effekseer_mcp import smoke_recipes
from effekseer_mcp.smoke_bridge import SmokeBridgeError


class FakeRecipeSmokeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def get_bridge_capabilities(self) -> dict[str, Any]:
        self.calls.append(("get_bridge_capabilities", ()))
        return {
            "ok": True,
            "result": {
                "commands": sorted(
                    smoke_recipes.RECIPE_SMOKE_REQUIRED_COMMANDS
                    | smoke_recipes.RECIPE_SMOKE_VISUAL_COMMANDS
                )
            },
        }

    def get_workspace_status(self) -> dict[str, Any]:
        self.calls.append(("get_workspace_status", ()))
        return {"ok": True, "result": {"enabled": True, "exists": True}}

    def get_node_tree(self) -> dict[str, Any]:
        self.calls.append(("get_node_tree", ()))
        return {
            "ok": True,
            "result": {
                "root": {
                    "automationNodeId": "root",
                    "name": "Root",
                    "children": [],
                }
            },
        }

    def remove_node_by_automation_id(self, automation_node_id: str) -> dict[str, Any]:
        self.calls.append(("remove_node_by_automation_id", (automation_node_id,)))
        return {"ok": True, "result": {"automationNodeId": automation_node_id}}

    def open_project_from_workspace(self, path: str) -> dict[str, Any]:
        self.calls.append(("open_project_from_workspace", (path,)))
        return {"ok": True, "result": {"path": path}}

    def stop_viewer(self) -> dict[str, Any]:
        self.calls.append(("stop_viewer", ()))
        return {"ok": True}

    def play_viewer(self) -> dict[str, Any]:
        self.calls.append(("play_viewer", ()))
        return {"ok": True}


def fake_recipe_result(spec: dict[str, Any]) -> dict[str, Any]:
    recipe_by_kind = {
        "firework": "firework_burst",
        "wind_slash": "slash",
        "holy_heal": "heal_sparkle",
        "fire": "elemental_burst",
        "water_projectile": "projectile_trail",
    }
    element_by_kind = {
        "wind_slash": "wind",
        "fire": "fire",
        "water_projectile": "water",
    }
    label = Path(spec["output_project_path"]).stem
    result: dict[str, Any] = {
        "project_path": spec["output_project_path"],
        "effect_path": spec["output_effect_path"],
        "recipe": recipe_by_kind[spec["kind"]],
        "automationNodeId": f"{label}-root",
        "nodes": {"root": f"{label}-root"},
        "commands": [{"command": "fake"}],
        "sample_tuning": {
            "enabled": True,
            "mode": "auto",
            "category": "projectile",
            "baseline_source": "fallback",
            "applied_multipliers": {"radius": 0.32, "velocity": 0.38},
        },
    }
    if spec["kind"] in element_by_kind:
        result["element"] = element_by_kind[spec["kind"]]
    return result


def test_build_representative_specs_uses_expected_cases_and_paths() -> None:
    cases = smoke_recipes.build_representative_specs("abcd1234")

    assert [case.label for case in cases] == [
        "firework_burst",
        "wind_slash",
        "holy_heal",
        "elemental_fire",
        "water_projectile",
    ]
    assert [case.spec["kind"] for case in cases] == [
        "firework",
        "wind_slash",
        "holy_heal",
        "fire",
        "water_projectile",
    ]
    assert all(
        case.spec["output_project_path"].startswith(
            "outputs/recipe_smoke_abcd1234/"
        )
        for case in cases
    )
    assert all(case.spec["texture_set"] == "builtin" for case in cases)
    assert all(case.spec["sample_tuning"] == "auto" for case in cases)


def test_build_representative_specs_can_disable_sample_tuning() -> None:
    cases = smoke_recipes.build_representative_specs(
        "abcd1234",
        sample_tuning="off",
    )

    assert all(case.spec["sample_tuning"] == "off" for case in cases)


def test_run_recipe_smoke_generates_manifest_and_review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeRecipeSmokeClient()
    recipe_calls: list[dict[str, Any]] = []

    def fake_create_effect_from_spec(
        spec: dict[str, Any],
        *,
        client: Any | None = None,
    ) -> dict[str, Any]:
        recipe_calls.append({"spec": spec, "client": client})
        return fake_recipe_result(spec)

    monkeypatch.setattr(
        smoke_recipes,
        "create_effect_from_spec",
        fake_create_effect_from_spec,
    )

    result = smoke_recipes.run_recipe_smoke(
        client=client,
        workspace=tmp_path,
        run_id="run00001",
        print_func=lambda _: None,
    )

    assert len(recipe_calls) == 5
    assert all(call["client"] is client for call in recipe_calls)
    assert result["manifest_path"] == "outputs/recipe_smoke_run00001/manifest.json"
    assert result["review_path"] == "outputs/recipe_smoke_run00001/REVIEW.md"
    assert (
        tmp_path / "inputs/textures/builtin/texture_manifest.json"
    ).exists()
    assert not any(
        call[0] in {"open_project_from_workspace", "play_viewer"}
        for call in client.calls
    )
    assert [
        call for call in client.calls if call[0] == "remove_node_by_automation_id"
    ] == [
        ("remove_node_by_automation_id", ("firework_burst-root",)),
        ("remove_node_by_automation_id", ("wind_slash-root",)),
        ("remove_node_by_automation_id", ("holy_heal-root",)),
        ("remove_node_by_automation_id", ("elemental_fire-root",)),
        ("remove_node_by_automation_id", ("water_projectile-root",)),
    ]

    manifest_path = tmp_path / result["manifest_path"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_id"] == "run00001"
    assert manifest["bridge_status"] == {"enabled": True, "exists": True}
    assert [entry["label"] for entry in manifest["recipes"]] == [
        "firework_burst",
        "wind_slash",
        "holy_heal",
        "elemental_fire",
        "water_projectile",
    ]
    assert manifest["recipes"][-1] == {
        "label": "water_projectile",
        "kind": "water_projectile",
        "project_path": "outputs/recipe_smoke_run00001/water_projectile.efkefc",
        "effect_path": "outputs/recipe_smoke_run00001/water_projectile.efk",
            "recipe": "projectile_trail",
            "texture_set": "builtin",
            "visual_profile": "projectile_water_default",
            "sample_tuning": {
                "enabled": True,
                "mode": "auto",
                "category": "projectile",
                "baseline_source": "fallback",
                "applied_multipliers": {"radius": 0.32, "velocity": 0.38},
            },
            "nodes": {"root": "water_projectile-root"},
            "command_count": 1,
            "element": "water",
    }

    review = (tmp_path / result["review_path"]).read_text(encoding="utf-8")
    assert "Texture set: `builtin`" in review
    assert "Sample tuning: `auto` category `projectile` from `fallback`" in review
    assert "Firework: 中心から粒子が広がるか" in review
    assert "Wind Slash: 斜めの斬撃と小さい粒子が見えるか" in review
    assert "Holy Heal: 柔らかい光、上昇する粒子、リングが見えるか" in review
    assert "Elemental Fire: 中心光と火属性っぽい粒子が見えるか" in review
    assert "Water Projectile: 弾の中心、軌跡、着弾粒子が見えるか" in review


def test_run_recipe_smoke_visual_opens_projects_in_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeRecipeSmokeClient()
    prompts: list[str] = []

    monkeypatch.setattr(
        smoke_recipes,
        "create_effect_from_spec",
        lambda spec, *, client=None: fake_recipe_result(spec),
    )

    smoke_recipes.run_recipe_smoke(
        client=client,
        workspace=tmp_path,
        run_id="visual01",
        visual=True,
        input_func=lambda prompt: prompts.append(prompt) or "",
        print_func=lambda _: None,
    )

    visual_calls = [
        call
        for call in client.calls
        if call[0] in {"open_project_from_workspace", "play_viewer", "stop_viewer"}
    ]
    assert visual_calls == [
        ("stop_viewer", ()),
        (
            "open_project_from_workspace",
            ("outputs/recipe_smoke_visual01/firework_burst.efkefc",),
        ),
        ("stop_viewer", ()),
        ("play_viewer", ()),
        ("stop_viewer", ()),
        ("stop_viewer", ()),
        (
            "open_project_from_workspace",
            ("outputs/recipe_smoke_visual01/wind_slash.efkefc",),
        ),
        ("stop_viewer", ()),
        ("play_viewer", ()),
        ("stop_viewer", ()),
        ("stop_viewer", ()),
        (
            "open_project_from_workspace",
            ("outputs/recipe_smoke_visual01/holy_heal.efkefc",),
        ),
        ("stop_viewer", ()),
        ("play_viewer", ()),
        ("stop_viewer", ()),
        ("stop_viewer", ()),
        (
            "open_project_from_workspace",
            ("outputs/recipe_smoke_visual01/elemental_fire.efkefc",),
        ),
        ("stop_viewer", ()),
        ("play_viewer", ()),
        ("stop_viewer", ()),
        ("stop_viewer", ()),
        (
            "open_project_from_workspace",
            ("outputs/recipe_smoke_visual01/water_projectile.efkefc",),
        ),
        ("stop_viewer", ()),
        ("play_viewer", ()),
        ("stop_viewer", ()),
    ]
    assert len(prompts) == 5


def test_run_recipe_smoke_fails_when_capabilities_are_missing(tmp_path: Path) -> None:
    class MissingCapabilityClient(FakeRecipeSmokeClient):
        def get_bridge_capabilities(self) -> dict[str, Any]:
            self.calls.append(("get_bridge_capabilities", ()))
            commands = sorted(
                smoke_recipes.RECIPE_SMOKE_REQUIRED_COMMANDS
                - {"export_runtime_effect_to_workspace"}
            )
            return {"ok": True, "result": {"commands": commands}}

    with pytest.raises(SmokeBridgeError, match="Bridge is missing required commands"):
        smoke_recipes.run_recipe_smoke(
            client=MissingCapabilityClient(),
            workspace=tmp_path,
            run_id="missing1",
            print_func=lambda _: None,
        )


def test_required_commands_include_cleanup_and_visual_stop() -> None:
    assert "set_node_is_rendered_by_automation_id" in (
        smoke_recipes.RECIPE_SMOKE_REQUIRED_COMMANDS
    )
    assert "remove_node_by_automation_id" in smoke_recipes.RECIPE_SMOKE_REQUIRED_COMMANDS
    assert "stop_viewer" not in smoke_recipes.required_commands_for_visual(False)
    assert "stop_viewer" in smoke_recipes.required_commands_for_visual(True)


def test_cleanup_previous_smoke_nodes_removes_only_fixed_smoke_names() -> None:
    class CleanupClient(FakeRecipeSmokeClient):
        def __init__(self) -> None:
            super().__init__()
            self.trees = [
                {
                    "root": {
                        "automationNodeId": "root",
                        "name": "Root",
                        "children": [
                            {
                                "automationNodeId": "legacy-firework",
                                "name": "SmokeFirework",
                            },
                            {
                                "automationNodeId": "user-node",
                                "name": "UserNode",
                            },
                        ],
                    }
                },
                {
                    "root": {
                        "automationNodeId": "root",
                        "name": "Root",
                        "children": [
                            {
                                "automationNodeId": "legacy-water",
                                "name": "SmokeWaterProjectile",
                            },
                            {
                                "automationNodeId": "user-smoke-like",
                                "name": "SmokeCustom",
                            },
                        ],
                    }
                },
                {
                    "root": {
                        "automationNodeId": "root",
                        "name": "Root",
                        "children": [
                            {
                                "automationNodeId": "user-node",
                                "name": "UserNode",
                            }
                        ],
                    }
                },
            ]

        def get_node_tree(self) -> dict[str, Any]:
            self.calls.append(("get_node_tree", ()))
            return self.trees.pop(0)

    client = CleanupClient()

    smoke_recipes.cleanup_previous_smoke_nodes(client, print_func=lambda _: None)

    assert [
        call for call in client.calls if call[0] == "remove_node_by_automation_id"
    ] == [
        ("remove_node_by_automation_id", ("legacy-firework",)),
        ("remove_node_by_automation_id", ("legacy-water",)),
    ]


def test_build_review_markdown_contains_checklist() -> None:
    markdown = smoke_recipes.build_review_markdown(
        "review01",
        smoke_recipes.build_representative_specs("review01"),
    )

    assert "# Recipe Smoke Review review01" in markdown
    assert "Texture set: `builtin`" in markdown
    assert "- [ ] Firework: 中心から粒子が広がるか" in markdown
    assert "outputs/recipe_smoke_review01/water_projectile.efk" in markdown

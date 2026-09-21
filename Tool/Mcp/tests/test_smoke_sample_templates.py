from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from effekseer_mcp import smoke_sample_templates
from effekseer_mcp.smoke_bridge import SmokeBridgeError


class FakeSampleSmokeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def get_bridge_capabilities(self) -> dict[str, Any]:
        self.calls.append(("get_bridge_capabilities", ()))
        return {
            "ok": True,
            "result": {
                "commands": sorted(
                    smoke_sample_templates.SAMPLE_SMOKE_REQUIRED_COMMANDS
                    | smoke_sample_templates.SAMPLE_SMOKE_VISUAL_COMMANDS
                )
            },
        }

    def get_workspace_status(self) -> dict[str, Any]:
        self.calls.append(("get_workspace_status", ()))
        return {"ok": True, "result": {"enabled": True, "exists": True}}

    def open_project_from_workspace(self, path: str) -> dict[str, Any]:
        self.calls.append(("open_project_from_workspace", (path,)))
        return {"ok": True, "result": {"path": path}}

    def export_runtime_effect_to_workspace(self, path: str) -> dict[str, Any]:
        self.calls.append(("export_runtime_effect_to_workspace", (path,)))
        return {"ok": True, "result": {"path": path, "bytes": 10}}

    def stop_viewer(self) -> dict[str, Any]:
        self.calls.append(("stop_viewer", ()))
        return {"ok": True}

    def play_viewer(self) -> dict[str, Any]:
        self.calls.append(("play_viewer", ()))
        return {"ok": True}


def fake_templates() -> list[dict[str, Any]]:
    return [
        {"sample_id": "fireball", "display_name": "FireBall"},
        {"sample_id": "magicheal1", "display_name": "MagicHeal1"},
        {"sample_id": "magicwater", "display_name": "MagicWater"},
        {"sample_id": "magicthunder", "display_name": "MagicThunder"},
        {"sample_id": "attack1", "display_name": "Attack1"},
    ]


def fake_sample_result(
    sample_id: str,
    output_project_path: str,
    output_effect_path: str,
    *,
    client: Any | None = None,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    del workspace
    if client is not None:
        client.open_project_from_workspace(output_project_path)
        client.export_runtime_effect_to_workspace(output_effect_path)
    return {
        "sample_id": sample_id,
        "display_name": sample_id,
        "project_path": output_project_path,
        "effect_path": output_effect_path,
        "copied_assets": [f"outputs/sample_smoke_run00001/{sample_id}/Parts"],
        "commands": [
            {"command": "open_project_from_workspace"},
            {"command": "export_runtime_effect_to_workspace"},
        ],
    }


def test_build_representative_sample_cases_selects_expected_templates() -> None:
    cases = smoke_sample_templates.build_representative_sample_cases(
        fake_templates(),
        "abcd1234",
    )

    assert [case.sample_id for case in cases] == [
        "fireball",
        "magicheal1",
        "magicwater",
        "magicthunder",
        "attack1",
    ]
    assert cases[0].output_project_path == (
        "outputs/sample_smoke_abcd1234/fireball.efkproj"
    )
    assert cases[0].output_effect_path == "outputs/sample_smoke_abcd1234/fireball.efk"


def test_run_sample_template_smoke_generates_manifest_and_review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeSampleSmokeClient()

    monkeypatch.setattr(
        smoke_sample_templates,
        "ensure_sample_templates_imported",
        lambda workspace, *, print_func: fake_templates(),
    )
    monkeypatch.setattr(
        smoke_sample_templates,
        "create_effect_from_sample_template",
        fake_sample_result,
    )

    result = smoke_sample_templates.run_sample_template_smoke(
        client=client,
        workspace=tmp_path,
        run_id="run00001",
        print_func=lambda _: None,
    )

    assert result["manifest_path"] == "outputs/sample_smoke_run00001/manifest.json"
    assert result["review_path"] == "outputs/sample_smoke_run00001/REVIEW.md"
    assert [
        call for call in client.calls if call[0] == "open_project_from_workspace"
    ] == [
        ("open_project_from_workspace", ("outputs/sample_smoke_run00001/fireball.efkproj",)),
        ("open_project_from_workspace", ("outputs/sample_smoke_run00001/magicheal1.efkproj",)),
        ("open_project_from_workspace", ("outputs/sample_smoke_run00001/magicwater.efkproj",)),
        ("open_project_from_workspace", ("outputs/sample_smoke_run00001/magicthunder.efkproj",)),
        ("open_project_from_workspace", ("outputs/sample_smoke_run00001/attack1.efkproj",)),
    ]
    assert not any(call[0] in {"stop_viewer", "play_viewer"} for call in client.calls)

    manifest = json.loads((tmp_path / result["manifest_path"]).read_text("utf-8"))
    assert manifest["run_id"] == "run00001"
    assert [entry["sample_id"] for entry in manifest["samples"]] == [
        "fireball",
        "magicheal1",
        "magicwater",
        "magicthunder",
        "attack1",
    ]
    assert manifest["samples"][0]["command_count"] == 2
    review = (tmp_path / result["review_path"]).read_text("utf-8")
    assert "SampleEffects Smoke Review run00001" in review
    assert "FireBall" in review


def test_run_sample_template_smoke_visual_opens_projects_in_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeSampleSmokeClient()
    prompts: list[str] = []

    monkeypatch.setattr(
        smoke_sample_templates,
        "ensure_sample_templates_imported",
        lambda workspace, *, print_func: fake_templates()[:2],
    )
    monkeypatch.setattr(
        smoke_sample_templates,
        "create_effect_from_sample_template",
        fake_sample_result,
    )

    smoke_sample_templates.run_sample_template_smoke(
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
        if call[0] in {"open_project_from_workspace", "stop_viewer", "play_viewer"}
    ]
    assert visual_calls[-10:] == [
        ("stop_viewer", ()),
        ("open_project_from_workspace", ("outputs/sample_smoke_visual01/fireball.efkproj",)),
        ("stop_viewer", ()),
        ("play_viewer", ()),
        ("stop_viewer", ()),
        ("stop_viewer", ()),
        ("open_project_from_workspace", ("outputs/sample_smoke_visual01/magicheal1.efkproj",)),
        ("stop_viewer", ()),
        ("play_viewer", ()),
        ("stop_viewer", ()),
    ]
    assert len(prompts) == 2


def test_run_sample_template_smoke_fails_when_capabilities_are_missing(
    tmp_path: Path,
) -> None:
    class MissingCapabilityClient(FakeSampleSmokeClient):
        def get_bridge_capabilities(self) -> dict[str, Any]:
            self.calls.append(("get_bridge_capabilities", ()))
            commands = sorted(
                smoke_sample_templates.SAMPLE_SMOKE_REQUIRED_COMMANDS
                - {"export_runtime_effect_to_workspace"}
            )
            return {"ok": True, "result": {"commands": commands}}

    with pytest.raises(SmokeBridgeError, match="Bridge is missing required commands"):
        smoke_sample_templates.run_sample_template_smoke(
            client=MissingCapabilityClient(),
            workspace=tmp_path,
            run_id="missing1",
            print_func=lambda _: None,
        )

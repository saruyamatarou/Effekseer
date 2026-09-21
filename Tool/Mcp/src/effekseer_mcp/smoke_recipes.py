from __future__ import annotations

import argparse
import json
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from effekseer_mcp.bridge_client import EffekseerBridgeClient
from effekseer_mcp.config import load_config
from effekseer_mcp.paths import ensure_workspace_path
from effekseer_mcp.recipes import create_effect_from_spec
from effekseer_mcp.smoke_bridge import (
    SmokeBridgeError,
    assert_bridge_capabilities,
    assert_workspace_status,
    unwrap_bridge_result,
)
from effekseer_mcp.texture_library import BUILTIN_TEXTURE_SET, ensure_builtin_textures

RECIPE_SMOKE_REQUIRED_COMMANDS = frozenset(
    {
        "get_bridge_capabilities",
        "get_workspace_status",
        "get_node_tree",
        "add_node_to_parent_by_automation_id",
        "set_node_renderer_type_by_automation_id",
        "set_node_max_generation_by_automation_id",
        "set_node_life_by_automation_id",
        "set_node_fixed_rotation_by_automation_id",
        "set_node_fixed_scale_by_automation_id",
        "set_node_generation_time_by_automation_id",
        "set_node_location_type_by_automation_id",
        "set_node_location_pva_by_automation_id",
        "set_node_scale_type_by_automation_id",
        "set_node_scale_pva_by_automation_id",
        "set_node_fade_in_out_by_automation_id",
        "set_node_color_all_fixed_rgba_by_automation_id",
        "set_node_is_rendered_by_automation_id",
        "set_node_alpha_blend_by_automation_id",
        "set_node_color_texture_from_workspace_by_automation_id",
        "remove_node_by_automation_id",
        "save_project_to_workspace",
        "export_runtime_effect_to_workspace",
    }
)
RECIPE_SMOKE_VISUAL_COMMANDS = frozenset(
    {
        "open_project_from_workspace",
        "play_viewer",
        "stop_viewer",
    }
)
SMOKE_TOP_LEVEL_NAMES = frozenset(
    {
        "SmokeFirework",
        "SmokeWindSlash",
        "SmokeHolyHeal",
        "SmokeElementalFire",
        "SmokeWaterProjectile",
    }
)


@dataclass(frozen=True)
class RecipeSmokeCase:
    label: str
    review_title: str
    review_prompt: str
    spec: dict[str, Any]


def build_representative_specs(
    run_id: str,
    *,
    sample_tuning: str = "auto",
) -> list[RecipeSmokeCase]:
    """Build representative recipe smoke cases with workspace-relative outputs."""
    output_dir = f"outputs/recipe_smoke_{run_id}"
    return [
        RecipeSmokeCase(
            label="firework_burst",
            review_title="Firework",
            review_prompt="中心から粒子が広がるか",
            spec={
                "kind": "firework",
                "name": "SmokeFirework",
                "output_project_path": f"{output_dir}/firework_burst.efkefc",
                "output_effect_path": f"{output_dir}/firework_burst.efk",
                "primary_color": {"r": 255, "g": 64, "b": 48, "a": 255},
                "secondary_color": {"r": 255, "g": 210, "b": 80, "a": 220},
                "intensity": 1.0,
                "scale": 1.0,
                "duration": 45,
                "texture_path": None,
                "texture_set": BUILTIN_TEXTURE_SET,
                "visual_profile": "firework_default",
                "sample_tuning": sample_tuning,
            },
        ),
        RecipeSmokeCase(
            label="wind_slash",
            review_title="Wind Slash",
            review_prompt="斜めの斬撃と小さい粒子が見えるか",
            spec={
                "kind": "wind_slash",
                "name": "SmokeWindSlash",
                "output_project_path": f"{output_dir}/wind_slash.efkefc",
                "output_effect_path": f"{output_dir}/wind_slash.efk",
                "primary_color": {"r": 64, "g": 220, "b": 255, "a": 255},
                "secondary_color": {"r": 245, "g": 255, "b": 255, "a": 180},
                "intensity": 1.0,
                "scale": 1.0,
                "duration": 30,
                "texture_path": None,
                "texture_set": BUILTIN_TEXTURE_SET,
                "visual_profile": "slash_wind_default",
                "sample_tuning": sample_tuning,
            },
        ),
        RecipeSmokeCase(
            label="holy_heal",
            review_title="Holy Heal",
            review_prompt="柔らかい光、上昇する粒子、リングが見えるか",
            spec={
                "kind": "holy_heal",
                "name": "SmokeHolyHeal",
                "output_project_path": f"{output_dir}/holy_heal.efkefc",
                "output_effect_path": f"{output_dir}/holy_heal.efk",
                "primary_color": {"r": 255, "g": 220, "b": 96, "a": 255},
                "secondary_color": {"r": 160, "g": 255, "b": 210, "a": 180},
                "intensity": 1.0,
                "scale": 1.0,
                "duration": 45,
                "texture_path": None,
                "texture_set": BUILTIN_TEXTURE_SET,
                "visual_profile": "heal_soft_default",
                "sample_tuning": sample_tuning,
            },
        ),
        RecipeSmokeCase(
            label="elemental_fire",
            review_title="Elemental Fire",
            review_prompt="中心光と火属性っぽい粒子が見えるか",
            spec={
                "kind": "fire",
                "name": "SmokeElementalFire",
                "output_project_path": f"{output_dir}/elemental_fire.efkefc",
                "output_effect_path": f"{output_dir}/elemental_fire.efk",
                "primary_color": {"r": 255, "g": 120, "b": 32, "a": 255},
                "secondary_color": {"r": 255, "g": 32, "b": 24, "a": 180},
                "intensity": 1.0,
                "scale": 1.0,
                "duration": 40,
                "texture_path": None,
                "texture_set": BUILTIN_TEXTURE_SET,
                "visual_profile": "elemental_fire_default",
                "sample_tuning": sample_tuning,
            },
        ),
        RecipeSmokeCase(
            label="water_projectile",
            review_title="Water Projectile",
            review_prompt="弾の中心、軌跡、着弾粒子が見えるか",
            spec={
                "kind": "water_projectile",
                "name": "SmokeWaterProjectile",
                "output_project_path": f"{output_dir}/water_projectile.efkefc",
                "output_effect_path": f"{output_dir}/water_projectile.efk",
                "primary_color": {"r": 48, "g": 132, "b": 255, "a": 255},
                "secondary_color": {"r": 96, "g": 235, "b": 255, "a": 180},
                "intensity": 1.0,
                "scale": 1.0,
                "duration": 45,
                "texture_path": None,
                "texture_set": BUILTIN_TEXTURE_SET,
                "visual_profile": "projectile_water_default",
                "sample_tuning": sample_tuning,
            },
        ),
    ]


def required_commands_for_visual(visual: bool) -> frozenset[str]:
    if visual:
        return RECIPE_SMOKE_REQUIRED_COMMANDS | RECIPE_SMOKE_VISUAL_COMMANDS
    return RECIPE_SMOKE_REQUIRED_COMMANDS


def run_recipe_smoke(
    *,
    client: Any | None = None,
    workspace: str | Path | None = None,
    run_id: str | None = None,
    visual: bool = False,
    sample_tuning: str = "auto",
    input_func: Callable[[str], str] = input,
    print_func: Callable[[str], None] = print,
) -> dict[str, Any]:
    """Generate representative recipe outputs and optional visual review playback."""
    bridge = client or EffekseerBridgeClient()
    actual_run_id = run_id or uuid.uuid4().hex[:8]
    workspace_path = Path(workspace) if workspace is not None else load_config().workspace
    output_dir = ensure_workspace_path(
        f"outputs/recipe_smoke_{actual_run_id}",
        workspace_path,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    print_func("[recipe-smoke] ensure builtin textures")
    ensure_builtin_textures(workspace_path)

    print_func("[recipe-smoke] get_bridge_capabilities")
    assert_bridge_capabilities(
        bridge.get_bridge_capabilities(),
        required_commands_for_visual(visual),
    )

    print_func("[recipe-smoke] get_workspace_status")
    workspace_status_response = bridge.get_workspace_status()
    assert_workspace_status(workspace_status_response)
    workspace_status = unwrap_bridge_result(workspace_status_response)

    print_func("[recipe-smoke] cleanup previous smoke nodes")
    cleanup_previous_smoke_nodes(bridge, print_func=print_func)

    cases = build_representative_specs(actual_run_id, sample_tuning=sample_tuning)
    entries: list[dict[str, Any]] = []
    for case in cases:
        print_func(f"[recipe-smoke] create_effect_from_spec {case.label}")
        result = create_effect_from_spec(case.spec, client=bridge)
        entries.append(build_manifest_entry(case, result))
        remove_created_recipe_node(bridge, case, result)

    manifest = {
        "run_id": actual_run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "bridge_status": summarize_bridge_status(workspace_status),
        "recipes": entries,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    review_path = output_dir / "REVIEW.md"
    review_path.write_text(
        build_review_markdown(actual_run_id, cases, entries),
        encoding="utf-8",
    )

    if visual:
        run_visual_review(
            bridge=bridge,
            cases=cases,
            entries=entries,
            input_func=input_func,
            print_func=print_func,
        )

    print_func(f"[recipe-smoke] wrote {relative_workspace_path(manifest_path, workspace_path)}")
    print_func(f"[recipe-smoke] wrote {relative_workspace_path(review_path, workspace_path)}")
    return {
        "run_id": actual_run_id,
        "output_dir": f"outputs/recipe_smoke_{actual_run_id}",
        "manifest_path": f"outputs/recipe_smoke_{actual_run_id}/manifest.json",
        "review_path": f"outputs/recipe_smoke_{actual_run_id}/REVIEW.md",
        "manifest": manifest,
    }


def build_manifest_entry(case: RecipeSmokeCase, result: dict[str, Any]) -> dict[str, Any]:
    entry = {
        "label": case.label,
        "kind": case.spec["kind"],
        "project_path": result.get("project_path"),
        "effect_path": result.get("effect_path"),
        "recipe": result.get("recipe"),
        "texture_set": case.spec.get("texture_set"),
        "visual_profile": case.spec.get("visual_profile"),
        "nodes": result.get("nodes", {}),
        "command_count": len(result.get("commands", [])),
    }
    if "sample_tuning" in result:
        entry["sample_tuning"] = result.get("sample_tuning")
    element = result.get("element")
    if isinstance(element, str):
        entry["element"] = element
    return entry


def summarize_bridge_status(status: dict[str, Any]) -> dict[str, Any]:
    return {
        key: status[key]
        for key in ("enabled", "exists")
        if key in status
    }


def remove_created_recipe_node(
    bridge: Any,
    case: RecipeSmokeCase,
    result: dict[str, Any],
) -> None:
    automation_node_id = result.get("automationNodeId")
    if not isinstance(automation_node_id, str) or not automation_node_id:
        raise SmokeBridgeError(f"{case.label} result did not include automationNodeId")
    bridge.remove_node_by_automation_id(automation_node_id)


def cleanup_previous_smoke_nodes(
    bridge: Any,
    *,
    print_func: Callable[[str], None],
) -> None:
    while True:
        tree = bridge.get_node_tree()
        smoke_node = find_first_named_node(tree, SMOKE_TOP_LEVEL_NAMES)
        if smoke_node is None:
            return
        automation_node_id = smoke_node.get("automationNodeId")
        name = smoke_node.get("name")
        if not isinstance(automation_node_id, str) or not automation_node_id:
            return
        print_func(f"[recipe-smoke] remove leftover {name}")
        bridge.remove_node_by_automation_id(automation_node_id)


def find_first_named_node(
    payload: Any,
    names: frozenset[str],
) -> dict[str, Any] | None:
    if isinstance(payload, dict):
        name = payload.get("name")
        automation_node_id = payload.get("automationNodeId")
        if (
            isinstance(name, str)
            and name in names
            and isinstance(automation_node_id, str)
            and automation_node_id
        ):
            return payload
        for value in payload.values():
            found = find_first_named_node(value, names)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = find_first_named_node(item, names)
            if found is not None:
                return found
    return None


def build_review_markdown(
    run_id: str,
    cases: Sequence[RecipeSmokeCase],
    entries: Sequence[dict[str, Any]] | None = None,
) -> str:
    entries_by_label = {
        entry["label"]: entry
        for entry in entries or []
        if isinstance(entry.get("label"), str)
    }
    lines = [
        f"# Recipe Smoke Review {run_id}",
        "",
        f"Texture set: `{BUILTIN_TEXTURE_SET}`",
        "",
        "Effekseer Editor で各 project を開き、以下を目視確認してください。",
        "",
        "## Checklist",
        "",
    ]
    for case in cases:
        tuning_lines = describe_tuning_for_review(
            entries_by_label.get(case.label, {}),
            case,
        )
        lines.extend(
            [
                f"- [ ] {case.review_title}: {case.review_prompt}",
                f"  - Visual profile: `{case.spec.get('visual_profile')}`",
                f"  - Texture set: `{case.spec.get('texture_set')}`",
                *tuning_lines,
                f"  - Project: `{case.spec['output_project_path']}`",
                f"  - Runtime: `{case.spec['output_effect_path']}`",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def describe_tuning_for_review(
    entry: dict[str, Any],
    case: RecipeSmokeCase,
) -> list[str]:
    tuning = entry.get("sample_tuning")
    if not isinstance(tuning, dict):
        return [f"  - Sample tuning: `{case.spec.get('sample_tuning')}`"]
    if not tuning.get("enabled"):
        return ["  - Sample tuning: `off`"]
    multipliers = tuning.get("applied_multipliers", {})
    radius = multipliers.get("radius") if isinstance(multipliers, dict) else None
    velocity = multipliers.get("velocity") if isinstance(multipliers, dict) else None
    return [
        (
            "  - Sample tuning: "
            f"`{tuning.get('mode')}` category `{tuning.get('category')}` "
            f"from `{tuning.get('baseline_source')}`"
        ),
        f"  - Tuning multipliers: radius `{radius}`, velocity `{velocity}`",
    ]


def run_visual_review(
    *,
    bridge: Any,
    cases: Sequence[RecipeSmokeCase],
    entries: Sequence[dict[str, Any]],
    input_func: Callable[[str], str],
    print_func: Callable[[str], None],
) -> None:
    for case, entry in zip(cases, entries, strict=True):
        project_path = entry.get("project_path")
        if not isinstance(project_path, str) or not project_path:
            raise SmokeBridgeError(f"{case.label} manifest entry has no project_path")

        print_func("")
        print_func(f"[recipe-smoke] visual {case.label}")
        print_func(f"Project: {project_path}")
        print_func(f"Check: {case.review_prompt}")
        bridge.stop_viewer()
        bridge.open_project_from_workspace(project_path)
        bridge.stop_viewer()
        bridge.play_viewer()
        input_func("Press Enter to continue to the next effect...")
        bridge.stop_viewer()


def relative_workspace_path(path: Path, workspace: Path) -> str:
    return path.resolve().relative_to(workspace.resolve()).as_posix()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate representative Effekseer recipe outputs for review.",
    )
    parser.add_argument(
        "--visual",
        action="store_true",
        help="Open each generated project in Effekseer and play the viewer.",
    )
    parser.add_argument(
        "--no-sample-tuning",
        action="store_true",
        help="Disable sample-guided tuning for generated recipe specs.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        run_recipe_smoke(
            visual=args.visual,
            sample_tuning="off" if args.no_sample_tuning else "auto",
        )
    except Exception as exc:
        print(f"Recipe smoke failed: {exc}")
        return 1
    print("Recipe smoke passed")
    return 0

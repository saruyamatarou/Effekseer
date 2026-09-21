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
from effekseer_mcp.sample_library import (
    SampleLibraryError,
    create_effect_from_sample_template,
    import_sample_effects,
    list_sample_templates,
)
from effekseer_mcp.smoke_bridge import (
    SmokeBridgeError,
    assert_bridge_capabilities,
    assert_workspace_status,
    unwrap_bridge_result,
)

SAMPLE_SMOKE_REQUIRED_COMMANDS = frozenset(
    {
        "get_bridge_capabilities",
        "get_workspace_status",
        "open_project_from_workspace",
        "export_runtime_effect_to_workspace",
    }
)
SAMPLE_SMOKE_VISUAL_COMMANDS = frozenset(
    {
        "open_project_from_workspace",
        "play_viewer",
        "stop_viewer",
    }
)
REPRESENTATIVE_SAMPLE_IDS = (
    "fireball",
    "magicheal1",
    "magicheal2",
    "magicwater",
    "magicthunder",
    "attack1",
    "impact",
)


@dataclass(frozen=True)
class SampleSmokeCase:
    label: str
    sample_id: str
    display_name: str
    review_prompt: str
    output_project_path: str
    output_effect_path: str


def required_commands_for_visual(visual: bool) -> frozenset[str]:
    if visual:
        return SAMPLE_SMOKE_REQUIRED_COMMANDS | SAMPLE_SMOKE_VISUAL_COMMANDS
    return SAMPLE_SMOKE_REQUIRED_COMMANDS


def run_sample_template_smoke(
    *,
    client: Any | None = None,
    workspace: str | Path | None = None,
    run_id: str | None = None,
    visual: bool = False,
    input_func: Callable[[str], str] = input,
    print_func: Callable[[str], None] = print,
) -> dict[str, Any]:
    """Import representative SampleEffects templates, export them, and optionally play them."""
    bridge = client or EffekseerBridgeClient()
    actual_run_id = run_id or uuid.uuid4().hex[:8]
    workspace_path = Path(workspace) if workspace is not None else load_config().workspace
    output_dir = ensure_workspace_path(
        f"outputs/sample_smoke_{actual_run_id}",
        workspace_path,
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    print_func("[sample-smoke] get_bridge_capabilities")
    assert_bridge_capabilities(
        bridge.get_bridge_capabilities(),
        required_commands_for_visual(visual),
    )

    print_func("[sample-smoke] get_workspace_status")
    workspace_status_response = bridge.get_workspace_status()
    assert_workspace_status(workspace_status_response)
    workspace_status = unwrap_bridge_result(workspace_status_response)

    templates = ensure_sample_templates_imported(workspace_path, print_func=print_func)
    cases = build_representative_sample_cases(templates, actual_run_id)
    if not cases:
        raise SmokeBridgeError("no representative SampleEffects templates were found")

    entries = []
    for case in cases:
        print_func(f"[sample-smoke] create_effect_from_sample_template {case.sample_id}")
        result = create_effect_from_sample_template(
            sample_id=case.sample_id,
            output_project_path=case.output_project_path,
            output_effect_path=case.output_effect_path,
            client=bridge,
            workspace=workspace_path,
        )
        entries.append(build_manifest_entry(case, result))

    manifest = {
        "run_id": actual_run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "bridge_status": summarize_bridge_status(workspace_status),
        "samples": entries,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    review_path = output_dir / "REVIEW.md"
    review_path.write_text(build_review_markdown(actual_run_id, cases), encoding="utf-8")

    if visual:
        run_visual_review(
            bridge=bridge,
            cases=cases,
            entries=entries,
            input_func=input_func,
            print_func=print_func,
        )

    print_func(f"[sample-smoke] wrote {relative_workspace_path(manifest_path, workspace_path)}")
    print_func(f"[sample-smoke] wrote {relative_workspace_path(review_path, workspace_path)}")
    return {
        "run_id": actual_run_id,
        "output_dir": f"outputs/sample_smoke_{actual_run_id}",
        "manifest_path": f"outputs/sample_smoke_{actual_run_id}/manifest.json",
        "review_path": f"outputs/sample_smoke_{actual_run_id}/REVIEW.md",
        "manifest": manifest,
    }


def ensure_sample_templates_imported(
    workspace: Path,
    *,
    print_func: Callable[[str], None],
) -> list[dict[str, Any]]:
    try:
        templates = list_sample_templates(workspace)
    except SampleLibraryError:
        print_func("[sample-smoke] import SampleEffects")
        import_sample_effects(workspace=workspace)
        templates = list_sample_templates(workspace)
    if not templates:
        print_func("[sample-smoke] import SampleEffects")
        import_sample_effects(workspace=workspace)
        templates = list_sample_templates(workspace)
    return templates


def build_representative_sample_cases(
    templates: Sequence[dict[str, Any]],
    run_id: str,
) -> list[SampleSmokeCase]:
    by_id = {
        template["sample_id"]: template
        for template in templates
        if isinstance(template.get("sample_id"), str)
    }
    selected_ids = []
    for sample_id in REPRESENTATIVE_SAMPLE_IDS:
        if sample_id in by_id and sample_id not in selected_ids:
            selected_ids.append(sample_id)
    if "magicheal1" in selected_ids and "magicheal2" in selected_ids:
        selected_ids.remove("magicheal2")
    if "attack1" in selected_ids and "impact" in selected_ids:
        selected_ids.remove("impact")

    cases = []
    output_dir = f"outputs/sample_smoke_{run_id}"
    for sample_id in selected_ids:
        template = by_id[sample_id]
        cases.append(
            SampleSmokeCase(
                label=sample_id,
                sample_id=sample_id,
                display_name=str(template.get("display_name", sample_id)),
                review_prompt=review_prompt_for_sample(sample_id),
                output_project_path=f"{output_dir}/{sample_id}.efkproj",
                output_effect_path=f"{output_dir}/{sample_id}.efk",
            )
        )
    return cases


def review_prompt_for_sample(sample_id: str) -> str:
    prompts = {
        "fireball": "FireBall sample opens, plays, and exports as a runtime .efk.",
        "magicheal1": "MagicHeal sample shows a healing-style effect.",
        "magicheal2": "MagicHeal sample shows a healing-style effect.",
        "magicwater": "MagicWater sample shows a water-style effect.",
        "magicthunder": "MagicThunder sample shows an electric-style effect.",
        "attack1": "Attack sample shows an impact or hit-style effect.",
        "impact": "Impact sample shows an impact or hit-style effect.",
    }
    return prompts.get(sample_id, f"{sample_id} sample opens and plays.")


def build_manifest_entry(
    case: SampleSmokeCase,
    result: dict[str, Any],
) -> dict[str, Any]:
    return {
        "label": case.label,
        "sample_id": case.sample_id,
        "display_name": case.display_name,
        "project_path": result.get("project_path"),
        "effect_path": result.get("effect_path"),
        "copied_assets": result.get("copied_assets", []),
        "command_count": len(result.get("commands", [])),
    }


def summarize_bridge_status(status: dict[str, Any]) -> dict[str, Any]:
    return {
        key: status[key]
        for key in ("enabled", "exists")
        if key in status
    }


def build_review_markdown(run_id: str, cases: Sequence[SampleSmokeCase]) -> str:
    lines = [
        f"# SampleEffects Smoke Review {run_id}",
        "",
        "These projects are imported from repo-local `SampleEffects` templates.",
        "",
        "## Checklist",
        "",
    ]
    for case in cases:
        lines.extend(
            [
                f"- [ ] {case.display_name}: {case.review_prompt}",
                f"  - Sample id: `{case.sample_id}`",
                f"  - Project: `{case.output_project_path}`",
                f"  - Runtime: `{case.output_effect_path}`",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def run_visual_review(
    *,
    bridge: Any,
    cases: Sequence[SampleSmokeCase],
    entries: Sequence[dict[str, Any]],
    input_func: Callable[[str], str],
    print_func: Callable[[str], None],
) -> None:
    for case, entry in zip(cases, entries, strict=True):
        project_path = entry.get("project_path")
        if not isinstance(project_path, str) or not project_path:
            raise SmokeBridgeError(f"{case.label} manifest entry has no project_path")

        print_func("")
        print_func(f"[sample-smoke] visual {case.sample_id}")
        print_func(f"Project: {project_path}")
        print_func(f"Check: {case.review_prompt}")
        bridge.stop_viewer()
        bridge.open_project_from_workspace(project_path)
        bridge.stop_viewer()
        bridge.play_viewer()
        input_func("Press Enter to continue to the next sample...")
        bridge.stop_viewer()


def relative_workspace_path(path: Path, workspace: Path) -> str:
    return path.resolve().relative_to(workspace.resolve()).as_posix()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate representative SampleEffects template outputs for review.",
    )
    parser.add_argument(
        "--visual",
        action="store_true",
        help="Open each generated project in Effekseer and play the viewer.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        run_sample_template_smoke(visual=args.visual)
    except Exception as exc:
        print(f"Sample template smoke failed: {exc}")
        return 1
    print("Sample template smoke passed")
    return 0

from __future__ import annotations

import json
import re
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from effekseer_mcp.bridge_client import (
    EffekseerBridgeClient,
    normalize_workspace_open_project_path,
    normalize_workspace_runtime_effect_path,
)
from effekseer_mcp.paths import ensure_workspace_path, get_project_root, resolve_workspace

SAMPLE_EFFECTS_SOURCE_DIR = "SampleEffects"
SAMPLE_LIBRARY_DIR = "samples/sample_effects"
SAMPLE_MANIFEST_NAME = "sample_manifest.json"
SAMPLE_ASSET_DIR_NAMES = frozenset(
    {
        "Parts",
        "Model",
        "Texture",
        "Material",
        "Sound",
        "fbx",
        "mqo",
    }
)
SAMPLE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_SAFE_ID_CHARS = re.compile(r"[^a-z0-9]+")


class SampleLibraryError(ValueError):
    """Raised when a sample template request is invalid or unavailable."""


def build_sample_effects_manifest(repo_root: Path, workspace: Path) -> dict[str, Any]:
    """Build a manifest for imported SampleEffects without absolute paths."""
    source_dir = _sample_source_dir(repo_root)
    library_dir = _sample_library_dir(workspace)
    projects = sorted(source_dir.glob("*.efkproj"), key=lambda path: path.name.lower())
    used_ids: set[str] = set()
    asset_roots = _asset_roots(source_dir, workspace)
    entries = []

    for project in projects:
        sample_id = _unique_sample_id(_safe_sample_id(project.stem), used_ids)
        tags = _infer_tags(project.stem)
        entries.append(
            {
                "sample_id": sample_id,
                "display_name": project.stem,
                "source_project_path": _relative_to_repo(project, repo_root),
                "workspace_project_path": _relative_to_workspace(
                    library_dir / project.name,
                    workspace,
                ),
                "category_hint": tags[0] if tags else "misc",
                "tags": tags,
                "asset_roots": asset_roots,
                "project_extension": project.suffix.lower(),
                "notes": "Official SampleEffects-derived template asset.",
            }
        )

    return {
        "library": "sample_effects",
        "source": SAMPLE_EFFECTS_SOURCE_DIR,
        "imported_at": datetime.now(UTC).isoformat(),
        "template_count": len(entries),
        "templates": entries,
    }


def import_sample_effects(
    repo_root: str | Path | None = None,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Copy repo-local SampleEffects into workspace/samples and write a manifest."""
    repo_root_path = Path(repo_root).resolve() if repo_root is not None else get_project_root()
    workspace_path = resolve_workspace(workspace)
    source_dir = _sample_source_dir(repo_root_path)
    library_dir = _sample_library_dir(workspace_path)
    library_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, library_dir, dirs_exist_ok=True)
    manifest = build_sample_effects_manifest(repo_root_path, workspace_path)
    _manifest_path(workspace_path).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def list_sample_templates(workspace: str | Path | None = None) -> list[dict[str, Any]]:
    """List imported sample templates from the workspace manifest."""
    manifest = _load_manifest(resolve_workspace(workspace))
    return list(manifest.get("templates", []))


def describe_sample_template(
    sample_id: str,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Describe one imported sample template by safe sample id."""
    normalized_id = _validate_sample_id(sample_id)
    for entry in list_sample_templates(workspace):
        if entry.get("sample_id") == normalized_id:
            return entry
    raise SampleLibraryError(f"unknown sample template: {sample_id}")


def resolve_sample_project_path(
    sample_id: str,
    workspace: str | Path | None = None,
) -> str:
    """Return the workspace-relative .efkproj path for a sample id."""
    entry = describe_sample_template(sample_id, workspace)
    project_path = entry.get("workspace_project_path")
    if not isinstance(project_path, str):
        raise SampleLibraryError(f"sample template has no project path: {sample_id}")
    return project_path


def copy_sample_template_to_output(
    sample_id: str,
    output_project_path: str,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Copy an imported sample project and sibling asset dirs into workspace/outputs."""
    workspace_path = resolve_workspace(workspace)
    entry = describe_sample_template(sample_id, workspace_path)
    normalized_project_path = _normalize_output_project_path(
        output_project_path,
        workspace_path,
    )
    source_project = ensure_workspace_path(entry["workspace_project_path"], workspace_path)
    output_project = ensure_workspace_path(normalized_project_path, workspace_path)
    output_dir = output_project.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_project, output_project)

    copied_assets: list[str] = []
    for asset_root in entry.get("asset_roots", []):
        if not isinstance(asset_root, str):
            continue
        source_asset_dir = ensure_workspace_path(asset_root, workspace_path)
        if not source_asset_dir.is_dir():
            continue
        destination = output_dir / source_asset_dir.name
        shutil.copytree(source_asset_dir, destination, dirs_exist_ok=True)
        copied_assets.append(_relative_to_workspace(destination, workspace_path))

    return {
        "sample_id": entry["sample_id"],
        "display_name": entry["display_name"],
        "project_path": normalized_project_path,
        "source_project_path": entry["workspace_project_path"],
        "copied_assets": copied_assets,
    }


def create_effect_from_sample_template(
    sample_id: str,
    output_project_path: str,
    output_effect_path: str,
    *,
    client: Any | None = None,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Copy a sample template to outputs, open it, and export runtime .efk."""
    bridge = client or EffekseerBridgeClient()
    workspace_path = resolve_workspace(workspace)
    copied = copy_sample_template_to_output(
        sample_id,
        output_project_path,
        workspace_path,
    )
    effect_path = _normalize_output_effect_path(output_effect_path, workspace_path)
    open_result = bridge.open_project_from_workspace(copied["project_path"])
    export_result = bridge.export_runtime_effect_to_workspace(effect_path)
    return {
        "sample_id": copied["sample_id"],
        "display_name": copied["display_name"],
        "project_path": copied["project_path"],
        "effect_path": effect_path,
        "copied_assets": copied["copied_assets"],
        "commands": [
            {"command": "open_project_from_workspace", "result": _summarize_result(open_result)},
            {
                "command": "export_runtime_effect_to_workspace",
                "result": _summarize_result(export_result),
            },
        ],
    }


def default_sample_output_paths(sample_id: str, run_id: str | None = None) -> tuple[str, str]:
    """Return workspace-relative output paths for smoke/template creation."""
    normalized_id = _validate_sample_id(sample_id)
    actual_run_id = run_id or uuid.uuid4().hex[:8]
    output_dir = f"outputs/sample_{normalized_id}_{actual_run_id}"
    return (
        f"{output_dir}/{normalized_id}.efkproj",
        f"{output_dir}/{normalized_id}.efk",
    )


def _sample_source_dir(repo_root: Path) -> Path:
    source_dir = repo_root / SAMPLE_EFFECTS_SOURCE_DIR
    if not source_dir.is_dir():
        raise SampleLibraryError(f"SampleEffects directory was not found: {SAMPLE_EFFECTS_SOURCE_DIR}")
    return source_dir


def _sample_library_dir(workspace: Path) -> Path:
    return ensure_workspace_path(SAMPLE_LIBRARY_DIR, workspace)


def _manifest_path(workspace: Path) -> Path:
    return _sample_library_dir(workspace) / SAMPLE_MANIFEST_NAME


def _load_manifest(workspace: Path) -> dict[str, Any]:
    manifest_path = _manifest_path(workspace)
    if not manifest_path.is_file():
        raise SampleLibraryError("sample effects have not been imported")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SampleLibraryError("sample manifest must be a JSON object")
    return data


def _safe_sample_id(name: str) -> str:
    sample_id = _SAFE_ID_CHARS.sub("", name.lower())
    if not sample_id:
        raise SampleLibraryError(f"sample name cannot be converted to a safe id: {name}")
    return sample_id


def _unique_sample_id(sample_id: str, used_ids: set[str]) -> str:
    if sample_id not in used_ids:
        used_ids.add(sample_id)
        return sample_id
    index = 2
    while f"{sample_id}-{index}" in used_ids:
        index += 1
    unique_id = f"{sample_id}-{index}"
    used_ids.add(unique_id)
    return unique_id


def _validate_sample_id(sample_id: str) -> str:
    if not isinstance(sample_id, str) or not SAMPLE_ID_PATTERN.fullmatch(sample_id):
        raise SampleLibraryError("sample_id must contain only lowercase letters, digits, '-' or '_'")
    return sample_id


def _asset_roots(source_dir: Path, workspace: Path) -> list[str]:
    library_dir = _sample_library_dir(workspace)
    roots = []
    for directory in sorted(source_dir.iterdir(), key=lambda path: path.name.lower()):
        if directory.is_dir() and (
            directory.name in SAMPLE_ASSET_DIR_NAMES
            or directory.suffix == ""
        ):
            roots.append(_relative_to_workspace(library_dir / directory.name, workspace))
    return roots


def _infer_tags(name: str) -> list[str]:
    lowered = name.lower()
    rules = [
        (("fire", "flame", "salamander", "blazing"), ("fire",)),
        (("cure", "heal", "benediction", "holy"), ("heal", "holy")),
        (("water", "aqua", "undine"), ("water",)),
        (("wind", "sylph", "tornade"), ("wind",)),
        (("dark", "blood", "shadow"), ("dark",)),
        (("attack", "blow", "claw", "impact"), ("hit", "impact")),
        (("arrow", "gun", "laser", "missile"), ("projectile",)),
        (("magic",), ("magic",)),
    ]
    tags: list[str] = []
    for needles, inferred_tags in rules:
        if any(needle in lowered for needle in needles):
            tags.extend(tag for tag in inferred_tags if tag not in tags)
    return tags or ["misc"]


def _normalize_output_project_path(path: str, workspace: Path) -> str:
    normalized = normalize_workspace_open_project_path(path, workspace=workspace)
    _require_outputs_path(normalized, "project path")
    return normalized


def _normalize_output_effect_path(path: str, workspace: Path) -> str:
    normalized = normalize_workspace_runtime_effect_path(path, workspace=workspace)
    _require_outputs_path(normalized, "runtime effect path")
    return normalized


def _require_outputs_path(path: str, label: str) -> None:
    if Path(path).parts[:1] != ("outputs",):
        raise SampleLibraryError(f"{label} must be under workspace/outputs")


def _relative_to_workspace(path: Path, workspace: Path) -> str:
    return path.resolve().relative_to(workspace.resolve()).as_posix()


def _relative_to_repo(path: Path, repo_root: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def _summarize_result(result: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    summary: dict[str, Any] = {}
    for key in ("ok", "command"):
        if key in result:
            summary[key] = result[key]
    result_payload = result.get("result")
    if isinstance(result_payload, dict):
        for key in ("path", "bytes"):
            if key in result_payload:
                summary[key] = result_payload[key]
    return summary

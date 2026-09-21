from datetime import UTC, datetime
from pathlib import Path

from effekseer_mcp.paths import WorkspacePathError, ensure_workspace_path, resolve_workspace

ASSET_KINDS_BY_EXTENSION = {
    ".efkefc": "effekseer_editable_effect",
    ".efk": "effekseer_runtime_effect",
    ".efkpkg": "effekseer_package",
    ".efkmat": "effekseer_material",
    ".efkmodel": "effekseer_model",
    ".png": "texture",
    ".jpg": "texture",
    ".jpeg": "texture",
    ".webp": "texture",
    ".wav": "audio",
    ".ogg": "audio",
    ".mp3": "audio",
    ".json": "metadata",
}
UNKNOWN_ASSET_KIND = "unknown"


def list_asset_kinds() -> list[str]:
    """Return supported asset kind names."""
    return sorted({*ASSET_KINDS_BY_EXTENSION.values(), UNKNOWN_ASSET_KIND})


def classify_asset(path: str | Path) -> str:
    """Classify an asset path by extension without reading file contents."""
    extension = Path(path).suffix.lower()
    return ASSET_KINDS_BY_EXTENSION.get(extension, UNKNOWN_ASSET_KIND)


def list_assets(
    kind: str | None = None,
    workspace: str | Path | None = None,
) -> list[dict[str, str | int]]:
    """List files in the workspace as read-only asset catalog entries."""
    workspace_path = resolve_workspace(workspace)
    assets: list[dict[str, str | int]] = []

    for path in workspace_path.rglob("*"):
        if not path.is_file():
            continue

        safe_path = ensure_workspace_path(path, workspace_path)
        asset = _asset_summary(safe_path, workspace_path)
        if kind is None or asset["kind"] == kind:
            assets.append(asset)

    return sorted(assets, key=lambda asset: str(asset["relative_path"]))


def inspect_asset(
    path: str | Path,
    workspace: str | Path | None = None,
) -> dict[str, str | int]:
    """Inspect one workspace-relative asset without reading file contents."""
    requested_path = Path(path)
    if requested_path.is_absolute():
        raise WorkspacePathError(f"asset path must be workspace-relative: {path}")

    workspace_path = resolve_workspace(workspace)
    safe_path = ensure_workspace_path(requested_path, workspace_path)

    if not safe_path.is_file():
        raise FileNotFoundError(f"asset does not exist: {path}")

    return _asset_summary(safe_path, workspace_path, include_modified_time=True)


def _asset_summary(
    path: Path,
    workspace: Path,
    *,
    include_modified_time: bool = False,
) -> dict[str, str | int]:
    stat = path.stat()
    relative_path = path.relative_to(workspace).as_posix()
    extension = path.suffix.lower()
    summary: dict[str, str | int] = {
        "relative_path": relative_path,
        "kind": classify_asset(path),
        "extension": extension,
        "size_bytes": stat.st_size,
    }

    if include_modified_time:
        summary["modified_time_iso"] = datetime.fromtimestamp(
            stat.st_mtime,
            UTC,
        ).isoformat()

    return summary

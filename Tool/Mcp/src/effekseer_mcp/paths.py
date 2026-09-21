from pathlib import Path
import os
import sys


class WorkspacePathError(ValueError):
    """Raised when a requested path escapes the configured workspace."""


PROJECT_ROOT = (
    Path(sys._MEIPASS) if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parents[2]
)
DEFAULT_WORKSPACE = PROJECT_ROOT / "workspace"
WORKSPACE_INPUTS = "inputs"
WORKSPACE_OUTPUTS = "outputs"
WORKSPACE_TEMP = "temp"


def get_project_root() -> Path:
    """Return the repository root for this MCP server."""
    return PROJECT_ROOT


def resolve_workspace(
    workspace: str | Path | None = None,
    *,
    project_root: str | Path | None = None,
    create: bool = True,
) -> Path:
    """Resolve and optionally create the workspace directory."""
    root = (
        Path(project_root).expanduser().resolve()
        if project_root is not None
        else get_project_root()
    )
    if workspace is None:
        workspace = os.getenv("EFFEKSEER_WORKSPACE")
    raw_workspace = Path(workspace) if workspace is not None else root / "workspace"

    if not raw_workspace.is_absolute():
        raw_workspace = root / raw_workspace

    resolved = raw_workspace.expanduser().resolve()
    if create:
        resolved.mkdir(parents=True, exist_ok=True)

    return resolved


def ensure_workspace_path(path: str | Path, workspace: str | Path | None = None) -> Path:
    """Resolve a path and ensure it remains inside the workspace."""
    workspace_path = resolve_workspace(workspace)
    requested_path = Path(path)

    if requested_path.is_absolute():
        resolved_path = requested_path.expanduser().resolve(strict=False)
    else:
        resolved_path = (workspace_path / requested_path).expanduser().resolve(strict=False)

    try:
        resolved_path.relative_to(workspace_path)
    except ValueError as exc:
        raise WorkspacePathError(f"path is outside the workspace: {path}") from exc

    return resolved_path


def get_workspace_subdir(
    name: str,
    workspace: str | Path | None = None,
    *,
    create: bool = True,
) -> Path:
    """Return a named workspace subdirectory after validating it is safe."""
    if name not in {WORKSPACE_INPUTS, WORKSPACE_OUTPUTS, WORKSPACE_TEMP}:
        raise ValueError(f"unsupported workspace directory: {name}")

    path = ensure_workspace_path(name, workspace)
    if create:
        path.mkdir(parents=True, exist_ok=True)

    return path


def get_inputs_dir(workspace: str | Path | None = None) -> Path:
    """Return workspace/inputs, creating it when needed."""
    return get_workspace_subdir(WORKSPACE_INPUTS, workspace)


def get_outputs_dir(workspace: str | Path | None = None) -> Path:
    """Return workspace/outputs, creating it when needed."""
    return get_workspace_subdir(WORKSPACE_OUTPUTS, workspace)


def get_temp_dir(workspace: str | Path | None = None) -> Path:
    """Return workspace/temp, creating it when needed."""
    return get_workspace_subdir(WORKSPACE_TEMP, workspace)

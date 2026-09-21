from pathlib import Path

import pytest

from effekseer_mcp.paths import (
    WorkspacePathError,
    ensure_workspace_path,
    get_inputs_dir,
    get_outputs_dir,
    get_temp_dir,
    resolve_workspace,
)


def test_workspace_path_allows_descendant(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"

    resolved = ensure_workspace_path("inputs/effect.efkefc", workspace)

    assert resolved == workspace.resolve() / "inputs" / "effect.efkefc"


def test_workspace_path_rejects_parent_traversal(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"

    with pytest.raises(WorkspacePathError):
        ensure_workspace_path("../outside.txt", workspace)


def test_workspace_path_rejects_absolute_path_outside_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    outside_path = tmp_path / "outside.txt"

    with pytest.raises(WorkspacePathError):
        ensure_workspace_path(outside_path, workspace)


def test_workspace_standard_directories_are_created(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"

    assert get_inputs_dir(workspace).is_dir()
    assert get_outputs_dir(workspace).is_dir()
    assert get_temp_dir(workspace).is_dir()


def test_resolve_workspace_uses_supplied_project_root_when_workspace_is_none(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"

    workspace = resolve_workspace(project_root=project_root)

    assert workspace == project_root.resolve() / "workspace"
    assert workspace.is_dir()

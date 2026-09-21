from pathlib import Path

import pytest

from effekseer_mcp.assets import (
    classify_asset,
    inspect_asset,
    list_assets,
)
from effekseer_mcp.paths import WorkspacePathError


@pytest.mark.parametrize(
    ("filename", "kind"),
    [
        ("effect.efkefc", "effekseer_editable_effect"),
        ("runtime.efk", "effekseer_runtime_effect"),
        ("bundle.efkpkg", "effekseer_package"),
        ("texture.png", "texture"),
        ("sound.wav", "audio"),
        ("recipe.json", "metadata"),
        ("notes.txt", "unknown"),
    ],
)
def test_classify_asset_by_extension(filename: str, kind: str) -> None:
    assert classify_asset(filename) == kind


def test_list_assets_returns_workspace_relative_paths_only(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    (workspace / "inputs").mkdir(parents=True)
    (workspace / "inputs" / "effect.efkefc").write_bytes(b"effect")
    (workspace / "texture.png").write_bytes(b"png")

    assets = list_assets(workspace=workspace)

    assert {asset["relative_path"] for asset in assets} == {
        "inputs/effect.efkefc",
        "texture.png",
    }
    assert all(not Path(str(asset["relative_path"])).is_absolute() for asset in assets)


def test_inspect_asset_rejects_parent_traversal(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (tmp_path / "outside.txt").write_bytes(b"outside")

    with pytest.raises(WorkspacePathError):
        inspect_asset("../outside.txt", workspace=workspace)


def test_inspect_asset_returns_no_absolute_paths(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "effect.efkefc").write_bytes(b"effect")

    result = inspect_asset("effect.efkefc", workspace=workspace)

    assert result["relative_path"] == "effect.efkefc"
    assert result["kind"] == "effekseer_editable_effect"
    assert result["extension"] == ".efkefc"
    assert result["size_bytes"] == 6
    assert "modified_time_iso" in result
    assert all(not Path(str(value)).is_absolute() for value in result.values())


def test_inspect_asset_rejects_absolute_path(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    asset = workspace / "effect.efkefc"
    asset.write_bytes(b"effect")

    with pytest.raises(WorkspacePathError):
        inspect_asset(asset, workspace=workspace)


def test_list_assets_filters_by_kind(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "effect.efkefc").write_bytes(b"effect")
    (workspace / "texture.png").write_bytes(b"png")
    (workspace / "sound.wav").write_bytes(b"wav")

    assets = list_assets(kind="texture", workspace=workspace)

    assert assets == [
        {
            "relative_path": "texture.png",
            "kind": "texture",
            "extension": ".png",
            "size_bytes": 3,
        },
    ]

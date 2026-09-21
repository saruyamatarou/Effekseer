from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from effekseer_mcp.bridge_client import EffekseerBridgeCommandError
from effekseer_mcp.sample_library import (
    SampleLibraryError,
    copy_sample_template_to_output,
    create_effect_from_sample_template,
    describe_sample_template,
    import_sample_effects,
    list_sample_templates,
    resolve_sample_project_path,
)


class FakeSampleBridgeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def open_project_from_workspace(self, path: str) -> dict[str, Any]:
        self.calls.append(("open_project_from_workspace", (path,)))
        return {"ok": True, "result": {"path": path}}

    def export_runtime_effect_to_workspace(self, path: str) -> dict[str, Any]:
        self.calls.append(("export_runtime_effect_to_workspace", (path,)))
        return {"ok": True, "result": {"path": path, "bytes": 12}}


def create_sample_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    sample_dir = repo_root / "SampleEffects"
    sample_dir.mkdir(parents=True)
    (sample_dir / "FireBall.efkproj").write_text("fire", encoding="utf-8")
    (sample_dir / "MagicHeal1.efkproj").write_text("heal", encoding="utf-8")
    (sample_dir / "Attack1.efkproj").write_text("attack", encoding="utf-8")
    (sample_dir / "Parts").mkdir()
    (sample_dir / "Parts" / "spark.png").write_text("png", encoding="utf-8")
    (sample_dir / "Model").mkdir()
    (sample_dir / "Model" / "mesh.efkmodel").write_text("model", encoding="utf-8")
    return repo_root


def test_import_sample_effects_creates_manifest_with_relative_paths(tmp_path: Path) -> None:
    repo_root = create_sample_repo(tmp_path)
    workspace = tmp_path / "workspace"

    manifest = import_sample_effects(repo_root=repo_root, workspace=workspace)

    assert manifest["library"] == "sample_effects"
    assert manifest["template_count"] == 3
    templates = list_sample_templates(workspace)
    assert [template["sample_id"] for template in templates] == [
        "attack1",
        "fireball",
        "magicheal1",
    ]
    fireball = describe_sample_template("fireball", workspace)
    assert fireball["display_name"] == "FireBall"
    assert fireball["source_project_path"] == "SampleEffects/FireBall.efkproj"
    assert fireball["workspace_project_path"] == (
        "samples/sample_effects/FireBall.efkproj"
    )
    assert "fire" in fireball["tags"]
    assert all(not Path(value).is_absolute() for value in fireball["asset_roots"])
    assert resolve_sample_project_path("fireball", workspace) == (
        "samples/sample_effects/FireBall.efkproj"
    )


def test_sample_id_safety(tmp_path: Path) -> None:
    repo_root = create_sample_repo(tmp_path)
    workspace = tmp_path / "workspace"
    import_sample_effects(repo_root=repo_root, workspace=workspace)

    with pytest.raises(SampleLibraryError):
        describe_sample_template("../fireball", workspace)

    with pytest.raises(SampleLibraryError):
        describe_sample_template("FireBall", workspace)


def test_copy_sample_template_to_output_copies_project_and_asset_roots(
    tmp_path: Path,
) -> None:
    repo_root = create_sample_repo(tmp_path)
    workspace = tmp_path / "workspace"
    import_sample_effects(repo_root=repo_root, workspace=workspace)

    result = copy_sample_template_to_output(
        "fireball",
        "outputs/sample_fireball/fireball.efkproj",
        workspace,
    )

    assert result["sample_id"] == "fireball"
    assert result["project_path"] == "outputs/sample_fireball/fireball.efkproj"
    assert (
        workspace / "outputs/sample_fireball/fireball.efkproj"
    ).read_text(encoding="utf-8") == "fire"
    assert (workspace / "outputs/sample_fireball/Parts/spark.png").is_file()
    assert (workspace / "outputs/sample_fireball/Model/mesh.efkmodel").is_file()
    assert sorted(result["copied_assets"]) == [
        "outputs/sample_fireball/Model",
        "outputs/sample_fireball/Parts",
    ]


@pytest.mark.parametrize(
    "output_project_path",
    [
        "samples/not_outputs/fireball.efkproj",
        "../fireball.efkproj",
        "outputs/fireball.txt",
        "C:/outside/fireball.efkproj",
    ],
)
def test_copy_sample_template_to_output_rejects_unsafe_project_paths(
    tmp_path: Path,
    output_project_path: str,
) -> None:
    repo_root = create_sample_repo(tmp_path)
    workspace = tmp_path / "workspace"
    import_sample_effects(repo_root=repo_root, workspace=workspace)

    with pytest.raises((SampleLibraryError, EffekseerBridgeCommandError, ValueError)):
        copy_sample_template_to_output("fireball", output_project_path, workspace)


def test_create_effect_from_sample_template_opens_and_exports(tmp_path: Path) -> None:
    repo_root = create_sample_repo(tmp_path)
    workspace = tmp_path / "workspace"
    import_sample_effects(repo_root=repo_root, workspace=workspace)
    client = FakeSampleBridgeClient()

    result = create_effect_from_sample_template(
        "fireball",
        "outputs/sample_fireball/fireball.efkproj",
        "outputs/sample_fireball/fireball.efk",
        client=client,
        workspace=workspace,
    )

    assert result["sample_id"] == "fireball"
    assert result["project_path"] == "outputs/sample_fireball/fireball.efkproj"
    assert result["effect_path"] == "outputs/sample_fireball/fireball.efk"
    assert client.calls == [
        (
            "open_project_from_workspace",
            ("outputs/sample_fireball/fireball.efkproj",),
        ),
        (
            "export_runtime_effect_to_workspace",
            ("outputs/sample_fireball/fireball.efk",),
        ),
    ]


def test_create_effect_from_sample_template_rejects_unsafe_effect_path(
    tmp_path: Path,
) -> None:
    repo_root = create_sample_repo(tmp_path)
    workspace = tmp_path / "workspace"
    import_sample_effects(repo_root=repo_root, workspace=workspace)

    with pytest.raises((SampleLibraryError, EffekseerBridgeCommandError, ValueError)):
        create_effect_from_sample_template(
            "fireball",
            "outputs/sample_fireball/fireball.efkproj",
            "samples/fireball.efk",
            client=FakeSampleBridgeClient(),
            workspace=workspace,
        )

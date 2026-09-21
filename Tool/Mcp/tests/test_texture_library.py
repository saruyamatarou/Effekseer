from __future__ import annotations

import json
from pathlib import Path

import pytest

from effekseer_mcp.texture_library import (
    TextureLibraryError,
    generate_builtin_textures,
    get_builtin_texture,
    get_default_texture_set,
    list_builtin_textures,
    resolve_texture_roles,
)


def test_list_builtin_textures_has_expected_manifest_shape() -> None:
    textures = list_builtin_textures()

    assert {texture["id"] for texture in textures} == {
        "soft_circle",
        "core_glow",
        "spark_dot",
        "spark_star",
        "smoke_puff_01",
        "smoke_puff_02",
        "slash_arc",
        "ring_soft",
        "trail_streak",
        "ripple_ring",
    }
    for texture in textures:
        assert texture["path"].startswith("inputs/textures/builtin/")
        assert texture["license"] == "generated_by_effekseer_mcp"
        assert texture["source"] == "procedural"
        assert texture["recommended_blend"] in {"Add", "Blend"}


def test_generate_builtin_textures_writes_pngs_and_manifest(tmp_path: Path) -> None:
    result = generate_builtin_textures(tmp_path, size=32)

    assert result["manifest_path"] == "inputs/textures/builtin/texture_manifest.json"
    manifest_path = tmp_path / result["manifest_path"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["texture_set"] == "builtin"
    assert len(manifest["textures"]) == 10

    for texture in manifest["textures"]:
        png_path = tmp_path / texture["path"]
        assert png_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_texture_role_resolution_defaults_and_overrides() -> None:
    defaults = get_default_texture_set()

    assert defaults["core"] == "inputs/textures/builtin/core_glow.png"
    assert get_builtin_texture("spark") == "inputs/textures/builtin/spark_star.png"
    assert (
        get_builtin_texture("spark", "spark_dot")
        == "inputs/textures/builtin/spark_dot.png"
    )

    resolved = resolve_texture_roles(
        "builtin",
        {
            "spark": "inputs/textures/custom_spark.png",
            "trail": "inputs/textures/custom_trail.png",
        },
    )
    assert resolved["core"] == defaults["core"]
    assert resolved["spark"] == "inputs/textures/custom_spark.png"
    assert resolved["trail"] == "inputs/textures/custom_trail.png"


def test_texture_role_resolution_rejects_unsafe_values() -> None:
    with pytest.raises(TextureLibraryError, match="unsupported texture set"):
        resolve_texture_roles("external", None)
    with pytest.raises(TextureLibraryError, match="unsupported texture role"):
        resolve_texture_roles("builtin", {"unknown": "inputs/x.png"})
    with pytest.raises(TextureLibraryError, match="workspace-relative"):
        resolve_texture_roles("builtin", {"core": "C:/outside.png"})
    with pytest.raises(TextureLibraryError, match="must not contain"):
        resolve_texture_roles("builtin", {"core": "../outside.png"})

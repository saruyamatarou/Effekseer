from __future__ import annotations

import json
from pathlib import Path

import pytest

from effekseer_mcp.sample_analyzer import (
    SampleAnalyzerError,
    analyze_project_file,
    analyze_sample_effects,
    get_sample_analysis_summary,
)


def write_manifest(workspace: Path, templates: list[dict]) -> None:
    sample_dir = workspace / "samples/sample_effects"
    sample_dir.mkdir(parents=True, exist_ok=True)
    (sample_dir / "sample_manifest.json").write_text(
        json.dumps({"templates": templates}, indent=2) + "\n",
        encoding="utf-8",
    )


def sample_project_xml() -> str:
    return """<?xml version="1.0" encoding="utf-8"?>
<EffekseerProject>
  <Root>
    <Children>
      <Node>
        <CommonValues>
          <MaxGeneration><Value>12</Value></MaxGeneration>
          <Life><Center>45</Center><Min>30</Min><Max>60</Max></Life>
          <GenerationTime><Center>0.5</Center><Min>0.25</Min><Max>0.75</Max></GenerationTime>
          <GenerationTimeOffset>3</GenerationTimeOffset>
        </CommonValues>
        <LocationValues>
          <PVA>
            <Velocity>
              <X><Center>1</Center><Min>0</Min><Max>2</Max></X>
              <Y><Center>3</Center><Min>2</Min><Max>4</Max></Y>
            </Velocity>
          </PVA>
        </LocationValues>
        <RotationValues>
          <PVA>
            <Velocity><Z><Center>5</Center><Min>4</Min><Max>6</Max></Z></Velocity>
          </PVA>
        </RotationValues>
        <ScalingValues>
          <Fixed><Scale><X>1.5</X><Y>2.0</Y><Z>1.0</Z></Scale></Fixed>
        </ScalingValues>
        <RendererCommonValues>
          <ColorTexture>Texture/Fire.png</ColorTexture>
          <AlphaBlend>2</AlphaBlend>
          <FadeIn><Frame>4</Frame></FadeIn>
          <FadeOut><Frame>18</Frame></FadeOut>
        </RendererCommonValues>
        <DrawingValues><Type>0</Type></DrawingValues>
        <ModelValues><Model>Model/Sample.efkmodel</Model></ModelValues>
        <SoundValues><Sound><Wave>Sound/Hit.wav</Wave></Sound></SoundValues>
      </Node>
    </Children>
  </Root>
</EffekseerProject>
"""


def test_analyze_project_file_extracts_core_values(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    project = workspace / "samples/sample_effects/FireBall.efkproj"
    project.parent.mkdir(parents=True)
    project.write_text(sample_project_xml(), encoding="utf-8")

    sample = analyze_project_file(
        "samples/sample_effects/FireBall.efkproj",
        workspace=workspace,
        sample_id="fireball",
        display_name="FireBall",
        category_hint="fire",
    )

    assert sample["sample_id"] == "fireball"
    assert sample["node_count"] == 1
    assert sample["max_generation_values"] == [12.0]
    assert sample["life_values"] == [{"center": 45.0, "min": 30.0, "max": 60.0}]
    assert sample["generation_time_values"] == [0.5, 0.25, 0.75]
    assert sample["generation_time_offset_values"] == [3.0]
    assert sample["location_velocity_values"] == [1.0, 0.0, 2.0, 3.0, 4.0]
    assert sample["rotation_velocity_values"] == [5.0, 4.0, 6.0]
    assert sample["scale_values"] == [1.5, 2.0, 1.0]
    assert sample["renderer_type_values"] == ["0"]
    assert sample["alpha_blend_values"] == ["2"]
    assert sample["color_texture_paths"] == ["Texture/Fire.png"]
    assert sample["model_paths"] == ["Model/Sample.efkmodel"]
    assert sample["sound_paths"] == ["Sound/Hit.wav"]
    assert sample["fade_in_frames"] == [4.0]
    assert sample["fade_out_frames"] == [18.0]
    assert sample["texture_usage_count"] == 1


def test_analyze_project_file_rejects_workspace_outside_paths(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    with pytest.raises(SampleAnalyzerError):
        analyze_project_file("../outside.efkproj", workspace=workspace)

    with pytest.raises(SampleAnalyzerError):
        analyze_project_file("outputs/not_sample.efkproj", workspace=workspace)


def test_analyze_sample_effects_writes_json_markdown_and_continues_on_bad_xml(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    sample_dir = workspace / "samples/sample_effects"
    sample_dir.mkdir(parents=True)
    (sample_dir / "FireBall.efkproj").write_text(sample_project_xml(), encoding="utf-8")
    (sample_dir / "Broken.efkproj").write_text("<EffekseerProject>", encoding="utf-8")
    write_manifest(
        workspace,
        [
            {
                "sample_id": "fireball",
                "display_name": "FireBall",
                "category_hint": "fire",
                "workspace_project_path": "samples/sample_effects/FireBall.efkproj",
            },
            {
                "sample_id": "broken",
                "display_name": "Broken",
                "category_hint": "misc",
                "workspace_project_path": "samples/sample_effects/Broken.efkproj",
            },
        ],
    )

    result = analyze_sample_effects(workspace=workspace)

    assert result["analysis_path"] == "outputs/sample_analysis/sample_analysis.json"
    assert result["summary_path"] == "outputs/sample_analysis/sample_analysis.md"
    assert result["summary"]["sample_count"] == 1
    assert result["summary"]["error_count"] == 1
    assert result["summary"]["categories"]["fire"]["life"]["median"] == 45.0
    assert result["summary"]["categories"]["fire"]["generation"]["median"] == 12.0
    assert result["summary"]["texture_ranking"] == [
        {"value": "Texture/Fire.png", "count": 1}
    ]
    markdown = (workspace / result["summary_path"]).read_text(encoding="utf-8")
    assert "# SampleEffects Analysis" in markdown
    assert "Texture Ranking" in markdown
    summary = get_sample_analysis_summary(workspace)
    assert summary["sample_count"] == 1
    assert summary["error_count"] == 1


def test_analyze_sample_effects_sample_id_filter(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    sample_dir = workspace / "samples/sample_effects"
    sample_dir.mkdir(parents=True)
    (sample_dir / "FireBall.efkproj").write_text(sample_project_xml(), encoding="utf-8")
    write_manifest(
        workspace,
        [
            {
                "sample_id": "fireball",
                "display_name": "FireBall",
                "category_hint": "fire",
                "workspace_project_path": "samples/sample_effects/FireBall.efkproj",
            }
        ],
    )

    result = analyze_sample_effects(sample_id="fireball", workspace=workspace)

    assert result["analysis"]["sample_count"] == 1
    assert result["analysis"]["samples"][0]["sample_id"] == "fireball"


def test_get_sample_analysis_summary_requires_existing_analysis(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    with pytest.raises(SampleAnalyzerError):
        get_sample_analysis_summary(workspace)

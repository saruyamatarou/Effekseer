from __future__ import annotations

import json
from pathlib import Path

from effekseer_mcp.recipe_tuning import (
    apply_recipe_tuning,
    clamp_motion_value,
    get_category_baseline,
    get_recipe_tuning_baseline,
    load_sample_analysis,
)


def write_analysis(workspace: Path) -> None:
    output_dir = workspace / "outputs/sample_analysis"
    output_dir.mkdir(parents=True)
    (output_dir / "sample_analysis.json").write_text(
        json.dumps(
            {
                "categories": {
                    "fire": {
                        "life": {"count": 2, "min": 18.0, "max": 42.0, "median": 30.0},
                        "generation": {
                            "count": 2,
                            "min": 6.0,
                            "max": 20.0,
                            "median": 10.0,
                        },
                        "velocity": {
                            "count": 2,
                            "min": 0.1,
                            "max": 0.8,
                            "median": 0.25,
                        },
                        "scale": {"count": 2, "min": 0.5, "max": 2.0, "median": 1.2},
                    },
                    "projectile": {
                        "life": {"count": 1, "min": 24.0, "max": 24.0, "median": 24.0},
                        "generation": {
                            "count": 1,
                            "min": 8.0,
                            "max": 8.0,
                            "median": 8.0,
                        },
                        "velocity": {
                            "count": 1,
                            "min": 0.4,
                            "max": 0.4,
                            "median": 0.4,
                        },
                        "scale": {"count": 1, "min": 1.0, "max": 1.0, "median": 1.0},
                    },
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_load_sample_analysis_and_category_baseline(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    write_analysis(workspace)

    analysis = load_sample_analysis(workspace)
    baseline = get_category_baseline("fire", analysis=analysis)

    assert baseline["category"] == "fire"
    assert baseline["source"] == "sample_analysis"
    assert baseline["life"]["median"] == 30.0


def test_recipe_baseline_uses_category_mapping(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    write_analysis(workspace)

    baseline = get_recipe_tuning_baseline(
        "projectile_trail",
        "water_projectile",
        "water",
        workspace=workspace,
    )

    assert baseline["category"] == "projectile"
    assert baseline["source"] == "sample_analysis"


def test_missing_category_uses_fallback() -> None:
    baseline = get_category_baseline("missing", analysis={})

    assert baseline["category"] == "misc"
    assert baseline["source"] == "fallback"


def test_clamp_motion_value_reduces_radius_and_velocity() -> None:
    baseline = {"radius_multiplier": 0.25, "velocity_multiplier": 0.2}

    assert clamp_motion_value(80.0, baseline, "radius") == 20.0
    assert clamp_motion_value(1.0, baseline, "velocity_factor") == 0.2


def test_apply_recipe_tuning_clamps_motion_values(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    write_analysis(workspace)

    tuning = apply_recipe_tuning(
        "elemental_burst",
        "fire",
        "fire",
        {
            "element_radius": 80.0,
            "element_velocity_factor": 1.0,
            "element_scale": 4.0,
            "element_life": 20,
            "element_generation": 80,
        },
        workspace=workspace,
    )

    parameters = tuning["parameters"]
    assert tuning["enabled"] is True
    assert tuning["category"] == "fire"
    assert parameters["element_radius"] < 80.0
    assert parameters["element_velocity_factor"] < 1.0
    assert parameters["element_scale"] <= 3.0
    assert parameters["element_life"] >= 30
    assert parameters["element_generation"] <= 25


def test_apply_recipe_tuning_off_preserves_values(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    write_analysis(workspace)
    raw = {"burst_radius": 80.0, "burst_velocity_factor": 1.0}

    tuning = apply_recipe_tuning(
        "firework_burst",
        "firework",
        None,
        raw,
        sample_tuning="off",
        workspace=workspace,
    )

    assert tuning["enabled"] is False
    assert tuning["parameters"] == raw

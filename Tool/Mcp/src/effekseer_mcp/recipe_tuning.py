from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from effekseer_mcp.paths import ensure_workspace_path, resolve_workspace
from effekseer_mcp.sample_analyzer import SAMPLE_ANALYSIS_DIR, SAMPLE_ANALYSIS_JSON


def _stats(median: float) -> dict[str, float | int]:
    return {"count": 1, "min": median, "max": median, "median": median}


def _baseline(
    category: str,
    *,
    life: float,
    generation: float,
    velocity: float,
    scale: float,
) -> dict[str, Any]:
    return {
        "category": category,
        "life": _stats(life),
        "generation": _stats(generation),
        "velocity": _stats(velocity),
        "scale": _stats(scale),
    }


FALLBACK_BASELINES: dict[str, dict[str, Any]] = {
    "fire": _baseline("fire", life=30.0, generation=10.0, velocity=0.2, scale=1.5),
    "heal": _baseline("heal", life=35.0, generation=12.0, velocity=0.05, scale=1.0),
    "hit": _baseline("hit", life=28.0, generation=20.0, velocity=0.1, scale=1.5),
    "impact": _baseline("impact", life=28.0, generation=20.0, velocity=0.1, scale=1.5),
    "magic": _baseline("magic", life=30.0, generation=15.0, velocity=0.1, scale=1.0),
    "projectile": _baseline(
        "projectile",
        life=30.0,
        generation=10.0,
        velocity=0.8,
        scale=2.0,
    ),
    "water": _baseline("water", life=20.0, generation=10.0, velocity=0.1, scale=1.0),
    "wind": _baseline("wind", life=20.0, generation=8.0, velocity=1.0, scale=1.0),
    "dark": _baseline("dark", life=36.0, generation=20.0, velocity=0.1, scale=1.3),
    "holy": _baseline("holy", life=35.0, generation=12.0, velocity=0.05, scale=1.0),
    "misc": _baseline("misc", life=30.0, generation=13.0, velocity=0.15, scale=1.25),
}
RADIUS_MULTIPLIER_BY_RECIPE = {
    "firework_burst": 0.28,
    "slash": 0.28,
    "heal_sparkle": 0.45,
    "elemental_burst": 0.33,
    "projectile_trail": 0.32,
}
VELOCITY_MULTIPLIER_BY_RECIPE = {
    "firework_burst": 0.28,
    "slash": 0.32,
    "heal_sparkle": 0.35,
    "elemental_burst": 0.35,
    "projectile_trail": 0.38,
}


class RecipeTuningError(ValueError):
    """Raised when recipe tuning input is malformed."""


def load_sample_analysis(workspace: str | Path | None = None) -> dict[str, Any]:
    """Load generated sample analysis JSON from the workspace."""
    workspace_path = resolve_workspace(workspace)
    analysis_path = ensure_workspace_path(
        f"{SAMPLE_ANALYSIS_DIR}/{SAMPLE_ANALYSIS_JSON}",
        workspace_path,
    )
    if not analysis_path.is_file():
        raise RecipeTuningError("sample analysis has not been generated")
    data = json.loads(analysis_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RecipeTuningError("sample analysis must be a JSON object")
    return data


def get_category_baseline(
    category: str,
    *,
    analysis: dict[str, Any] | None = None,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Return a category baseline from sample analysis or fallback data."""
    normalized = _normalize_category(category)
    analysis_data = analysis
    if analysis_data is None:
        try:
            analysis_data = load_sample_analysis(workspace)
        except RecipeTuningError:
            analysis_data = None

    categories = analysis_data.get("categories", {}) if isinstance(analysis_data, dict) else {}
    baseline = categories.get(normalized) if isinstance(categories, dict) else None
    if isinstance(baseline, dict):
        result = copy.deepcopy(baseline)
        result["category"] = normalized
        result["source"] = "sample_analysis"
        return result

    fallback = copy.deepcopy(FALLBACK_BASELINES.get(normalized, FALLBACK_BASELINES["misc"]))
    fallback["source"] = "fallback"
    return fallback


def get_recipe_tuning_baseline(
    recipe_id: str,
    kind: str | None = None,
    element: str | None = None,
    *,
    analysis: dict[str, Any] | None = None,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Resolve a sample-analysis category baseline for a recipe/kind/element."""
    categories = _categories_for_recipe(recipe_id, kind, element)
    for category in categories:
        baseline = get_category_baseline(
            category,
            analysis=analysis,
            workspace=workspace,
        )
        if baseline.get("source") == "sample_analysis":
            return baseline
    return get_category_baseline(categories[0], analysis={}, workspace=workspace)


def clamp_motion_value(value: float, baseline: dict[str, Any], key: str) -> float:
    """Clamp or adjust one numeric recipe value with conservative sample guidance."""
    numeric = float(value)
    if key in {"radius", "burst_radius", "residual_radius"}:
        return max(1.0, numeric * float(baseline.get("radius_multiplier", 0.33)))
    if key in {"velocity", "velocity_factor"}:
        return max(0.05, numeric * float(baseline.get("velocity_multiplier", 0.35)))
    if key == "scale":
        scale_cap = _median(baseline, "scale") * 2.5
        return min(numeric, max(0.25, scale_cap))
    if key == "life":
        life_floor = _median(baseline, "life")
        return max(numeric, life_floor, numeric * 1.12)
    if key == "max_generation":
        generation_cap = max(1.0, _median(baseline, "generation") * 2.5)
        return max(1.0, min(numeric, generation_cap))
    return numeric


def apply_recipe_tuning(
    recipe_id: str,
    kind: str | None,
    element: str | None,
    raw_parameters: dict[str, Any],
    *,
    sample_tuning: str | dict[str, Any] | None = "auto",
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Apply sample-guided conservative tuning to raw recipe parameters."""
    mode, overrides = _normalize_sample_tuning(sample_tuning)
    original = copy.deepcopy(raw_parameters)
    if mode == "off":
        return {
            "enabled": False,
            "mode": "off",
            "parameters": copy.deepcopy(raw_parameters),
            "original_parameters": original,
            "applied_multipliers": {},
        }

    baseline = get_recipe_tuning_baseline(
        recipe_id,
        kind,
        element,
        workspace=workspace,
    )
    baseline["radius_multiplier"] = float(
        overrides.get(
            "radius_multiplier",
            RADIUS_MULTIPLIER_BY_RECIPE.get(recipe_id, 0.33),
        )
    )
    baseline["velocity_multiplier"] = float(
        overrides.get(
            "velocity_multiplier",
            VELOCITY_MULTIPLIER_BY_RECIPE.get(recipe_id, 0.35),
        )
    )
    parameters = copy.deepcopy(raw_parameters)

    for key in list(parameters):
        if _is_radius_key(key):
            parameters[key] = clamp_motion_value(parameters[key], baseline, "radius")
        elif _is_velocity_key(key):
            parameters[key] = clamp_motion_value(
                parameters[key],
                baseline,
                "velocity_factor",
            )
        elif _is_scale_key(key):
            parameters[key] = clamp_motion_value(parameters[key], baseline, "scale")
        elif _is_life_key(key):
            parameters[key] = max(1, round(clamp_motion_value(parameters[key], baseline, "life")))
        elif _is_generation_key(key):
            parameters[key] = max(
                1,
                round(clamp_motion_value(parameters[key], baseline, "max_generation")),
            )

    return {
        "enabled": True,
        "mode": mode,
        "category": baseline.get("category"),
        "baseline_source": baseline.get("source"),
        "baseline": _baseline_summary(baseline),
        "original_parameters": original,
        "parameters": parameters,
        "applied_multipliers": {
            "radius": baseline["radius_multiplier"],
            "velocity": baseline["velocity_multiplier"],
        },
    }


def _normalize_category(category: str) -> str:
    if not isinstance(category, str) or not category:
        return "misc"
    if category == "impact":
        return "hit"
    return category


def _categories_for_recipe(
    recipe_id: str,
    kind: str | None,
    element: str | None,
) -> tuple[str, ...]:
    if recipe_id == "firework_burst":
        return ("magic", "fire")
    if recipe_id == "slash":
        return ("hit", "impact")
    if recipe_id == "heal_sparkle":
        return ("heal", "holy")
    if recipe_id == "elemental_burst":
        return (_normalize_category(element or kind or "fire"), "magic")
    if recipe_id == "projectile_trail":
        if element in {"fire", "water"}:
            return ("projectile", element)
        return ("projectile", _normalize_category(element or "misc"))
    return ("misc",)


def _normalize_sample_tuning(
    sample_tuning: str | dict[str, Any] | None,
) -> tuple[str, dict[str, Any]]:
    if sample_tuning is None or sample_tuning == "auto":
        return "auto", {}
    if sample_tuning == "off":
        return "off", {}
    if isinstance(sample_tuning, dict):
        mode = sample_tuning.get("mode", "auto")
        if mode not in {"auto", "off"}:
            raise RecipeTuningError("sample_tuning.mode must be 'auto' or 'off'")
        return str(mode), sample_tuning
    raise RecipeTuningError("sample_tuning must be 'auto', 'off', an object, or null")


def _median(baseline: dict[str, Any], key: str) -> float:
    stats = baseline.get(key)
    if not isinstance(stats, dict):
        return _median(FALLBACK_BASELINES["misc"], key)
    value = stats.get("median")
    if isinstance(value, bool) or not isinstance(value, int | float):
        return _median(FALLBACK_BASELINES["misc"], key)
    return float(value)


def _baseline_summary(baseline: dict[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(baseline.get(key))
        for key in ("life", "generation", "velocity", "scale")
    }


def _is_radius_key(key: str) -> bool:
    return "radius" in key


def _is_velocity_key(key: str) -> bool:
    return "velocity_factor" in key


def _is_scale_key(key: str) -> bool:
    return key == "scale" or key.endswith("_scale")


def _is_life_key(key: str) -> bool:
    return key == "life" or key.endswith("_life")


def _is_generation_key(key: str) -> bool:
    return key in {"max_generation", "spark_count", "secondary_spark_count"} or key.endswith(
        "_generation"
    )

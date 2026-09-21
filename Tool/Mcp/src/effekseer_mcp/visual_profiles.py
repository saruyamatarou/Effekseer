from __future__ import annotations

import copy
from typing import Any


class VisualProfileError(ValueError):
    """Raised when a visual profile is unknown or malformed."""


VISUAL_PROFILES: dict[str, dict[str, Any]] = {
    "firework_default": {
        "id": "firework_default",
        "nodes": {
            "burst_core": {
                "texture_role": "core",
                "alpha_blend": "Add",
                "color_alpha": 1.0,
                "scale": 1.25,
            },
            "burst_sparks": {
                "texture_role": "spark",
                "alpha_blend": "Add",
                "generation": 1.15,
                "radius": 1.1,
                "scale": 0.9,
            },
            "secondary_sparkles": {
                "texture_role": "smoke",
                "alpha_blend": "Blend",
                "color_alpha": 0.68,
                "generation": 0.9,
                "life": 1.25,
                "radius": 0.9,
                "gravity": 0.6,
                "scale": 1.15,
            },
        },
    },
    "slash_wind_default": {
        "id": "slash_wind_default",
        "nodes": {
            "slash_arc": {
                "texture_role": "slash",
                "alpha_blend": "Add",
                "color_alpha": 1.0,
                "life": 0.75,
                "scale": 1.25,
                "scale_x": 1.25,
                "scale_y": 0.72,
            },
            "impact_sparks": {
                "texture_role": "spark",
                "alpha_blend": "Add",
                "generation": 1.05,
                "radius": 0.85,
                "life": 0.85,
            },
            "afterimage_particles": {
                "texture_role": "trail",
                "alpha_blend": "Add",
                "color_alpha": 0.65,
                "generation": 0.85,
                "life": 0.9,
                "radius": 1.25,
                "scale": 0.55,
            },
        },
    },
    "heal_soft_default": {
        "id": "heal_soft_default",
        "nodes": {
            "soft_glow_core": {
                "texture_role": "core",
                "alpha_blend": "Add",
                "color_alpha": 0.85,
                "scale": 1.25,
            },
            "upward_sparkles": {
                "texture_role": "spark",
                "alpha_blend": "Add",
                "generation": 0.9,
                "life": 1.15,
                "radius": 0.8,
                "scale": 0.85,
            },
            "healing_ring": {
                "texture_role": "ring",
                "alpha_blend": "Add",
                "color_alpha": 0.55,
                "life": 1.35,
                "scale": 1.35,
            },
        },
    },
    "elemental_fire_default": {
        "id": "elemental_fire_default",
        "nodes": {
            "core_glow": {
                "texture_role": "core",
                "alpha_blend": "Add",
                "scale": 1.15,
            },
            "element_sparks": {
                "texture_role": "spark",
                "alpha_blend": "Add",
                "generation": 1.15,
                "radius": 1.1,
                "gravity": 1.15,
            },
            "residual_particles": {
                "texture_role": "smoke",
                "alpha_blend": "Blend",
                "color_alpha": 0.62,
                "generation": 1.25,
                "life": 1.25,
                "radius": 0.95,
                "gravity": 0.7,
                "scale": 1.15,
            },
        },
    },
    "projectile_water_default": {
        "id": "projectile_water_default",
        "nodes": {
            "projectile_core": {
                "texture_role": "core",
                "alpha_blend": "Add",
                "scale": 0.9,
            },
            "trail_particles": {
                "texture_role": "trail",
                "alpha_blend": "Add",
                "color_alpha": 0.72,
                "generation": 1.25,
                "life": 1.25,
                "radius": 0.65,
                "gravity": 0.5,
                "scale": 0.55,
            },
            "impact_sparks": {
                "texture_role": "ripple",
                "alpha_blend": "Blend",
                "color_alpha": 0.72,
                "generation": 0.85,
                "life": 1.15,
                "radius": 0.85,
                "gravity": 0.4,
                "scale": 1.2,
            },
        },
    },
}

DEFAULT_PROFILE_BY_RECIPE = {
    "firework_burst": "firework_default",
    "slash": "slash_wind_default",
    "heal_sparkle": "heal_soft_default",
    "elemental_burst": "elemental_fire_default",
    "projectile_trail": "projectile_water_default",
}


def list_visual_profiles() -> list[dict[str, Any]]:
    return [copy.deepcopy(profile) for profile in VISUAL_PROFILES.values()]


def get_visual_profile(profile_id: str) -> dict[str, Any]:
    profile = VISUAL_PROFILES.get(profile_id)
    if profile is None:
        supported = ", ".join(sorted(VISUAL_PROFILES))
        raise VisualProfileError(
            f"unsupported visual profile: {profile_id}. Supported profiles: {supported}"
        )
    return copy.deepcopy(profile)


def resolve_visual_profile(
    profile_id: str | None,
    *,
    recipe_id: str,
    kind: str | None = None,
    element: str | None = None,
) -> dict[str, Any]:
    if profile_id is not None:
        return get_visual_profile(profile_id)

    if recipe_id == "slash" and kind == "fire_slash":
        return get_visual_profile("slash_wind_default")
    if recipe_id == "elemental_burst" and element == "fire":
        return get_visual_profile("elemental_fire_default")
    if recipe_id == "projectile_trail" and element == "water":
        return get_visual_profile("projectile_water_default")

    default_profile = DEFAULT_PROFILE_BY_RECIPE.get(recipe_id)
    if default_profile is None:
        raise VisualProfileError(f"no default visual profile for recipe: {recipe_id}")
    return get_visual_profile(default_profile)


def profile_node(profile: dict[str, Any], node_role: str) -> dict[str, Any]:
    nodes = profile.get("nodes")
    if not isinstance(nodes, dict):
        return {}
    node = nodes.get(node_role)
    return node if isinstance(node, dict) else {}


def texture_role(profile: dict[str, Any], node_role: str, fallback: str) -> str:
    value = profile_node(profile, node_role).get("texture_role", fallback)
    return value if isinstance(value, str) and value else fallback


def alpha_blend(profile: dict[str, Any], node_role: str, fallback: str = "Add") -> str:
    value = profile_node(profile, node_role).get("alpha_blend", fallback)
    return value if isinstance(value, str) and value else fallback


def multiplier(
    profile: dict[str, Any],
    node_role: str,
    key: str,
    fallback: float = 1.0,
) -> float:
    value = profile_node(profile, node_role).get(key, fallback)
    if isinstance(value, bool) or not isinstance(value, int | float):
        return fallback
    return float(value)


def apply_color_alpha(color: dict[str, int], alpha_multiplier: float) -> dict[str, int]:
    adjusted = dict(color)
    alpha = adjusted.get("a", 255)
    if isinstance(alpha, bool) or not isinstance(alpha, int):
        return adjusted
    adjusted["a"] = max(0, min(255, round(alpha * alpha_multiplier)))
    return adjusted

from __future__ import annotations

import pytest

from effekseer_mcp.visual_profiles import (
    VisualProfileError,
    alpha_blend,
    apply_color_alpha,
    list_visual_profiles,
    multiplier,
    resolve_visual_profile,
    texture_role,
)


def test_list_visual_profiles_includes_expected_profiles() -> None:
    profile_ids = {profile["id"] for profile in list_visual_profiles()}

    assert profile_ids == {
        "firework_default",
        "slash_wind_default",
        "heal_soft_default",
        "elemental_fire_default",
        "projectile_water_default",
    }


def test_resolve_visual_profile_uses_default_by_recipe() -> None:
    firework = resolve_visual_profile(None, recipe_id="firework_burst")
    projectile = resolve_visual_profile(
        None,
        recipe_id="projectile_trail",
        element="water",
    )

    assert firework["id"] == "firework_default"
    assert texture_role(firework, "secondary_sparkles", "spark") == "smoke"
    assert alpha_blend(firework, "secondary_sparkles") == "Blend"
    assert projectile["id"] == "projectile_water_default"
    assert texture_role(projectile, "impact_sparks", "spark") == "ripple"


def test_resolve_visual_profile_accepts_explicit_profile() -> None:
    profile = resolve_visual_profile(
        "heal_soft_default",
        recipe_id="projectile_trail",
        element="water",
    )

    assert profile["id"] == "heal_soft_default"


def test_resolve_visual_profile_rejects_unsupported_profile() -> None:
    with pytest.raises(VisualProfileError, match="unsupported visual profile"):
        resolve_visual_profile("not_a_profile", recipe_id="firework_burst")


def test_profile_helpers_apply_multipliers_and_alpha() -> None:
    profile = resolve_visual_profile("slash_wind_default", recipe_id="slash")

    assert multiplier(profile, "slash_arc", "life") == 0.75
    assert multiplier(profile, "missing", "life") == 1.0
    assert apply_color_alpha({"r": 10, "g": 20, "b": 30, "a": 200}, 0.5) == {
        "r": 10,
        "g": 20,
        "b": 30,
        "a": 100,
    }

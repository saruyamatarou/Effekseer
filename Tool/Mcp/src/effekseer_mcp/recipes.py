from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

from effekseer_mcp.bridge_client import EffekseerBridgeClient
from effekseer_mcp.recipe_primitives import (
    add_named_child_node,
    command_summary,
    configure_burst_sparks,
    configure_fade,
    configure_glow_core,
    configure_sprite_common,
    configure_upward_sparkles,
    extract_automation_node_id,
    get_required_value,
    hide_container_node,
)
from effekseer_mcp.recipe_tuning import apply_recipe_tuning
from effekseer_mcp.texture_library import resolve_texture_roles
from effekseer_mcp.visual_profiles import (
    alpha_blend,
    apply_color_alpha,
    multiplier,
    resolve_visual_profile,
    texture_role,
)

AUTOMATION_NODE_ID_KEYS = ("automationNodeId", "automation_node_id")
NODE_NAME_KEYS = ("name", "nodeName", "node_name")
ROOT_KEYS = ("root", "rootNode", "nodeTree", "tree")
EFFECT_SPEC_VERSION = "v0"
SLASH_ELEMENTS = {"neutral", "wind", "fire", "water", "dark", "holy"}
ELEMENTAL_ELEMENTS = {"neutral", "fire", "water", "wind", "dark", "holy"}

EFFECT_RECIPE_REGISTRY: dict[str, dict[str, Any]] = {
    "basic_sprite_burst": {
        "id": "basic_sprite_burst",
        "effect_spec_kinds": ["basic_sprite_burst"],
        "description": (
            "Create one Sprite node, write basic fixed parameters, save .efkefc, "
            "and export .efk."
        ),
        "required_effect_spec_fields": [
            "kind",
            "name",
            "output_project_path",
            "output_effect_path",
            "primary_color",
            "intensity",
            "scale",
        ],
        "optional_effect_spec_fields": [
            "secondary_color",
            "duration",
            "texture_path",
            "visual_profile",
            "sample_tuning",
        ],
    },
    "firework_burst": {
        "id": "firework_burst",
        "effect_spec_kinds": ["firework", "firework_burst"],
        "description": (
            "Create a FireworkRoot node with BurstCore, BurstSparks, and "
            "SecondarySparkles children, save .efkefc, and export .efk."
        ),
        "required_effect_spec_fields": [
            "kind",
            "name",
            "output_project_path",
            "output_effect_path",
            "primary_color",
            "intensity",
            "scale",
        ],
        "optional_effect_spec_fields": [
            "secondary_color",
            "duration",
            "texture_path",
            "texture_set",
            "textures",
            "visual_profile",
            "sample_tuning",
        ],
    },
    "slash": {
        "id": "slash",
        "effect_spec_kinds": ["slash", "wind_slash", "fire_slash"],
        "description": (
            "Create a slash-style Sprite effect with an arc, impact sparks, "
            "and delayed afterimage particles."
        ),
        "required_effect_spec_fields": [
            "kind",
            "name",
            "output_project_path",
            "output_effect_path",
            "primary_color",
            "intensity",
            "scale",
        ],
        "optional_effect_spec_fields": [
            "secondary_color",
            "duration",
            "element",
            "texture_path",
            "texture_set",
            "textures",
            "visual_profile",
            "sample_tuning",
        ],
    },
    "heal_sparkle": {
        "id": "heal_sparkle",
        "effect_spec_kinds": ["heal", "heal_sparkle", "holy_heal"],
        "description": (
            "Create a healing Sprite effect with soft glow, upward sparkles, "
            "and a larger healing ring."
        ),
        "required_effect_spec_fields": [
            "kind",
            "name",
            "output_project_path",
            "output_effect_path",
            "primary_color",
            "intensity",
            "scale",
        ],
        "optional_effect_spec_fields": [
            "secondary_color",
            "duration",
            "texture_path",
            "texture_set",
            "textures",
            "visual_profile",
            "sample_tuning",
        ],
    },
    "elemental_burst": {
        "id": "elemental_burst",
        "effect_spec_kinds": [
            "elemental_burst",
            "fire",
            "water",
            "wind",
            "dark",
            "holy",
        ],
        "description": (
            "Create a reusable elemental burst with core glow, sparks, "
            "and residual particles."
        ),
        "required_effect_spec_fields": [
            "kind",
            "name",
            "output_project_path",
            "output_effect_path",
            "primary_color",
            "intensity",
            "scale",
        ],
        "optional_effect_spec_fields": [
            "secondary_color",
            "duration",
            "element",
            "texture_path",
            "texture_set",
            "textures",
            "visual_profile",
            "sample_tuning",
        ],
    },
    "projectile_trail": {
        "id": "projectile_trail",
        "effect_spec_kinds": [
            "projectile",
            "projectile_trail",
            "fireball",
            "water_projectile",
            "wind_projectile",
            "dark_projectile",
            "holy_projectile",
        ],
        "description": (
            "Create a moving projectile-style Sprite effect with a glowing core, "
            "trail particles, and impact sparks."
        ),
        "required_effect_spec_fields": [
            "kind",
            "name",
            "output_project_path",
            "output_effect_path",
            "primary_color",
            "intensity",
            "scale",
        ],
        "optional_effect_spec_fields": [
            "secondary_color",
            "duration",
            "element",
            "texture_path",
            "texture_set",
            "textures",
            "visual_profile",
            "sample_tuning",
        ],
    },
}

EFFECT_RECIPE_ALIASES = {
    kind: recipe_id
    for recipe_id, recipe in EFFECT_RECIPE_REGISTRY.items()
    for kind in recipe["effect_spec_kinds"]
}


class EffekseerRecipeError(RuntimeError):
    """Raised when a high-level Effekseer recipe cannot complete."""


def list_effect_recipes() -> list[dict[str, Any]]:
    """List high-level effect recipes supported by EffectSpec routing."""
    return [copy_recipe_metadata(recipe) for recipe in EFFECT_RECIPE_REGISTRY.values()]


def describe_effect_recipe(kind: str) -> dict[str, Any]:
    """Describe one high-level effect recipe by recipe id or EffectSpec kind."""
    recipe_id = resolve_effect_recipe_id(kind)
    return copy_recipe_metadata(EFFECT_RECIPE_REGISTRY[recipe_id])


def create_effect_from_spec(
    spec: dict[str, Any],
    *,
    client: Any | None = None,
) -> dict[str, Any]:
    """Route an EffectSpec v0 payload to an allowlisted high-level recipe."""
    if not isinstance(spec, dict):
        raise EffekseerRecipeError("EffectSpec must be an object")

    kind = require_string(spec, "kind")
    recipe_id = resolve_effect_recipe_id(kind)
    name = require_string(spec, "name")
    output_project_path = require_string(spec, "output_project_path")
    output_effect_path = require_string(spec, "output_effect_path")
    primary_color = require_rgba_mapping(spec, "primary_color")
    intensity = require_positive_finite_number(spec, "intensity")
    scale = require_positive_finite_number(spec, "scale")
    duration = optional_positive_int(spec, "duration")
    texture_path = optional_string(spec, "texture_path")
    texture_set = optional_string(spec, "texture_set")
    textures = optional_texture_mapping(spec, "textures")
    visual_profile = optional_string(spec, "visual_profile")
    sample_tuning = optional_sample_tuning(spec, "sample_tuning")

    if recipe_id == "firework_burst":
        result = create_firework_burst_effect(
            name=name,
            output_project_path=output_project_path,
            output_effect_path=output_effect_path,
            primary_color=primary_color,
            secondary_color=optional_rgba_mapping(spec, "secondary_color")
            or primary_color,
            spark_count=max(1, round(48 * intensity)),
            secondary_spark_count=max(1, round(24 * intensity)),
            burst_life=duration or 45,
            secondary_life=max(1, round((duration or 45) * 0.78)),
            burst_radius=80.0 * intensity,
            gravity=-0.15,
            scale=scale,
            texture_path=texture_path,
            texture_set=texture_set,
            textures=textures,
            visual_profile=visual_profile,
            sample_tuning=sample_tuning,
            client=client,
        )
    elif recipe_id == "slash":
        slash_duration = duration or 30
        result = create_slash_effect(
            name=name,
            output_project_path=output_project_path,
            output_effect_path=output_effect_path,
            primary_color=primary_color,
            secondary_color=optional_rgba_mapping(spec, "secondary_color"),
            intensity=intensity,
            scale=scale,
            duration=slash_duration,
            element=optional_string(spec, "element") or infer_slash_element(kind),
            texture_path=texture_path,
            texture_set=texture_set,
            textures=textures,
            visual_profile=visual_profile,
            sample_tuning=sample_tuning,
            client=client,
        )
    elif recipe_id == "heal_sparkle":
        result = create_heal_sparkle_effect(
            name=name,
            output_project_path=output_project_path,
            output_effect_path=output_effect_path,
            primary_color=primary_color,
            secondary_color=optional_rgba_mapping(spec, "secondary_color"),
            intensity=intensity,
            scale=scale,
            duration=duration or 45,
            texture_path=texture_path,
            texture_set=texture_set,
            textures=textures,
            visual_profile=visual_profile,
            sample_tuning=sample_tuning,
            client=client,
        )
    elif recipe_id == "elemental_burst":
        result = create_elemental_burst_effect(
            name=name,
            output_project_path=output_project_path,
            output_effect_path=output_effect_path,
            primary_color=primary_color,
            secondary_color=optional_rgba_mapping(spec, "secondary_color"),
            intensity=intensity,
            scale=scale,
            duration=duration or 40,
            element=optional_string(spec, "element")
            or infer_elemental_element(kind),
            texture_path=texture_path,
            texture_set=texture_set,
            textures=textures,
            visual_profile=visual_profile,
            sample_tuning=sample_tuning,
            client=client,
        )
    elif recipe_id == "projectile_trail":
        result = create_projectile_trail_effect(
            name=name,
            output_project_path=output_project_path,
            output_effect_path=output_effect_path,
            primary_color=primary_color,
            secondary_color=optional_rgba_mapping(spec, "secondary_color"),
            intensity=intensity,
            scale=scale,
            duration=duration or 45,
            element=optional_string(spec, "element")
            or infer_projectile_element(kind),
            texture_path=texture_path,
            texture_set=texture_set,
            textures=textures,
            visual_profile=visual_profile,
            sample_tuning=sample_tuning,
            client=client,
        )
    elif recipe_id == "basic_sprite_burst":
        life_center = duration or 30
        result = create_basic_sprite_burst_effect(
            name=name,
            output_project_path=output_project_path,
            output_effect_path=output_effect_path,
            color=primary_color,
            max_generation=max(1, round(8 * intensity)),
            life={
                "center": life_center,
                "min": max(1, round(life_center * 0.75)),
                "max": max(life_center, round(life_center * 1.25)),
            },
            location={"x": 0.0, "y": 0.0, "z": 0.0},
            rotation={"x": 0.0, "y": 0.0, "z": 0.0},
            scale={"x": scale, "y": scale, "z": scale},
            alpha_blend="Add",
            texture_path=texture_path,
            client=client,
        )
    else:  # pragma: no cover - resolve_effect_recipe_id guards this
        raise EffekseerRecipeError(f"unsupported effect recipe kind: {kind}")

    routed_result = dict(result)
    routed_result["recipe"] = recipe_id
    routed_result["effect_spec_version"] = EFFECT_SPEC_VERSION
    return routed_result


def create_basic_sprite_burst_effect(
    *,
    name: str,
    output_project_path: str,
    output_effect_path: str,
    color: dict[str, int],
    max_generation: int,
    life: dict[str, int],
    location: dict[str, float],
    rotation: dict[str, float],
    scale: dict[str, float],
    alpha_blend: str = "Add",
    texture_path: str | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    """Create and export a simple sprite burst effect using allowlisted commands."""
    bridge = client or EffekseerBridgeClient()
    commands: list[dict[str, Any]] = []
    created_node_id: str | None = None

    try:
        root_id = get_root_automation_node_id(bridge.get_node_tree())
        add_response = bridge.add_node_to_parent_by_automation_id(root_id, name)
        commands.append(command_summary("add_node_to_parent_by_automation_id", add_response))
        created_node_id = extract_automation_node_id(add_response)

        if created_node_id is None:
            tree = bridge.get_node_tree()
            created_node_id = find_automation_node_id_by_name(tree, name)
        if created_node_id is None:
            raise EffekseerRecipeError(f"created node was not found: {name}")

        commands.append(
            command_summary(
                "rename_node_by_automation_id",
                bridge.rename_node_by_automation_id(created_node_id, name),
            )
        )
        commands.append(
            command_summary(
                "set_node_renderer_type_by_automation_id",
                bridge.set_node_renderer_type_by_automation_id(created_node_id, "Sprite"),
            )
        )
        commands.append(
            command_summary(
                "set_node_max_generation_by_automation_id",
                bridge.set_node_max_generation_by_automation_id(
                    created_node_id,
                    max_generation,
                ),
            )
        )
        commands.append(
            command_summary(
                "set_node_life_by_automation_id",
                bridge.set_node_life_by_automation_id(
                    created_node_id,
                    get_required_value(life, "center"),
                    get_required_value(life, "min"),
                    get_required_value(life, "max"),
                ),
            )
        )
        commands.append(
            command_summary(
                "set_node_fixed_location_by_automation_id",
                bridge.set_node_fixed_location_by_automation_id(
                    created_node_id,
                    get_required_value(location, "x"),
                    get_required_value(location, "y"),
                    get_required_value(location, "z"),
                ),
            )
        )
        commands.append(
            command_summary(
                "set_node_fixed_rotation_by_automation_id",
                bridge.set_node_fixed_rotation_by_automation_id(
                    created_node_id,
                    get_required_value(rotation, "x"),
                    get_required_value(rotation, "y"),
                    get_required_value(rotation, "z"),
                ),
            )
        )
        commands.append(
            command_summary(
                "set_node_fixed_scale_by_automation_id",
                bridge.set_node_fixed_scale_by_automation_id(
                    created_node_id,
                    get_required_value(scale, "x"),
                    get_required_value(scale, "y"),
                    get_required_value(scale, "z"),
                ),
            )
        )
        commands.append(
            command_summary(
                "set_node_color_all_fixed_rgba_by_automation_id",
                bridge.set_node_color_all_fixed_rgba_by_automation_id(
                    created_node_id,
                    get_required_value(color, "r"),
                    get_required_value(color, "g"),
                    get_required_value(color, "b"),
                    get_required_value(color, "a"),
                ),
            )
        )
        commands.append(
            command_summary(
                "set_node_alpha_blend_by_automation_id",
                bridge.set_node_alpha_blend_by_automation_id(
                    created_node_id,
                    alpha_blend,
                ),
            )
        )

        if texture_path is not None:
            commands.append(
                command_summary(
                    "set_node_color_texture_from_workspace_by_automation_id",
                    bridge.set_node_color_texture_from_workspace_by_automation_id(
                        created_node_id,
                        texture_path,
                    ),
                )
            )

        project_response = bridge.save_project_to_workspace(output_project_path)
        commands.append(command_summary("save_project_to_workspace", project_response))

        export_response = bridge.export_runtime_effect_to_workspace(output_effect_path)
        commands.append(command_summary("export_runtime_effect_to_workspace", export_response))

        return {
            "automationNodeId": created_node_id,
            "project_path": output_project_path,
            "effect_path": output_effect_path,
            "commands": commands,
        }
    except Exception as exc:
        cleanup_error: Exception | None = None
        if created_node_id is not None:
            try:
                bridge.remove_node_by_automation_id(created_node_id)
            except Exception as cleanup_exc:  # pragma: no cover - defensive wrapper
                cleanup_error = cleanup_exc
        if cleanup_error is not None:
            raise EffekseerRecipeError(
                f"{exc}; cleanup also failed: {cleanup_error}"
            ) from exc
        raise


def resolve_recipe_texture_paths(
    roles: Iterable[str],
    *,
    texture_path: str | None,
    texture_set: str | None,
    textures: dict[str, str] | None,
) -> dict[str, str | None]:
    """Resolve role textures while preserving texture_path backward compatibility."""
    role_list = list(roles)
    if textures is not None or texture_set is not None:
        resolved = resolve_texture_roles(texture_set, textures)
        return {role: resolved.get(role) for role in role_list}
    if texture_path is not None:
        return {role: texture_path for role in role_list}
    resolved = resolve_texture_roles("builtin", None)
    return {role: resolved.get(role) for role in role_list}


def resolve_profile_texture_paths(
    node_roles: dict[str, str],
    *,
    profile: dict[str, Any],
    texture_path: str | None,
    texture_set: str | None,
    textures: dict[str, str] | None,
) -> dict[str, str | None]:
    profile_roles = {
        node_role: texture_role(profile, node_role, fallback_role)
        for node_role, fallback_role in node_roles.items()
    }
    resolved = resolve_recipe_texture_paths(
        set(profile_roles.values()),
        texture_path=texture_path,
        texture_set=texture_set,
        textures=textures,
    )
    return {
        node_role: resolved.get(role)
        for node_role, role in profile_roles.items()
    }


def create_firework_burst_effect(
    *,
    name: str,
    output_project_path: str,
    output_effect_path: str,
    primary_color: dict[str, int],
    secondary_color: dict[str, int],
    spark_count: int = 48,
    secondary_spark_count: int = 24,
    burst_life: int = 45,
    secondary_life: int = 35,
    burst_radius: float = 80.0,
    gravity: float = -0.15,
    scale: float = 1.0,
    texture_path: str | None = None,
    texture_set: str | None = None,
    textures: dict[str, str] | None = None,
    visual_profile: str | None = None,
    sample_tuning: str | dict[str, Any] | None = "auto",
    client: Any | None = None,
) -> dict[str, Any]:
    """Create and export a minimal firework burst using allowlisted commands."""
    bridge = client or EffekseerBridgeClient()
    commands: list[dict[str, Any]] = []
    firework_root_id: str | None = None
    profile = resolve_visual_profile(
        visual_profile,
        recipe_id="firework_burst",
    )
    texture_paths = resolve_profile_texture_paths(
        {
            "burst_core": "core",
            "burst_sparks": "spark",
            "secondary_sparkles": "spark",
        },
        profile=profile,
        texture_path=texture_path,
        texture_set=texture_set,
        textures=textures,
    )
    tuning = apply_recipe_tuning(
        "firework_burst",
        "firework",
        None,
        {
            "spark_count": spark_count,
            "secondary_spark_count": secondary_spark_count,
            "burst_life": burst_life,
            "secondary_life": secondary_life,
            "burst_radius": burst_radius,
            "scale": scale,
            "burst_velocity_factor": 1.0,
            "secondary_velocity_factor": 0.65,
        },
        sample_tuning=sample_tuning,
    )
    tuned = tuning["parameters"]

    try:
        root_id = get_root_automation_node_id(bridge.get_node_tree())
        root_response = bridge.add_node_to_parent_by_automation_id(root_id, name)
        commands.append(command_summary("add_node_to_parent_by_automation_id", root_response))
        firework_root_id = extract_automation_node_id(root_response)

        if firework_root_id is None:
            tree = bridge.get_node_tree()
            firework_root_id = find_automation_node_id_by_name(tree, name)
        if firework_root_id is None:
            raise EffekseerRecipeError(f"created root node was not found: {name}")
        hide_container_node(bridge, commands, firework_root_id)

        burst_core_id = add_named_child_node(
            bridge,
            commands,
            firework_root_id,
            "BurstCore",
        )
        burst_sparks_id = add_named_child_node(
            bridge,
            commands,
            firework_root_id,
            "BurstSparks",
        )
        secondary_sparkles_id = add_named_child_node(
            bridge,
            commands,
            firework_root_id,
            "SecondarySparkles",
        )

        configure_glow_core(
            bridge,
            commands,
            burst_core_id,
            apply_color_alpha(
                primary_color,
                multiplier(profile, "burst_core", "color_alpha"),
            ),
            tuned["scale"] * multiplier(profile, "burst_core", "scale"),
            texture_paths["burst_core"],
            alpha_blend=alpha_blend(profile, "burst_core"),
        )
        configure_burst_sparks(
            bridge,
            commands,
            burst_sparks_id,
            apply_color_alpha(
                primary_color,
                multiplier(profile, "burst_sparks", "color_alpha"),
            ),
            max(1, round(tuned["spark_count"] * multiplier(profile, "burst_sparks", "generation"))),
            max(1, round(tuned["burst_life"] * multiplier(profile, "burst_sparks", "life"))),
            tuned["burst_radius"] * multiplier(profile, "burst_sparks", "radius"),
            gravity * multiplier(profile, "burst_sparks", "gravity"),
            tuned["scale"] * multiplier(profile, "burst_sparks", "scale"),
            generation_time=0.0,
            velocity_factor=tuned["burst_velocity_factor"],
            texture_path=texture_paths["burst_sparks"],
            alpha_blend=alpha_blend(profile, "burst_sparks"),
        )
        configure_burst_sparks(
            bridge,
            commands,
            secondary_sparkles_id,
            apply_color_alpha(
                secondary_color,
                multiplier(profile, "secondary_sparkles", "color_alpha"),
            ),
            max(
                1,
                round(
                    tuned["secondary_spark_count"]
                    * multiplier(profile, "secondary_sparkles", "generation")
                ),
            ),
            max(
                1,
                round(tuned["secondary_life"] * multiplier(profile, "secondary_sparkles", "life")),
            ),
            tuned["burst_radius"] * 0.55 * multiplier(profile, "secondary_sparkles", "radius"),
            gravity * 0.75 * multiplier(profile, "secondary_sparkles", "gravity"),
            tuned["scale"] * 0.55 * multiplier(profile, "secondary_sparkles", "scale"),
            generation_time=0.12,
            velocity_factor=tuned["secondary_velocity_factor"],
            texture_path=texture_paths["secondary_sparkles"],
            alpha_blend=alpha_blend(profile, "secondary_sparkles"),
        )

        project_response = bridge.save_project_to_workspace(output_project_path)
        commands.append(command_summary("save_project_to_workspace", project_response))

        export_response = bridge.export_runtime_effect_to_workspace(output_effect_path)
        commands.append(command_summary("export_runtime_effect_to_workspace", export_response))

        return {
            "automationNodeId": firework_root_id,
            "nodes": {
                "firework_root": firework_root_id,
                "burst_core": burst_core_id,
                "burst_sparks": burst_sparks_id,
                "secondary_sparkles": secondary_sparkles_id,
            },
            "project_path": output_project_path,
            "effect_path": output_effect_path,
            "visual_profile": profile["id"],
            "sample_tuning": tuning,
            "commands": commands,
        }
    except Exception as exc:
        cleanup_error: Exception | None = None
        if firework_root_id is not None:
            try:
                bridge.remove_node_by_automation_id(firework_root_id)
            except Exception as cleanup_exc:  # pragma: no cover - defensive wrapper
                cleanup_error = cleanup_exc
        if cleanup_error is not None:
            raise EffekseerRecipeError(
                f"{exc}; cleanup also failed: {cleanup_error}"
            ) from exc
        raise


def create_slash_effect(
    *,
    name: str,
    output_project_path: str,
    output_effect_path: str,
    primary_color: dict[str, int],
    secondary_color: dict[str, int] | None = None,
    intensity: float = 1.0,
    scale: float = 1.0,
    duration: int = 30,
    element: str = "neutral",
    texture_path: str | None = None,
    texture_set: str | None = None,
    textures: dict[str, str] | None = None,
    visual_profile: str | None = None,
    sample_tuning: str | dict[str, Any] | None = "auto",
    client: Any | None = None,
) -> dict[str, Any]:
    """Create and export a reusable slash effect using allowlisted commands."""
    validate_slash_element(element)
    bridge = client or EffekseerBridgeClient()
    commands: list[dict[str, Any]] = []
    slash_root_id: str | None = None
    profile = resolve_visual_profile(
        visual_profile,
        recipe_id="slash",
        element=element,
    )
    texture_paths = resolve_profile_texture_paths(
        {
            "slash_arc": "slash",
            "impact_sparks": "spark",
            "afterimage_particles": "trail",
        },
        profile=profile,
        texture_path=texture_path,
        texture_set=texture_set,
        textures=textures,
    )
    tuning = apply_recipe_tuning(
        "slash",
        "slash",
        element,
        {
            "scale": scale,
            "duration_life": duration,
            "impact_generation": max(1.0, 18 * intensity),
            "impact_life": max(1.0, duration * 0.55),
            "impact_radius": 32.0 * intensity,
            "impact_scale": scale * 0.45,
            "impact_velocity_factor": 0.7,
            "afterimage_generation": max(1.0, 12 * intensity),
            "afterimage_life": duration,
            "afterimage_radius": 20.0 * intensity,
            "afterimage_scale": scale * 0.35,
            "afterimage_velocity_factor": 0.45,
        },
        sample_tuning=sample_tuning,
    )
    tuned = tuning["parameters"]

    try:
        root_id = get_root_automation_node_id(bridge.get_node_tree())
        root_response = bridge.add_node_to_parent_by_automation_id(root_id, name)
        commands.append(command_summary("add_node_to_parent_by_automation_id", root_response))
        slash_root_id = extract_automation_node_id(root_response)

        if slash_root_id is None:
            tree = bridge.get_node_tree()
            slash_root_id = find_automation_node_id_by_name(tree, name)
        if slash_root_id is None:
            raise EffekseerRecipeError(f"created slash root node was not found: {name}")
        hide_container_node(bridge, commands, slash_root_id)

        slash_arc_id = add_named_child_node(
            bridge,
            commands,
            slash_root_id,
            "SlashArc",
        )
        impact_sparks_id = add_named_child_node(
            bridge,
            commands,
            slash_root_id,
            "ImpactSparks",
        )
        afterimage_particles_id = add_named_child_node(
            bridge,
            commands,
            slash_root_id,
            "AfterimageParticles",
        )

        configure_slash_arc(
            bridge,
            commands,
            slash_arc_id,
            apply_color_alpha(primary_color, multiplier(profile, "slash_arc", "color_alpha")),
            tuned["scale"],
            tuned["duration_life"],
            element,
            texture_paths["slash_arc"],
            alpha_blend=alpha_blend(profile, "slash_arc"),
            life_multiplier=multiplier(profile, "slash_arc", "life"),
            scale_x_multiplier=multiplier(profile, "slash_arc", "scale_x"),
            scale_y_multiplier=multiplier(profile, "slash_arc", "scale_y"),
        )
        configure_burst_sparks(
            bridge,
            commands,
            impact_sparks_id,
            apply_color_alpha(
                primary_color,
                multiplier(profile, "impact_sparks", "color_alpha"),
            ),
            max(1, round(tuned["impact_generation"] * multiplier(profile, "impact_sparks", "generation"))),
            max(1, round(tuned["impact_life"] * multiplier(profile, "impact_sparks", "life"))),
            tuned["impact_radius"] * multiplier(profile, "impact_sparks", "radius"),
            -0.05 * multiplier(profile, "impact_sparks", "gravity"),
            tuned["impact_scale"] * multiplier(profile, "impact_sparks", "scale"),
            generation_time=0.0,
            velocity_factor=tuned["impact_velocity_factor"],
            texture_path=texture_paths["impact_sparks"],
            alpha_blend=alpha_blend(profile, "impact_sparks"),
        )
        configure_burst_sparks(
            bridge,
            commands,
            afterimage_particles_id,
            apply_color_alpha(
                secondary_color or faded_color(primary_color),
                multiplier(profile, "afterimage_particles", "color_alpha"),
            ),
            max(
                1,
                round(
                    tuned["afterimage_generation"]
                    * multiplier(profile, "afterimage_particles", "generation")
                ),
            ),
            max(1, round(tuned["afterimage_life"] * multiplier(profile, "afterimage_particles", "life"))),
            tuned["afterimage_radius"] * multiplier(profile, "afterimage_particles", "radius"),
            0.0 * multiplier(profile, "afterimage_particles", "gravity"),
            tuned["afterimage_scale"] * multiplier(profile, "afterimage_particles", "scale"),
            generation_time=0.08,
            velocity_factor=tuned["afterimage_velocity_factor"],
            texture_path=texture_paths["afterimage_particles"],
            alpha_blend=alpha_blend(profile, "afterimage_particles"),
        )

        project_response = bridge.save_project_to_workspace(output_project_path)
        commands.append(command_summary("save_project_to_workspace", project_response))

        export_response = bridge.export_runtime_effect_to_workspace(output_effect_path)
        commands.append(command_summary("export_runtime_effect_to_workspace", export_response))

        return {
            "automationNodeId": slash_root_id,
            "nodes": {
                "slash_root": slash_root_id,
                "slash_arc": slash_arc_id,
                "impact_sparks": impact_sparks_id,
                "afterimage_particles": afterimage_particles_id,
            },
            "project_path": output_project_path,
            "effect_path": output_effect_path,
            "element": element,
            "visual_profile": profile["id"],
            "sample_tuning": tuning,
            "commands": commands,
        }
    except Exception as exc:
        cleanup_error: Exception | None = None
        if slash_root_id is not None:
            try:
                bridge.remove_node_by_automation_id(slash_root_id)
            except Exception as cleanup_exc:  # pragma: no cover - defensive wrapper
                cleanup_error = cleanup_exc
        if cleanup_error is not None:
            raise EffekseerRecipeError(
                f"{exc}; cleanup also failed: {cleanup_error}"
            ) from exc
        raise


def create_heal_sparkle_effect(
    *,
    name: str,
    output_project_path: str,
    output_effect_path: str,
    primary_color: dict[str, int],
    secondary_color: dict[str, int] | None = None,
    intensity: float = 1.0,
    scale: float = 1.0,
    duration: int = 45,
    texture_path: str | None = None,
    texture_set: str | None = None,
    textures: dict[str, str] | None = None,
    visual_profile: str | None = None,
    sample_tuning: str | dict[str, Any] | None = "auto",
    client: Any | None = None,
) -> dict[str, Any]:
    """Create and export a soft healing sparkle effect using allowlisted commands."""
    bridge = client or EffekseerBridgeClient()
    commands: list[dict[str, Any]] = []
    heal_root_id: str | None = None
    profile = resolve_visual_profile(
        visual_profile,
        recipe_id="heal_sparkle",
    )
    texture_paths = resolve_profile_texture_paths(
        {
            "soft_glow_core": "core",
            "upward_sparkles": "spark",
            "healing_ring": "ring",
        },
        profile=profile,
        texture_path=texture_path,
        texture_set=texture_set,
        textures=textures,
    )
    tuning = apply_recipe_tuning(
        "heal_sparkle",
        "heal",
        "holy",
        {
            "scale": scale,
            "duration_life": duration,
            "spark_generation": max(1.0, 20 * intensity),
            "spark_life": duration,
            "spark_radius": 42.0 * intensity,
            "spark_scale": scale * 0.45,
            "ring_life": duration,
            "ring_scale": scale,
        },
        sample_tuning=sample_tuning,
    )
    tuned = tuning["parameters"]

    try:
        root_id = get_root_automation_node_id(bridge.get_node_tree())
        root_response = bridge.add_node_to_parent_by_automation_id(root_id, name)
        commands.append(command_summary("add_node_to_parent_by_automation_id", root_response))
        heal_root_id = extract_automation_node_id(root_response)

        if heal_root_id is None:
            tree = bridge.get_node_tree()
            heal_root_id = find_automation_node_id_by_name(tree, name)
        if heal_root_id is None:
            raise EffekseerRecipeError(f"created heal root node was not found: {name}")
        hide_container_node(bridge, commands, heal_root_id)

        soft_glow_core_id = add_named_child_node(
            bridge,
            commands,
            heal_root_id,
            "SoftGlowCore",
        )
        upward_sparkles_id = add_named_child_node(
            bridge,
            commands,
            heal_root_id,
            "UpwardSparkles",
        )
        healing_ring_id = add_named_child_node(
            bridge,
            commands,
            heal_root_id,
            "HealingRing",
        )

        configure_glow_core(
            bridge,
            commands,
            soft_glow_core_id,
            apply_color_alpha(
                primary_color,
                multiplier(profile, "soft_glow_core", "color_alpha"),
            ),
            tuned["scale"] * 0.9 * multiplier(profile, "soft_glow_core", "scale"),
            texture_paths["soft_glow_core"],
            alpha_blend=alpha_blend(profile, "soft_glow_core"),
        )
        configure_upward_sparkles(
            bridge,
            commands,
            upward_sparkles_id,
            apply_color_alpha(
                secondary_color or faded_color(primary_color),
                multiplier(profile, "upward_sparkles", "color_alpha"),
            ),
            max(
                1,
                round(tuned["spark_generation"] * multiplier(profile, "upward_sparkles", "generation")),
            ),
            max(1, round(tuned["spark_life"] * multiplier(profile, "upward_sparkles", "life"))),
            tuned["spark_radius"] * multiplier(profile, "upward_sparkles", "radius"),
            tuned["spark_scale"] * multiplier(profile, "upward_sparkles", "scale"),
            generation_time=0.06,
            texture_path=texture_paths["upward_sparkles"],
            alpha_blend=alpha_blend(profile, "upward_sparkles"),
        )
        configure_healing_ring(
            bridge,
            commands,
            healing_ring_id,
            apply_color_alpha(
                secondary_color or faded_color(primary_color),
                multiplier(profile, "healing_ring", "color_alpha"),
            ),
            tuned["ring_scale"] * multiplier(profile, "healing_ring", "scale"),
            tuned["ring_life"],
            intensity,
            texture_paths["healing_ring"],
            alpha_blend=alpha_blend(profile, "healing_ring"),
            life_multiplier=multiplier(profile, "healing_ring", "life"),
        )

        project_response = bridge.save_project_to_workspace(output_project_path)
        commands.append(command_summary("save_project_to_workspace", project_response))

        export_response = bridge.export_runtime_effect_to_workspace(output_effect_path)
        commands.append(command_summary("export_runtime_effect_to_workspace", export_response))

        return {
            "automationNodeId": heal_root_id,
            "nodes": {
                "heal_root": heal_root_id,
                "soft_glow_core": soft_glow_core_id,
                "upward_sparkles": upward_sparkles_id,
                "healing_ring": healing_ring_id,
            },
            "project_path": output_project_path,
            "effect_path": output_effect_path,
            "visual_profile": profile["id"],
            "sample_tuning": tuning,
            "commands": commands,
        }
    except Exception as exc:
        cleanup_error: Exception | None = None
        if heal_root_id is not None:
            try:
                bridge.remove_node_by_automation_id(heal_root_id)
            except Exception as cleanup_exc:  # pragma: no cover - defensive wrapper
                cleanup_error = cleanup_exc
        if cleanup_error is not None:
            raise EffekseerRecipeError(
                f"{exc}; cleanup also failed: {cleanup_error}"
            ) from exc
        raise


def create_elemental_burst_effect(
    *,
    name: str,
    output_project_path: str,
    output_effect_path: str,
    primary_color: dict[str, int],
    secondary_color: dict[str, int] | None = None,
    intensity: float = 1.0,
    scale: float = 1.0,
    duration: int = 40,
    element: str = "fire",
    texture_path: str | None = None,
    texture_set: str | None = None,
    textures: dict[str, str] | None = None,
    visual_profile: str | None = None,
    sample_tuning: str | dict[str, Any] | None = "auto",
    client: Any | None = None,
) -> dict[str, Any]:
    """Create and export a reusable elemental burst using allowlisted commands."""
    validate_elemental_element(element)
    settings = elemental_settings(element)
    bridge = client or EffekseerBridgeClient()
    commands: list[dict[str, Any]] = []
    elemental_root_id: str | None = None
    profile = resolve_visual_profile(
        visual_profile,
        recipe_id="elemental_burst",
        element=element,
    )
    residual_fallback_role = "spark" if element in {"holy", "wind"} else "smoke"
    texture_paths = resolve_profile_texture_paths(
        {
            "core_glow": "core",
            "element_sparks": "spark",
            "residual_particles": residual_fallback_role,
        },
        profile=profile,
        texture_path=texture_path,
        texture_set=texture_set,
        textures=textures,
    )
    tuning = apply_recipe_tuning(
        "elemental_burst",
        "elemental_burst",
        element,
        {
            "scale": scale,
            "duration_life": duration,
            "element_generation": max(1.0, 30 * intensity * settings["spark_count_factor"]),
            "element_life": max(1.0, duration * settings["life_factor"]),
            "element_radius": 46.0 * intensity * settings["radius_factor"],
            "element_scale": scale * settings["spark_scale"],
            "element_velocity_factor": settings["velocity_factor"],
            "residual_generation": max(
                1.0,
                18 * intensity * settings["residual_count_factor"],
            ),
            "residual_life": max(1.0, duration * settings["residual_life_factor"]),
            "residual_radius": (
                36.0 if element == "holy" else 30.0
            )
            * intensity
            * settings["radius_factor"],
            "residual_scale": scale * settings["residual_scale"],
            "residual_velocity_factor": settings["residual_velocity_factor"],
        },
        sample_tuning=sample_tuning,
    )
    tuned = tuning["parameters"]

    try:
        root_id = get_root_automation_node_id(bridge.get_node_tree())
        root_response = bridge.add_node_to_parent_by_automation_id(root_id, name)
        commands.append(command_summary("add_node_to_parent_by_automation_id", root_response))
        elemental_root_id = extract_automation_node_id(root_response)

        if elemental_root_id is None:
            tree = bridge.get_node_tree()
            elemental_root_id = find_automation_node_id_by_name(tree, name)
        if elemental_root_id is None:
            raise EffekseerRecipeError(
                f"created elemental root node was not found: {name}"
            )
        hide_container_node(bridge, commands, elemental_root_id)

        core_glow_id = add_named_child_node(
            bridge,
            commands,
            elemental_root_id,
            "CoreGlow",
        )
        element_sparks_id = add_named_child_node(
            bridge,
            commands,
            elemental_root_id,
            "ElementSparks",
        )
        residual_particles_id = add_named_child_node(
            bridge,
            commands,
            elemental_root_id,
            "ResidualParticles",
        )

        configure_glow_core(
            bridge,
            commands,
            core_glow_id,
            apply_color_alpha(
                primary_color,
                multiplier(profile, "core_glow", "color_alpha"),
            ),
            tuned["scale"] * settings["core_scale"] * multiplier(profile, "core_glow", "scale"),
            texture_paths["core_glow"],
            alpha_blend=alpha_blend(profile, "core_glow"),
        )
        configure_burst_sparks(
            bridge,
            commands,
            element_sparks_id,
            apply_color_alpha(
                primary_color,
                multiplier(profile, "element_sparks", "color_alpha"),
            ),
            max(
                1,
                round(
                    tuned["element_generation"]
                    * multiplier(profile, "element_sparks", "generation")
                ),
            ),
            max(
                1,
                round(
                    tuned["element_life"]
                    * multiplier(profile, "element_sparks", "life")
                ),
            ),
            tuned["element_radius"] * multiplier(profile, "element_sparks", "radius"),
            settings["gravity"] * multiplier(profile, "element_sparks", "gravity"),
            tuned["element_scale"] * multiplier(profile, "element_sparks", "scale"),
            generation_time=0.0,
            velocity_factor=tuned["element_velocity_factor"],
            texture_path=texture_paths["element_sparks"],
            alpha_blend=alpha_blend(profile, "element_sparks"),
        )
        residual_color = apply_color_alpha(
            secondary_color or faded_color(primary_color),
            multiplier(profile, "residual_particles", "color_alpha"),
        )
        residual_generation = max(
            1,
            round(
                tuned["residual_generation"]
                * multiplier(profile, "residual_particles", "generation")
            ),
        )
        residual_life = max(
            1,
            round(
                tuned["residual_life"]
                * multiplier(profile, "residual_particles", "life")
            ),
        )
        if element == "holy":
            configure_upward_sparkles(
                bridge,
                commands,
                residual_particles_id,
                residual_color,
                residual_generation,
                residual_life,
                tuned["residual_radius"] * multiplier(profile, "residual_particles", "radius"),
                tuned["residual_scale"] * multiplier(profile, "residual_particles", "scale"),
                generation_time=0.1,
                texture_path=texture_paths["residual_particles"],
                alpha_blend=alpha_blend(profile, "residual_particles"),
            )
        else:
            configure_burst_sparks(
                bridge,
                commands,
                residual_particles_id,
                residual_color,
                residual_generation,
                residual_life,
                tuned["residual_radius"] * multiplier(profile, "residual_particles", "radius"),
                settings["residual_gravity"]
                * multiplier(profile, "residual_particles", "gravity"),
                tuned["residual_scale"] * multiplier(profile, "residual_particles", "scale"),
                generation_time=0.1,
                velocity_factor=tuned["residual_velocity_factor"],
                texture_path=texture_paths["residual_particles"],
                alpha_blend=alpha_blend(profile, "residual_particles"),
            )

        project_response = bridge.save_project_to_workspace(output_project_path)
        commands.append(command_summary("save_project_to_workspace", project_response))

        export_response = bridge.export_runtime_effect_to_workspace(output_effect_path)
        commands.append(command_summary("export_runtime_effect_to_workspace", export_response))

        return {
            "automationNodeId": elemental_root_id,
            "nodes": {
                "elemental_burst_root": elemental_root_id,
                "core_glow": core_glow_id,
                "element_sparks": element_sparks_id,
                "residual_particles": residual_particles_id,
            },
            "project_path": output_project_path,
            "effect_path": output_effect_path,
            "element": element,
            "visual_profile": profile["id"],
            "sample_tuning": tuning,
            "commands": commands,
        }
    except Exception as exc:
        cleanup_error: Exception | None = None
        if elemental_root_id is not None:
            try:
                bridge.remove_node_by_automation_id(elemental_root_id)
            except Exception as cleanup_exc:  # pragma: no cover - defensive wrapper
                cleanup_error = cleanup_exc
        if cleanup_error is not None:
            raise EffekseerRecipeError(
                f"{exc}; cleanup also failed: {cleanup_error}"
            ) from exc
        raise


def create_projectile_trail_effect(
    *,
    name: str,
    output_project_path: str,
    output_effect_path: str,
    primary_color: dict[str, int],
    secondary_color: dict[str, int] | None = None,
    intensity: float = 1.0,
    scale: float = 1.0,
    duration: int = 45,
    element: str = "fire",
    texture_path: str | None = None,
    texture_set: str | None = None,
    textures: dict[str, str] | None = None,
    visual_profile: str | None = None,
    sample_tuning: str | dict[str, Any] | None = "auto",
    client: Any | None = None,
) -> dict[str, Any]:
    """Create and export a projectile trail effect using allowlisted commands."""
    validate_projectile_element(element)
    settings = projectile_settings(element)
    bridge = client or EffekseerBridgeClient()
    commands: list[dict[str, Any]] = []
    projectile_root_id: str | None = None
    profile = resolve_visual_profile(
        visual_profile,
        recipe_id="projectile_trail",
        element=element,
    )
    texture_paths = resolve_profile_texture_paths(
        {
            "projectile_core": "core",
            "trail_particles": "trail",
            "impact_sparks": "spark",
        },
        profile=profile,
        texture_path=texture_path,
        texture_set=texture_set,
        textures=textures,
    )
    tuning = apply_recipe_tuning(
        "projectile_trail",
        "projectile_trail",
        element,
        {
            "scale": scale,
            "duration_life": duration,
            "trail_generation": max(
                1.0,
                22 * intensity * settings["trail_count_factor"],
            ),
            "trail_life": max(1.0, duration * settings["trail_life_factor"]),
            "trail_radius": 24.0 * intensity * settings["trail_radius_factor"],
            "trail_scale": scale * settings["trail_scale"],
            "trail_velocity_factor": settings["trail_velocity_factor"],
            "impact_generation": max(
                1.0,
                16 * intensity * settings["impact_count_factor"],
            ),
            "impact_life": max(1.0, duration * settings["impact_life_factor"]),
            "impact_radius": 34.0 * intensity * settings["impact_radius_factor"],
            "impact_scale": scale * settings["impact_scale"],
            "impact_velocity_factor": settings["impact_velocity_factor"],
        },
        sample_tuning=sample_tuning,
    )
    tuned = tuning["parameters"]

    try:
        root_id = get_root_automation_node_id(bridge.get_node_tree())
        root_response = bridge.add_node_to_parent_by_automation_id(root_id, name)
        commands.append(command_summary("add_node_to_parent_by_automation_id", root_response))
        projectile_root_id = extract_automation_node_id(root_response)

        if projectile_root_id is None:
            tree = bridge.get_node_tree()
            projectile_root_id = find_automation_node_id_by_name(tree, name)
        if projectile_root_id is None:
            raise EffekseerRecipeError(
                f"created projectile root node was not found: {name}"
            )
        hide_container_node(bridge, commands, projectile_root_id)

        projectile_core_id = add_named_child_node(
            bridge,
            commands,
            projectile_root_id,
            "ProjectileCore",
        )
        trail_particles_id = add_named_child_node(
            bridge,
            commands,
            projectile_root_id,
            "TrailParticles",
        )
        impact_sparks_id = add_named_child_node(
            bridge,
            commands,
            projectile_root_id,
            "ImpactSparks",
        )

        configure_glow_core(
            bridge,
            commands,
            projectile_core_id,
            apply_color_alpha(
                primary_color,
                multiplier(profile, "projectile_core", "color_alpha"),
            ),
            tuned["scale"]
            * settings["core_scale"]
            * multiplier(profile, "projectile_core", "scale"),
            texture_paths["projectile_core"],
            alpha_blend=alpha_blend(profile, "projectile_core"),
        )
        trail_color = apply_color_alpha(
            secondary_color or faded_color(primary_color),
            multiplier(profile, "trail_particles", "color_alpha"),
        )
        configure_burst_sparks(
            bridge,
            commands,
            trail_particles_id,
            trail_color,
            max(
                1,
                round(
                    tuned["trail_generation"]
                    * multiplier(profile, "trail_particles", "generation")
                ),
            ),
            max(
                1,
                round(
                    tuned["trail_life"]
                    * multiplier(profile, "trail_particles", "life")
                ),
            ),
            tuned["trail_radius"] * multiplier(profile, "trail_particles", "radius"),
            settings["trail_gravity"] * multiplier(profile, "trail_particles", "gravity"),
            tuned["trail_scale"] * multiplier(profile, "trail_particles", "scale"),
            generation_time=0.04,
            velocity_factor=tuned["trail_velocity_factor"],
            texture_path=texture_paths["trail_particles"],
            alpha_blend=alpha_blend(profile, "trail_particles"),
        )
        configure_burst_sparks(
            bridge,
            commands,
            impact_sparks_id,
            apply_color_alpha(
                primary_color,
                multiplier(profile, "impact_sparks", "color_alpha"),
            ),
            max(
                1,
                round(
                    tuned["impact_generation"]
                    * multiplier(profile, "impact_sparks", "generation")
                ),
            ),
            max(
                1,
                round(
                    tuned["impact_life"]
                    * multiplier(profile, "impact_sparks", "life")
                ),
            ),
            tuned["impact_radius"] * multiplier(profile, "impact_sparks", "radius"),
            settings["impact_gravity"] * multiplier(profile, "impact_sparks", "gravity"),
            tuned["impact_scale"] * multiplier(profile, "impact_sparks", "scale"),
            generation_time=0.0,
            velocity_factor=tuned["impact_velocity_factor"],
            texture_path=texture_paths["impact_sparks"],
            alpha_blend=alpha_blend(profile, "impact_sparks"),
        )

        project_response = bridge.save_project_to_workspace(output_project_path)
        commands.append(command_summary("save_project_to_workspace", project_response))

        export_response = bridge.export_runtime_effect_to_workspace(output_effect_path)
        commands.append(command_summary("export_runtime_effect_to_workspace", export_response))

        return {
            "automationNodeId": projectile_root_id,
            "nodes": {
                "projectile_root": projectile_root_id,
                "projectile_core": projectile_core_id,
                "trail_particles": trail_particles_id,
                "impact_sparks": impact_sparks_id,
            },
            "project_path": output_project_path,
            "effect_path": output_effect_path,
            "element": element,
            "visual_profile": profile["id"],
            "sample_tuning": tuning,
            "commands": commands,
        }
    except Exception as exc:
        cleanup_error: Exception | None = None
        if projectile_root_id is not None:
            try:
                bridge.remove_node_by_automation_id(projectile_root_id)
            except Exception as cleanup_exc:  # pragma: no cover - defensive wrapper
                cleanup_error = cleanup_exc
        if cleanup_error is not None:
            raise EffekseerRecipeError(
                f"{exc}; cleanup also failed: {cleanup_error}"
            ) from exc
        raise


def configure_healing_ring(
    bridge: Any,
    commands: list[dict[str, Any]],
    automation_node_id: str,
    color: dict[str, int],
    scale: float,
    duration: int,
    intensity: float,
    texture_path: str | None,
    *,
    alpha_blend: str = "Add",
    life_multiplier: float = 1.0,
) -> None:
    configure_sprite_common(
        bridge,
        commands,
        automation_node_id,
        color,
        texture_path,
        alpha_blend=alpha_blend,
    )
    ring_life = max(1, round(duration * 0.8 * life_multiplier))
    commands.append(
        command_summary(
            "set_node_max_generation_by_automation_id",
            bridge.set_node_max_generation_by_automation_id(automation_node_id, 1),
        )
    )
    commands.append(
        command_summary(
            "set_node_life_by_automation_id",
            bridge.set_node_life_by_automation_id(
                automation_node_id,
                ring_life,
                max(1, round(ring_life * 0.8)),
                ring_life,
            ),
        )
    )
    ring_scale = scale * (2.2 + intensity * 0.25)
    commands.append(
        command_summary(
            "set_node_fixed_scale_by_automation_id",
            bridge.set_node_fixed_scale_by_automation_id(
                automation_node_id,
                ring_scale,
                ring_scale,
                scale,
            ),
        )
    )
    configure_fade(
        bridge,
        commands,
        automation_node_id,
        fade_in_type="Use",
        fade_in_frame=max(1.0, ring_life * 0.15),
        fade_out_type="WithinLifetime",
        fade_out_frame=max(1.0, ring_life * 0.55),
    )


def configure_slash_arc(
    bridge: Any,
    commands: list[dict[str, Any]],
    automation_node_id: str,
    color: dict[str, int],
    scale: float,
    duration: int,
    element: str,
    texture_path: str | None,
    *,
    alpha_blend: str = "Add",
    life_multiplier: float = 1.0,
    scale_x_multiplier: float = 1.0,
    scale_y_multiplier: float = 1.0,
) -> None:
    configure_sprite_common(
        bridge,
        commands,
        automation_node_id,
        color,
        texture_path,
        alpha_blend=alpha_blend,
    )
    arc_life = max(1, round(duration * 0.45 * life_multiplier))
    commands.append(
        command_summary(
            "set_node_max_generation_by_automation_id",
            bridge.set_node_max_generation_by_automation_id(automation_node_id, 1),
        )
    )
    commands.append(
        command_summary(
            "set_node_life_by_automation_id",
            bridge.set_node_life_by_automation_id(
                automation_node_id,
                arc_life,
                max(1, round(arc_life * 0.75)),
                arc_life,
            ),
        )
    )
    commands.append(
        command_summary(
            "set_node_fixed_rotation_by_automation_id",
            bridge.set_node_fixed_rotation_by_automation_id(
                automation_node_id,
                0.0,
                0.0,
                slash_rotation_z(element),
            ),
        )
    )
    commands.append(
        command_summary(
            "set_node_fixed_scale_by_automation_id",
            bridge.set_node_fixed_scale_by_automation_id(
                automation_node_id,
                scale * 2.8 * scale_x_multiplier,
                scale * 0.65 * scale_y_multiplier,
                scale,
            ),
        )
    )
    configure_fade(
        bridge,
        commands,
        automation_node_id,
        fade_in_type="Use",
        fade_in_frame=1.0,
        fade_out_type="WithinLifetime",
        fade_out_frame=max(1.0, arc_life * 0.65),
    )


def copy_recipe_metadata(recipe: dict[str, Any]) -> dict[str, Any]:
    copied: dict[str, Any] = {}
    for key, value in recipe.items():
        if isinstance(value, list):
            copied[key] = list(value)
        else:
            copied[key] = value
    return copied


def validate_slash_element(element: str) -> None:
    if element not in SLASH_ELEMENTS:
        supported = ", ".join(sorted(SLASH_ELEMENTS))
        raise EffekseerRecipeError(
            f"unsupported slash element: {element}. Supported elements: {supported}"
        )


def validate_elemental_element(element: str) -> None:
    if element not in ELEMENTAL_ELEMENTS:
        supported = ", ".join(sorted(ELEMENTAL_ELEMENTS))
        raise EffekseerRecipeError(
            f"unsupported elemental element: {element}. Supported elements: {supported}"
        )


def validate_projectile_element(element: str) -> None:
    if element not in ELEMENTAL_ELEMENTS:
        supported = ", ".join(sorted(ELEMENTAL_ELEMENTS))
        raise EffekseerRecipeError(
            f"unsupported projectile element: {element}. Supported elements: {supported}"
        )


def infer_slash_element(kind: str) -> str:
    if kind == "wind_slash":
        return "wind"
    if kind == "fire_slash":
        return "fire"
    return "neutral"


def infer_elemental_element(kind: str) -> str:
    if kind in ELEMENTAL_ELEMENTS:
        return kind
    return "fire"


def infer_projectile_element(kind: str) -> str:
    return {
        "fireball": "fire",
        "water_projectile": "water",
        "wind_projectile": "wind",
        "dark_projectile": "dark",
        "holy_projectile": "holy",
    }.get(kind, "fire")


def elemental_settings(element: str) -> dict[str, float]:
    return {
        "neutral": {
            "core_scale": 1.0,
            "spark_count_factor": 1.0,
            "radius_factor": 1.0,
            "gravity": -0.05,
            "life_factor": 1.0,
            "spark_scale": 0.55,
            "velocity_factor": 0.8,
            "residual_count_factor": 1.0,
            "residual_life_factor": 1.1,
            "residual_gravity": -0.02,
            "residual_scale": 0.35,
            "residual_velocity_factor": 0.55,
        },
        "fire": {
            "core_scale": 1.1,
            "spark_count_factor": 1.15,
            "radius_factor": 1.2,
            "gravity": -0.12,
            "life_factor": 0.95,
            "spark_scale": 0.55,
            "velocity_factor": 0.9,
            "residual_count_factor": 1.0,
            "residual_life_factor": 1.0,
            "residual_gravity": -0.08,
            "residual_scale": 0.34,
            "residual_velocity_factor": 0.55,
        },
        "water": {
            "core_scale": 1.0,
            "spark_count_factor": 1.0,
            "radius_factor": 0.95,
            "gravity": -0.02,
            "life_factor": 1.05,
            "spark_scale": 0.5,
            "velocity_factor": 0.7,
            "residual_count_factor": 1.35,
            "residual_life_factor": 1.2,
            "residual_gravity": -0.01,
            "residual_scale": 0.32,
            "residual_velocity_factor": 0.5,
        },
        "wind": {
            "core_scale": 0.9,
            "spark_count_factor": 1.1,
            "radius_factor": 1.05,
            "gravity": 0.0,
            "life_factor": 0.9,
            "spark_scale": 0.42,
            "velocity_factor": 1.05,
            "residual_count_factor": 1.1,
            "residual_life_factor": 1.05,
            "residual_gravity": 0.03,
            "residual_scale": 0.28,
            "residual_velocity_factor": 0.75,
        },
        "dark": {
            "core_scale": 1.25,
            "spark_count_factor": 0.95,
            "radius_factor": 1.05,
            "gravity": -0.04,
            "life_factor": 1.25,
            "spark_scale": 0.65,
            "velocity_factor": 0.65,
            "residual_count_factor": 1.2,
            "residual_life_factor": 1.35,
            "residual_gravity": -0.03,
            "residual_scale": 0.45,
            "residual_velocity_factor": 0.45,
        },
        "holy": {
            "core_scale": 1.35,
            "spark_count_factor": 1.05,
            "radius_factor": 0.9,
            "gravity": 0.04,
            "life_factor": 1.05,
            "spark_scale": 0.5,
            "velocity_factor": 0.65,
            "residual_count_factor": 1.25,
            "residual_life_factor": 1.15,
            "residual_gravity": 0.04,
            "residual_scale": 0.34,
            "residual_velocity_factor": 0.55,
        },
    }[element]


def projectile_settings(element: str) -> dict[str, float]:
    return {
        "neutral": {
            "core_scale": 0.9,
            "trail_count_factor": 1.0,
            "trail_life_factor": 1.0,
            "trail_radius_factor": 0.75,
            "trail_gravity": 0.0,
            "trail_scale": 0.3,
            "trail_velocity_factor": 0.42,
            "impact_count_factor": 1.0,
            "impact_life_factor": 0.5,
            "impact_radius_factor": 0.9,
            "impact_gravity": -0.08,
            "impact_scale": 0.38,
            "impact_velocity_factor": 0.75,
        },
        "fire": {
            "core_scale": 1.05,
            "trail_count_factor": 1.1,
            "trail_life_factor": 1.05,
            "trail_radius_factor": 0.8,
            "trail_gravity": -0.06,
            "trail_scale": 0.32,
            "trail_velocity_factor": 0.45,
            "impact_count_factor": 1.2,
            "impact_life_factor": 0.55,
            "impact_radius_factor": 1.0,
            "impact_gravity": -0.12,
            "impact_scale": 0.42,
            "impact_velocity_factor": 0.8,
        },
        "water": {
            "core_scale": 0.95,
            "trail_count_factor": 1.25,
            "trail_life_factor": 1.15,
            "trail_radius_factor": 0.65,
            "trail_gravity": -0.02,
            "trail_scale": 0.28,
            "trail_velocity_factor": 0.36,
            "impact_count_factor": 0.9,
            "impact_life_factor": 0.6,
            "impact_radius_factor": 0.8,
            "impact_gravity": -0.05,
            "impact_scale": 0.36,
            "impact_velocity_factor": 0.65,
        },
        "wind": {
            "core_scale": 0.85,
            "trail_count_factor": 1.35,
            "trail_life_factor": 0.9,
            "trail_radius_factor": 1.05,
            "trail_gravity": 0.02,
            "trail_scale": 0.24,
            "trail_velocity_factor": 0.55,
            "impact_count_factor": 1.05,
            "impact_life_factor": 0.45,
            "impact_radius_factor": 1.15,
            "impact_gravity": 0.01,
            "impact_scale": 0.32,
            "impact_velocity_factor": 0.9,
        },
        "dark": {
            "core_scale": 1.15,
            "trail_count_factor": 0.95,
            "trail_life_factor": 1.25,
            "trail_radius_factor": 0.7,
            "trail_gravity": -0.01,
            "trail_scale": 0.36,
            "trail_velocity_factor": 0.35,
            "impact_count_factor": 1.0,
            "impact_life_factor": 0.7,
            "impact_radius_factor": 0.85,
            "impact_gravity": -0.04,
            "impact_scale": 0.48,
            "impact_velocity_factor": 0.6,
        },
        "holy": {
            "core_scale": 1.1,
            "trail_count_factor": 1.2,
            "trail_life_factor": 1.1,
            "trail_radius_factor": 0.75,
            "trail_gravity": 0.05,
            "trail_scale": 0.3,
            "trail_velocity_factor": 0.4,
            "impact_count_factor": 1.15,
            "impact_life_factor": 0.55,
            "impact_radius_factor": 0.95,
            "impact_gravity": 0.04,
            "impact_scale": 0.42,
            "impact_velocity_factor": 0.72,
        },
    }[element]


def slash_rotation_z(element: str) -> float:
    return {
        "neutral": -35.0,
        "wind": -25.0,
        "fire": -45.0,
        "water": -30.0,
        "dark": -40.0,
        "holy": -28.0,
    }[element]


def faded_color(color: dict[str, int]) -> dict[str, int]:
    return {
        "r": get_required_value(color, "r"),
        "g": get_required_value(color, "g"),
        "b": get_required_value(color, "b"),
        "a": min(get_required_value(color, "a"), 128),
    }


def resolve_effect_recipe_id(kind: str) -> str:
    if not isinstance(kind, str) or not kind:
        raise EffekseerRecipeError("EffectSpec kind must be a non-empty string")

    recipe_id = EFFECT_RECIPE_ALIASES.get(kind)
    if recipe_id is None:
        supported = ", ".join(sorted(EFFECT_RECIPE_ALIASES))
        raise EffekseerRecipeError(
            f"unsupported effect recipe kind: {kind}. Supported kinds: {supported}"
        )
    return recipe_id


def require_string(spec: dict[str, Any], key: str) -> str:
    value = spec.get(key)
    if not isinstance(value, str) or not value:
        raise EffekseerRecipeError(f"EffectSpec {key} must be a non-empty string")
    return value


def optional_string(spec: dict[str, Any], key: str) -> str | None:
    value = spec.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise EffekseerRecipeError(f"EffectSpec {key} must be a non-empty string or null")
    return value


def optional_sample_tuning(spec: dict[str, Any], key: str) -> str | dict[str, Any] | None:
    value = spec.get(key)
    if value is None:
        return None
    if isinstance(value, str):
        if value not in {"auto", "off"}:
            raise EffekseerRecipeError(f"EffectSpec {key} must be 'auto' or 'off'")
        return value
    if isinstance(value, dict):
        return value
    raise EffekseerRecipeError(f"EffectSpec {key} must be 'auto', 'off', an object, or null")


def optional_texture_mapping(spec: dict[str, Any], key: str) -> dict[str, str] | None:
    value = spec.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise EffekseerRecipeError(f"EffectSpec {key} must be an object or null")
    mapping: dict[str, str] = {}
    for role, path in value.items():
        if not isinstance(role, str) or not role:
            raise EffekseerRecipeError(f"EffectSpec {key} roles must be strings")
        if not isinstance(path, str) or not path:
            raise EffekseerRecipeError(f"EffectSpec {key}.{role} must be a string")
        mapping[role] = path
    return mapping


def require_rgba_mapping(spec: dict[str, Any], key: str) -> dict[str, int]:
    value = spec.get(key)
    if not isinstance(value, dict):
        raise EffekseerRecipeError(f"EffectSpec {key} must be an RGBA object")
    return {
        channel: require_rgba_channel(value, channel, key)
        for channel in ("r", "g", "b", "a")
    }


def optional_rgba_mapping(spec: dict[str, Any], key: str) -> dict[str, int] | None:
    value = spec.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise EffekseerRecipeError(f"EffectSpec {key} must be an RGBA object or null")
    return {
        channel: require_rgba_channel(value, channel, key)
        for channel in ("r", "g", "b", "a")
    }


def require_rgba_channel(mapping: dict[str, Any], channel: str, label: str) -> int:
    value = mapping.get(channel)
    if isinstance(value, bool) or not isinstance(value, int):
        raise EffekseerRecipeError(f"EffectSpec {label}.{channel} must be an int")
    if value < 0 or value > 255:
        raise EffekseerRecipeError(
            f"EffectSpec {label}.{channel} must be between 0 and 255"
        )
    return value


def require_positive_finite_number(spec: dict[str, Any], key: str) -> float:
    value = spec.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise EffekseerRecipeError(f"EffectSpec {key} must be a finite number")
    float_value = float(value)
    if not math.isfinite(float_value) or float_value <= 0.0:
        raise EffekseerRecipeError(f"EffectSpec {key} must be a positive finite number")
    return float_value


def optional_positive_int(spec: dict[str, Any], key: str) -> int | None:
    value = spec.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise EffekseerRecipeError(f"EffectSpec {key} must be an int or null")
    if value <= 0:
        raise EffekseerRecipeError(f"EffectSpec {key} must be positive")
    return value


def get_root_automation_node_id(tree: dict[str, Any]) -> str:
    root = find_root_node(tree)
    automation_node_id = get_automation_node_id(root)
    if automation_node_id is None:
        raise EffekseerRecipeError("root node does not have an automationNodeId")

    return automation_node_id


def find_root_node(tree: dict[str, Any]) -> dict[str, Any]:
    for key in ROOT_KEYS:
        value = tree.get(key)
        if isinstance(value, dict):
            node = first_node(value)
            if node is not None:
                return node

    nodes = list(iter_nodes(tree))
    if not nodes:
        raise EffekseerRecipeError("node tree did not contain any nodes")

    return nodes[0]


def first_node(value: Any) -> dict[str, Any] | None:
    return next(iter(iter_nodes(value)), None)


def iter_nodes(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        if get_automation_node_id(value) is not None:
            yield value
        for child_value in value.values():
            yield from iter_nodes(child_value)
    elif isinstance(value, list):
        for item in value:
            yield from iter_nodes(item)


def find_automation_node_id_by_name(tree: dict[str, Any], name: str) -> str | None:
    for node in iter_nodes(tree):
        if get_node_name(node) == name:
            return get_automation_node_id(node)

    return None


def get_automation_node_id(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None

    for key in AUTOMATION_NODE_ID_KEYS:
        raw_value = value.get(key)
        if isinstance(raw_value, str) and raw_value:
            return raw_value

    return None


def get_node_name(value: dict[str, Any]) -> str | None:
    for key in NODE_NAME_KEYS:
        raw_value = value.get(key)
        if isinstance(raw_value, str):
            return raw_value

    return None

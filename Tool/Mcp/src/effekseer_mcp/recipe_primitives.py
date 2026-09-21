from __future__ import annotations

from typing import Any

AUTOMATION_NODE_ID_KEYS = ("automationNodeId", "automation_node_id")


class RecipePrimitiveError(RuntimeError):
    """Raised when a reusable recipe primitive cannot complete."""


def add_named_child_node(
    bridge: Any,
    commands: list[dict[str, Any]],
    parent_automation_node_id: str,
    name: str,
) -> str:
    """Add a named child node and append a command summary."""
    response = bridge.add_node_to_parent_by_automation_id(
        parent_automation_node_id,
        name,
    )
    commands.append(command_summary("add_node_to_parent_by_automation_id", response))
    automation_node_id = extract_automation_node_id(response)
    if automation_node_id is None:
        raise RecipePrimitiveError(f"created child node was not found: {name}")

    return automation_node_id


def hide_container_node(
    bridge: Any,
    commands: list[dict[str, Any]],
    automation_node_id: str,
) -> None:
    """Hide a structural container node so only its child effect nodes render."""
    commands.append(
        command_summary(
            "set_node_is_rendered_by_automation_id",
            bridge.set_node_is_rendered_by_automation_id(
                automation_node_id,
                False,
            ),
        )
    )


def configure_sprite_common(
    bridge: Any,
    commands: list[dict[str, Any]],
    automation_node_id: str,
    color: dict[str, int],
    texture_path: str | None = None,
    *,
    alpha_blend: str = "Add",
    renderer_type: str = "Sprite",
) -> None:
    """Configure file-safe common Sprite renderer values."""
    commands.append(
        command_summary(
            "set_node_renderer_type_by_automation_id",
            bridge.set_node_renderer_type_by_automation_id(
                automation_node_id,
                renderer_type,
            ),
        )
    )
    commands.append(
        command_summary(
            "set_node_alpha_blend_by_automation_id",
            bridge.set_node_alpha_blend_by_automation_id(
                automation_node_id,
                alpha_blend,
            ),
        )
    )
    commands.append(
        command_summary(
            "set_node_color_all_fixed_rgba_by_automation_id",
            bridge.set_node_color_all_fixed_rgba_by_automation_id(
                automation_node_id,
                get_required_value(color, "r"),
                get_required_value(color, "g"),
                get_required_value(color, "b"),
                get_required_value(color, "a"),
            ),
        )
    )
    if texture_path is not None:
        commands.append(
            command_summary(
                "set_node_color_texture_from_workspace_by_automation_id",
                bridge.set_node_color_texture_from_workspace_by_automation_id(
                    automation_node_id,
                    texture_path,
                ),
            )
        )


def configure_glow_core(
    bridge: Any,
    commands: list[dict[str, Any]],
    automation_node_id: str,
    color: dict[str, int],
    scale: float,
    texture_path: str | None = None,
    *,
    alpha_blend: str = "Add",
) -> None:
    """Configure a short-lived additive glow core sprite."""
    configure_sprite_common(
        bridge,
        commands,
        automation_node_id,
        color,
        texture_path,
        alpha_blend=alpha_blend,
    )
    commands.append(
        command_summary(
            "set_node_max_generation_by_automation_id",
            bridge.set_node_max_generation_by_automation_id(automation_node_id, 1),
        )
    )
    commands.append(
        command_summary(
            "set_node_life_by_automation_id",
            bridge.set_node_life_by_automation_id(automation_node_id, 12, 8, 14),
        )
    )
    fixed_scale = scale * 3.0
    commands.append(
        command_summary(
            "set_node_fixed_scale_by_automation_id",
            bridge.set_node_fixed_scale_by_automation_id(
                automation_node_id,
                fixed_scale,
                fixed_scale,
                fixed_scale,
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
        fade_out_frame=10.0,
    )


def configure_burst_sparks(
    bridge: Any,
    commands: list[dict[str, Any]],
    automation_node_id: str,
    color: dict[str, int],
    max_generation: int,
    life: int,
    burst_radius: float,
    gravity: float,
    scale: float,
    *,
    generation_time: float,
    velocity_factor: float,
    texture_path: str | None = None,
    alpha_blend: str = "Add",
) -> None:
    """Configure a PVA spark burst moving outward with optional gravity."""
    configure_sprite_common(
        bridge,
        commands,
        automation_node_id,
        color,
        texture_path,
        alpha_blend=alpha_blend,
    )
    commands.append(
        command_summary(
            "set_node_max_generation_by_automation_id",
            bridge.set_node_max_generation_by_automation_id(
                automation_node_id,
                max_generation,
            ),
        )
    )
    commands.append(
        command_summary(
            "set_node_generation_time_by_automation_id",
            bridge.set_node_generation_time_by_automation_id(
                automation_node_id,
                generation_time,
                generation_time,
                generation_time,
            ),
        )
    )
    commands.append(
        command_summary(
            "set_node_life_by_automation_id",
            bridge.set_node_life_by_automation_id(
                automation_node_id,
                life,
                max(1, int(life * 0.75)),
                life,
            ),
        )
    )
    commands.append(
        command_summary(
            "set_node_location_type_by_automation_id",
            bridge.set_node_location_type_by_automation_id(automation_node_id, "PVA"),
        )
    )
    zero = make_random_number(0.0)
    velocity = make_random_vector(
        burst_radius * velocity_factor,
        burst_radius * velocity_factor,
        burst_radius * velocity_factor,
    )
    acceleration = {
        "x": zero,
        "y": make_random_number(gravity),
        "z": zero,
    }
    commands.append(
        command_summary(
            "set_node_location_pva_by_automation_id",
            bridge.set_node_location_pva_by_automation_id(
                automation_node_id,
                make_random_vector(0.0, 0.0, 0.0),
                velocity,
                acceleration,
            ),
        )
    )
    commands.append(
        command_summary(
            "set_node_scale_type_by_automation_id",
            bridge.set_node_scale_type_by_automation_id(automation_node_id, "PVA"),
        )
    )
    commands.append(
        command_summary(
            "set_node_scale_pva_by_automation_id",
            bridge.set_node_scale_pva_by_automation_id(
                automation_node_id,
                make_fixed_random_vector(scale, scale, scale),
                make_fixed_random_vector(
                    -scale / max(float(life), 1.0),
                    -scale / max(float(life), 1.0),
                    -scale / max(float(life), 1.0),
                ),
                make_fixed_random_vector(0.0, 0.0, 0.0),
            ),
        )
    )
    configure_fade(
        bridge,
        commands,
        automation_node_id,
        fade_in_type="None",
        fade_in_frame=1.0,
        fade_out_type="WithinLifetime",
        fade_out_frame=max(1.0, life * 0.4),
    )


def configure_upward_sparkles(
    bridge: Any,
    commands: list[dict[str, Any]],
    automation_node_id: str,
    color: dict[str, int],
    max_generation: int,
    life: int,
    height: float,
    scale: float,
    *,
    generation_time: float = 0.0,
    texture_path: str | None = None,
    alpha_blend: str = "Add",
) -> None:
    """Configure a small upward sparkle burst for heal or magic recipes."""
    configure_burst_sparks(
        bridge,
        commands,
        automation_node_id,
        color,
        max_generation,
        life,
        height,
        gravity=height * 0.01,
        scale=scale,
        generation_time=generation_time,
        velocity_factor=0.35,
        texture_path=texture_path,
        alpha_blend=alpha_blend,
    )


def configure_fade(
    bridge: Any,
    commands: list[dict[str, Any]],
    automation_node_id: str,
    *,
    fade_in_type: str,
    fade_in_frame: float,
    fade_out_type: str,
    fade_out_frame: float,
) -> None:
    """Configure fade-in/fade-out values and append a command summary."""
    commands.append(
        command_summary(
            "set_node_fade_in_out_by_automation_id",
            bridge.set_node_fade_in_out_by_automation_id(
                automation_node_id,
                fade_in_type,
                fade_in_frame,
                fade_out_type,
                fade_out_frame,
            ),
        )
    )


def make_random_number(value: float) -> dict[str, float]:
    return {"center": value, "min": value, "max": value}


def make_random_axis_spread(radius: float) -> dict[str, float]:
    return {"center": 0.0, "min": -radius, "max": radius}


def make_random_vector(
    x_radius: float,
    y_radius: float,
    z_radius: float,
) -> dict[str, dict[str, float]]:
    return {
        "x": make_random_axis_spread(x_radius),
        "y": make_random_axis_spread(y_radius),
        "z": make_random_axis_spread(z_radius),
    }


def make_fixed_random_vector(
    x: float,
    y: float,
    z: float,
) -> dict[str, dict[str, float]]:
    return {
        "x": make_random_number(x),
        "y": make_random_number(y),
        "z": make_random_number(z),
    }


def get_required_value(mapping: dict[str, Any], key: str) -> Any:
    if key not in mapping:
        raise RecipePrimitiveError(f"missing required value: {key}")
    return mapping[key]


def command_summary(command: str, response: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {"command": command}
    if "ok" in response:
        summary["ok"] = response["ok"]
    if "command" in response:
        summary["bridge_command"] = response["command"]

    result = response.get("result")
    if isinstance(result, dict):
        for key in ("path", "bytes", "automationNodeId"):
            if key in result:
                summary[key] = result[key]

    automation_node_id = extract_automation_node_id(response)
    if automation_node_id is not None:
        summary["automationNodeId"] = automation_node_id

    return summary


def get_automation_node_id(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None

    for key in AUTOMATION_NODE_ID_KEYS:
        raw_value = value.get(key)
        if isinstance(raw_value, str) and raw_value:
            return raw_value

    return None


def extract_automation_node_id(response: dict[str, Any]) -> str | None:
    automation_node_id = get_automation_node_id(response)
    if automation_node_id is not None:
        return automation_node_id

    result = response.get("result")
    if isinstance(result, dict):
        automation_node_id = get_automation_node_id(result)
        if automation_node_id is not None:
            return automation_node_id
        for key in ("added_node", "addedNode", "node"):
            value = result.get(key)
            if isinstance(value, dict):
                automation_node_id = get_automation_node_id(value)
                if automation_node_id is not None:
                    return automation_node_id

    for key in ("added_node", "addedNode", "node"):
        value = response.get(key)
        if isinstance(value, dict):
            automation_node_id = get_automation_node_id(value)
            if automation_node_id is not None:
                return automation_node_id

    return None

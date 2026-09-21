from typing import Any

import pytest

from effekseer_mcp.recipe_primitives import (
    RecipePrimitiveError,
    add_named_child_node,
    configure_burst_sparks,
    configure_sprite_common,
    make_fixed_random_vector,
    make_random_number,
    make_random_vector,
)


class FakePrimitiveClient:
    def __init__(self, *, missing_added_node_id: bool = False) -> None:
        self.missing_added_node_id = missing_added_node_id
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def add_node_to_parent_by_automation_id(
        self,
        parent_automation_node_id: str,
        name: str | None = None,
    ) -> dict[str, Any]:
        self.calls.append(
            ("add_node_to_parent_by_automation_id", (parent_automation_node_id, name))
        )
        added_node: dict[str, Any] = {"name": name}
        if not self.missing_added_node_id:
            added_node["automationNodeId"] = "child"
        return {"ok": True, "result": {"added_node": added_node}}

    def set_node_renderer_type_by_automation_id(
        self,
        automation_node_id: str,
        renderer_type: str,
    ) -> dict[str, Any]:
        self.calls.append(
            (
                "set_node_renderer_type_by_automation_id",
                (automation_node_id, renderer_type),
            )
        )
        return {"ok": True}

    def set_node_alpha_blend_by_automation_id(
        self,
        automation_node_id: str,
        alpha_blend: str,
    ) -> dict[str, Any]:
        self.calls.append(
            ("set_node_alpha_blend_by_automation_id", (automation_node_id, alpha_blend))
        )
        return {"ok": True}

    def set_node_color_all_fixed_rgba_by_automation_id(
        self,
        automation_node_id: str,
        r: int,
        g: int,
        b: int,
        a: int,
    ) -> dict[str, Any]:
        self.calls.append(
            (
                "set_node_color_all_fixed_rgba_by_automation_id",
                (automation_node_id, r, g, b, a),
            )
        )
        return {"ok": True}

    def set_node_color_texture_from_workspace_by_automation_id(
        self,
        automation_node_id: str,
        path: str,
    ) -> dict[str, Any]:
        self.calls.append(
            (
                "set_node_color_texture_from_workspace_by_automation_id",
                (automation_node_id, path),
            )
        )
        return {"ok": True, "result": {"path": path}}

    def set_node_max_generation_by_automation_id(
        self,
        automation_node_id: str,
        max_generation: int,
    ) -> dict[str, Any]:
        self.calls.append(
            (
                "set_node_max_generation_by_automation_id",
                (automation_node_id, max_generation),
            )
        )
        return {"ok": True}

    def set_node_generation_time_by_automation_id(
        self,
        automation_node_id: str,
        center: float,
        min: float,
        max: float,
    ) -> dict[str, Any]:
        self.calls.append(
            (
                "set_node_generation_time_by_automation_id",
                (automation_node_id, center, min, max),
            )
        )
        return {"ok": True}

    def set_node_life_by_automation_id(
        self,
        automation_node_id: str,
        center: int,
        min: int,
        max: int,
    ) -> dict[str, Any]:
        self.calls.append(
            ("set_node_life_by_automation_id", (automation_node_id, center, min, max))
        )
        return {"ok": True}

    def set_node_location_type_by_automation_id(
        self,
        automation_node_id: str,
        location_type: str,
    ) -> dict[str, Any]:
        self.calls.append(
            ("set_node_location_type_by_automation_id", (automation_node_id, location_type))
        )
        return {"ok": True}

    def set_node_location_pva_by_automation_id(
        self,
        automation_node_id: str,
        location: dict[str, dict[str, float]],
        velocity: dict[str, dict[str, float]],
        acceleration: dict[str, dict[str, float]],
    ) -> dict[str, Any]:
        self.calls.append(
            (
                "set_node_location_pva_by_automation_id",
                (automation_node_id, location, velocity, acceleration),
            )
        )
        return {"ok": True}

    def set_node_scale_type_by_automation_id(
        self,
        automation_node_id: str,
        scale_type: str,
    ) -> dict[str, Any]:
        self.calls.append(
            ("set_node_scale_type_by_automation_id", (automation_node_id, scale_type))
        )
        return {"ok": True}

    def set_node_scale_pva_by_automation_id(
        self,
        automation_node_id: str,
        scale: dict[str, dict[str, float]],
        velocity: dict[str, dict[str, float]],
        acceleration: dict[str, dict[str, float]],
    ) -> dict[str, Any]:
        self.calls.append(
            (
                "set_node_scale_pva_by_automation_id",
                (automation_node_id, scale, velocity, acceleration),
            )
        )
        return {"ok": True}

    def set_node_fade_in_out_by_automation_id(
        self,
        automation_node_id: str,
        fade_in_type: str,
        fade_in_frame: float,
        fade_out_type: str,
        fade_out_frame: float,
    ) -> dict[str, Any]:
        self.calls.append(
            (
                "set_node_fade_in_out_by_automation_id",
                (
                    automation_node_id,
                    fade_in_type,
                    fade_in_frame,
                    fade_out_type,
                    fade_out_frame,
                ),
            )
        )
        return {"ok": True}


def test_add_named_child_node_appends_summary_and_returns_automation_id() -> None:
    client = FakePrimitiveClient()
    commands: list[dict[str, Any]] = []

    automation_node_id = add_named_child_node(client, commands, "root", "Child")

    assert automation_node_id == "child"
    assert commands == [
        {
            "command": "add_node_to_parent_by_automation_id",
            "ok": True,
            "automationNodeId": "child",
        }
    ]


def test_add_named_child_node_rejects_missing_automation_id() -> None:
    client = FakePrimitiveClient(missing_added_node_id=True)

    with pytest.raises(RecipePrimitiveError, match="created child node was not found"):
        add_named_child_node(client, [], "root", "Child")


def test_configure_sprite_common_sets_sprite_color_alpha_and_texture() -> None:
    client = FakePrimitiveClient()
    commands: list[dict[str, Any]] = []

    configure_sprite_common(
        client,
        commands,
        "node",
        {"r": 1, "g": 2, "b": 3, "a": 4},
        "inputs/textures/smoke_color.png",
    )

    assert client.calls == [
        ("set_node_renderer_type_by_automation_id", ("node", "Sprite")),
        ("set_node_alpha_blend_by_automation_id", ("node", "Add")),
        ("set_node_color_all_fixed_rgba_by_automation_id", ("node", 1, 2, 3, 4)),
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("node", "inputs/textures/smoke_color.png"),
        ),
    ]
    assert [command["command"] for command in commands] == [
        "set_node_renderer_type_by_automation_id",
        "set_node_alpha_blend_by_automation_id",
        "set_node_color_all_fixed_rgba_by_automation_id",
        "set_node_color_texture_from_workspace_by_automation_id",
    ]


def test_configure_burst_sparks_writes_pva_motion_scale_and_fade() -> None:
    client = FakePrimitiveClient()

    configure_burst_sparks(
        client,
        [],
        "spark",
        {"r": 255, "g": 128, "b": 32, "a": 255},
        12,
        30,
        80.0,
        -0.15,
        1.0,
        generation_time=0.0,
        velocity_factor=0.5,
    )

    assert ("set_node_location_type_by_automation_id", ("spark", "PVA")) in client.calls
    assert ("set_node_scale_type_by_automation_id", ("spark", "PVA")) in client.calls
    assert (
        "set_node_fade_in_out_by_automation_id",
        ("spark", "None", 1.0, "WithinLifetime", 12.0),
    ) in client.calls


def test_random_payload_helpers() -> None:
    assert make_random_number(2.0) == {"center": 2.0, "min": 2.0, "max": 2.0}
    assert make_random_vector(3.0, 4.0, 5.0) == {
        "x": {"center": 0.0, "min": -3.0, "max": 3.0},
        "y": {"center": 0.0, "min": -4.0, "max": 4.0},
        "z": {"center": 0.0, "min": -5.0, "max": 5.0},
    }
    assert make_fixed_random_vector(1.0, 2.0, 3.0) == {
        "x": {"center": 1.0, "min": 1.0, "max": 1.0},
        "y": {"center": 2.0, "min": 2.0, "max": 2.0},
        "z": {"center": 3.0, "min": 3.0, "max": 3.0},
    }

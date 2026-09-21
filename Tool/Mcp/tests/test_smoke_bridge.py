import math
from io import StringIO
from typing import Any

import pytest

from effekseer_mcp.smoke_bridge import (
    DRAWING_PARAMETERS_REQUIRED_KEYS,
    DrawingRendererWriteValues,
    EXPECTED_PARAMETER_GROUPS,
    LifeValues,
    MaxGenerationValue,
    MotionTimingFadeWriteValues,
    RENDERER_PARAMETERS_REQUIRED_KEYS,
    REQUIRED_BRIDGE_COMMANDS,
    RandomFloatValues,
    RgbaValues,
    SpriteCornerColors,
    TRANSFORM_PARAMETERS_REQUIRED_KEYS,
    VectorRandomValues,
    VectorValues,
    SmokeBridgeError,
    assert_basic_info,
    assert_bridge_capabilities,
    assert_parameter_groups,
    assert_required_parameter_keys,
    assert_texture_reference_has_value,
    extract_enum_payload,
    extract_rgba_payload,
    find_automation_node_id_by_name,
    find_node_id_by_name,
    find_root_node,
    find_run_smoke_node_names,
    get_drawing_renderer_write_values,
    get_generation_write_values,
    get_max_generation_write_response_value,
    get_motion_timing_fade_write_values,
    get_transform_write_values,
    make_smoke_names,
    restore_drawing_renderer_write_values,
    restore_motion_timing_fade_write_values,
    run_smoke_test,
    warn_about_duplicate_node_ids,
)


def vector_to_dict(values: tuple[float, float, float]) -> dict[str, float]:
    return {"x": values[0], "y": values[1], "z": values[2]}


def pva_vector_payload() -> dict[str, dict[str, float]]:
    return {
        "x": {"center": 999.0, "min": 998.0, "max": 1000.0},
        "y": {"center": 999.0, "min": 998.0, "max": 1000.0},
        "z": {"center": 999.0, "min": 998.0, "max": 1000.0},
    }


def random_payload(values: tuple[float, float, float]) -> dict[str, float]:
    return {"center": values[0], "min": values[1], "max": values[2]}


def vector_random_payload(
    values: tuple[
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
    ],
) -> dict[str, dict[str, float]]:
    return {
        "x": random_payload(values[0]),
        "y": random_payload(values[1]),
        "z": random_payload(values[2]),
    }


class FakeBridgeClient:
    def __init__(
        self,
        *,
        include_legacy_renamed: bool = False,
        capability_commands: set[str] | None = None,
        capabilities_response: dict[str, Any] | None = None,
    ) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self.smoke_root_present = False
        self.smoke_root_automation_node_id = "auto-smoke-root"
        self.smoke_root_name = ""
        self.node_name = ""
        self.added_automation_node_id = "auto-child"
        self.duplicate_name = ""
        self.duplicate_automation_node_id = "auto-duplicate"
        self.wrapper_name = ""
        self.wrapper_automation_node_id = "auto-wrapper"
        self.wrapper_present = False
        self.legacy_renamed_present = include_legacy_renamed
        self.legacy_renamed_automation_node_id = "auto-legacy-renamed"
        self.is_rendered = True
        self.max_generation = 1
        self.life = (10, 2, 20)
        self.generation_time = (1.0, 1.0, 1.0)
        self.location = (0.0, 0.0, 0.0)
        self.rotation = (0.0, 0.0, 0.0)
        self.scale = (1.0, 1.0, 1.0)
        self.location_type = "Fixed"
        self.location_pva = (
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0),
        )
        self.velocity_pva = (
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0),
        )
        self.acceleration_pva = (
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0),
        )
        self.scale_type = "Fixed"
        self.scale_pva = (
            (1.0, 1.0, 1.0),
            (1.0, 1.0, 1.0),
            (1.0, 1.0, 1.0),
        )
        self.scale_velocity_pva = (
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0),
        )
        self.scale_acceleration_pva = (
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0),
        )
        self.renderer_type = "Sprite"
        self.color_all = {"r": 255, "g": 255, "b": 255, "a": 255}
        self.corner_colors = {
            "lowerLeft": {"r": 255, "g": 255, "b": 255, "a": 255},
            "lowerRight": {"r": 255, "g": 255, "b": 255, "a": 255},
            "upperLeft": {"r": 255, "g": 255, "b": 255, "a": 255},
            "upperRight": {"r": 255, "g": 255, "b": 255, "a": 255},
        }
        self.alpha_blend = "Blend"
        self.z_write = True
        self.z_test = True
        self.fade_in_type = "None"
        self.fade_in_frame = 1.0
        self.fade_out_type = "None"
        self.fade_out_frame = 1.0
        self.color_texture_path: str | None = None
        self.normal_texture_path: str | None = None
        self.material_path: str | None = None
        self.model_path: str | None = None
        self.undo_stack: list[tuple[str, Any]] = []
        self.redo_stack: list[tuple[str, Any]] = []
        self.capability_commands = capability_commands or set(REQUIRED_BRIDGE_COMMANDS)
        self.capabilities_response = capabilities_response

    def ping(self) -> dict[str, bool]:
        self.calls.append(("ping", ()))
        return {"ok": True}

    def get_status(self) -> dict[str, str]:
        self.calls.append(("get_status", ()))
        return {"status": "ok"}

    def get_bridge_capabilities(self) -> dict[str, Any]:
        self.calls.append(("get_bridge_capabilities", ()))
        if self.capabilities_response is not None:
            return self.capabilities_response

        return {
            "ok": True,
            "result": {"commands": sorted(self.capability_commands)},
        }

    def get_workspace_status(self) -> dict[str, Any]:
        self.calls.append(("get_workspace_status", ()))
        return {"ok": True, "result": {"enabled": True, "exists": True}}

    def save_project_to_workspace(self, path: str) -> dict[str, bool]:
        self.calls.append(("save_project_to_workspace", (path,)))
        return {"ok": True, "result": {"path": path}}

    def open_project_from_workspace(self, path: str) -> dict[str, bool]:
        self.calls.append(("open_project_from_workspace", (path,)))
        return {"ok": True, "result": {"path": path, "status": {"running": True}}}

    def export_runtime_effect_to_workspace(self, path: str) -> dict[str, Any]:
        self.calls.append(("export_runtime_effect_to_workspace", (path,)))
        return {"ok": True, "result": {"path": path, "bytes": 128}}

    def get_node_tree(self) -> dict[str, Any]:
        self.calls.append(("get_node_tree", ()))
        root_children: list[dict[str, Any]] = []
        smoke_root_children: list[dict[str, Any]] = []
        if self.legacy_renamed_present:
            root_children.append(
                {
                    "automationNodeId": self.legacy_renamed_automation_node_id,
                    "name": "SmokeTestRenamed",
                    "children": [],
                }
            )
        if self.node_name:
            smoke_root_children.append(
                {
                    "automationNodeId": self.added_automation_node_id,
                    "name": self.node_name,
                    "children": [],
                }
            )
        if self.duplicate_name:
            duplicate_node = {
                "automationNodeId": self.duplicate_automation_node_id,
                "name": self.duplicate_name,
                "children": [],
            }
            if self.wrapper_present:
                smoke_root_children.append(
                    {
                        "automationNodeId": self.wrapper_automation_node_id,
                        "name": self.wrapper_name,
                        "children": [duplicate_node],
                    }
                )
            else:
                smoke_root_children.append(duplicate_node)

        if self.smoke_root_present:
            root_children.append(
                {
                    "automationNodeId": self.smoke_root_automation_node_id,
                    "name": self.smoke_root_name,
                    "children": smoke_root_children,
                }
            )

        return {
            "root": {
                "automationNodeId": "auto-root",
                "name": "Root",
                "children": root_children,
            }
        }

    def add_node_to_parent_by_automation_id(
        self,
        parent_automation_node_id: str,
        name: str | None = None,
    ) -> dict[str, str]:
        self.calls.append(
            ("add_node_to_parent_by_automation_id", (parent_automation_node_id, name))
        )
        if parent_automation_node_id == "auto-root":
            self.smoke_root_present = True
            self.smoke_root_name = name or "SmokeRoot"
            return {"automationNodeId": self.smoke_root_automation_node_id}

        self.node_name = name or "Node"
        return {"automationNodeId": self.added_automation_node_id}

    def rename_node_by_automation_id(
        self,
        automation_node_id: str,
        name: str,
    ) -> dict[str, bool]:
        self.calls.append(("rename_node_by_automation_id", (automation_node_id, name)))
        self.node_name = name
        return {"ok": True}

    def get_node_basic_info_by_automation_id(
        self,
        automation_node_id: str,
    ) -> dict[str, Any]:
        self.calls.append(("get_node_basic_info_by_automation_id", (automation_node_id,)))
        return {
            "ok": True,
            "result": {
                "automationNodeId": automation_node_id,
                "name": self.node_name,
                "childCount": 0,
                "isRendered": self.is_rendered,
                "nodeType": "Normal",
                "className": "Effekseer.InternalScript.EffectNode",
            },
        }

    def get_node_parameter_groups_by_automation_id(
        self,
        automation_node_id: str,
    ) -> dict[str, Any]:
        self.calls.append(
            ("get_node_parameter_groups_by_automation_id", (automation_node_id,))
        )
        return {
            "ok": True,
            "result": {
                "groups": [
                    "node_base",
                    "common",
                    "generation",
                    "location",
                    "rotation",
                    "scale",
                ]
            },
        }

    def get_node_base_parameters_by_automation_id(
        self,
        automation_node_id: str,
    ) -> dict[str, Any]:
        self.calls.append(("get_node_base_parameters_by_automation_id", (automation_node_id,)))
        return {
            "ok": True,
            "result": {
                "automationNodeId": automation_node_id,
                "name": self.node_name,
                "childCount": 0,
                "isRendered": self.is_rendered,
                "nodeType": "Normal",
                "className": "Effekseer.InternalScript.EffectNode",
            },
        }

    def set_node_is_rendered_by_automation_id(
        self,
        automation_node_id: str,
        is_rendered: bool,
    ) -> dict[str, bool]:
        self.calls.append(
            (
                "set_node_is_rendered_by_automation_id",
                (automation_node_id, is_rendered),
            )
        )
        self.undo_stack.append(("is_rendered", self.is_rendered))
        self.redo_stack.clear()
        self.is_rendered = is_rendered
        return {"ok": True}

    def get_node_generation_parameters_by_automation_id(
        self,
        automation_node_id: str,
    ) -> dict[str, Any]:
        self.calls.append(
            ("get_node_generation_parameters_by_automation_id", (automation_node_id,))
        )
        return {
            "ok": True,
            "result": {
                "automationNodeId": automation_node_id,
                "name": self.node_name,
                "maxGeneration": {
                    "value": self.max_generation,
                    "infinite": False,
                },
                "life": {
                    "center": self.life[0],
                    "min": self.life[1],
                    "max": self.life[2],
                },
                "generation": {
                    "generationTime": random_payload(self.generation_time),
                    "generationTimeOffset": random_payload((0.0, 0.0, 0.0)),
                },
            },
        }

    def get_node_transform_parameters_by_automation_id(
        self,
        automation_node_id: str,
    ) -> dict[str, Any]:
        self.calls.append(
            ("get_node_transform_parameters_by_automation_id", (automation_node_id,))
        )
        return {
            "ok": True,
            "result": {
                "automationNodeId": automation_node_id,
                "name": self.node_name,
                "location": {
                    "type": {
                        "value": self.location_type,
                        "valueId": 1 if self.location_type == "PVA" else 0,
                    },
                    "fixed": {"location": vector_to_dict(self.location)},
                    "pva": {
                        "location": vector_random_payload(self.location_pva),
                        "velocity": vector_random_payload(self.velocity_pva),
                        "acceleration": vector_random_payload(self.acceleration_pva),
                    },
                },
                "rotation": {
                    "fixed": {"rotation": vector_to_dict(self.rotation)},
                    "pva": {"rotation": pva_vector_payload()},
                },
                "scale": {
                    "type": {
                        "value": self.scale_type,
                        "valueId": 1 if self.scale_type == "PVA" else 0,
                    },
                    "fixed": {"scale": vector_to_dict(self.scale)},
                    "pva": {
                        "scale": vector_random_payload(self.scale_pva),
                        "velocity": vector_random_payload(self.scale_velocity_pva),
                        "acceleration": vector_random_payload(
                            self.scale_acceleration_pva
                        ),
                    },
                },
            },
        }

    def get_node_drawing_parameters_by_automation_id(
        self,
        automation_node_id: str,
    ) -> dict[str, Any]:
        self.calls.append(
            ("get_node_drawing_parameters_by_automation_id", (automation_node_id,))
        )
        return {
            "ok": True,
            "result": {
                "automationNodeId": automation_node_id,
                "name": self.node_name,
                "rendererType": {
                    "value": self.renderer_type,
                    "valueId": 0 if self.renderer_type == "Sprite" else 1,
                },
                "textureUVType": "Default",
                "colorAll": {
                    "type": {"value": "Fixed", "valueId": 0},
                    "fixed": self.color_all,
                    "random": {},
                    "easing": {},
                    "fcurve": {},
                    "gradient": {},
                },
                "sprite": {
                    "summary": "default sprite drawing",
                    "fixedColors": self.corner_colors,
                },
                "model": {
                    "model": {
                        "hasValue": self.model_path is not None,
                        "path": self.model_path,
                    }
                },
            },
        }

    def get_node_renderer_parameters_by_automation_id(
        self,
        automation_node_id: str,
    ) -> dict[str, Any]:
        self.calls.append(
            ("get_node_renderer_parameters_by_automation_id", (automation_node_id,))
        )
        return {
            "ok": True,
            "result": {
                "automationNodeId": automation_node_id,
                "name": self.node_name,
                "material": {
                    "type": {
                        "value": "File" if self.material_path is not None else "Default",
                        "valueId": 1 if self.material_path is not None else 0,
                    },
                    "materialFile": {
                        "hasValue": self.material_path is not None,
                        "path": self.material_path,
                    },
                },
                "textures": [],
                "colorTexture": {
                    "reference": {
                        "hasValue": self.color_texture_path is not None,
                        "path": self.color_texture_path,
                    }
                },
                "normalTexture": {
                    "reference": {
                        "hasValue": self.normal_texture_path is not None,
                        "path": self.normal_texture_path,
                    }
                },
                "blend": {
                    "type": "alpha",
                    "alphaBlend": {
                        "value": self.alpha_blend,
                        "valueId": 0 if self.alpha_blend == "Blend" else 1,
                    },
                    "zWrite": self.z_write,
                    "zTest": self.z_test,
                },
                "fade": {
                    "fadeInType": {
                        "value": self.fade_in_type,
                        "valueId": 1 if self.fade_in_type == "Use" else 0,
                    },
                    "fadeIn": {"frame": {"value": self.fade_in_frame}},
                    "fadeOutType": {
                        "value": self.fade_out_type,
                        "valueId": 1 if self.fade_out_type != "None" else 0,
                    },
                    "fadeOut": {"frame": {"value": self.fade_out_frame}},
                },
                "uv": {"summary": "default uv"},
            },
        }

    def set_node_max_generation_by_automation_id(
        self,
        automation_node_id: str,
        max_generation: int,
    ) -> dict[str, bool]:
        self.calls.append(
            (
                "set_node_max_generation_by_automation_id",
                (automation_node_id, max_generation),
            )
        )
        self.undo_stack.append(("max_generation", self.max_generation))
        self.redo_stack.clear()
        self.max_generation = max_generation
        return {"ok": True}

    def set_node_life_by_automation_id(
        self,
        automation_node_id: str,
        center: int,
        min: int,
        max: int,
    ) -> dict[str, bool]:
        self.calls.append(
            (
                "set_node_life_by_automation_id",
                (automation_node_id, center, min, max),
            )
        )
        self.undo_stack.append(("life", self.life))
        self.redo_stack.clear()
        self.life = (center, min, max)
        return {"ok": True}

    def set_node_fixed_location_by_automation_id(
        self,
        automation_node_id: str,
        x: float,
        y: float,
        z: float,
    ) -> dict[str, bool]:
        self.calls.append(
            (
                "set_node_fixed_location_by_automation_id",
                (automation_node_id, x, y, z),
            )
        )
        self.undo_stack.append(("location", self.location))
        self.redo_stack.clear()
        self.location = (x, y, z)
        return {"ok": True}

    def set_node_fixed_rotation_by_automation_id(
        self,
        automation_node_id: str,
        x: float,
        y: float,
        z: float,
    ) -> dict[str, bool]:
        self.calls.append(
            (
                "set_node_fixed_rotation_by_automation_id",
                (automation_node_id, x, y, z),
            )
        )
        self.undo_stack.append(("rotation", self.rotation))
        self.redo_stack.clear()
        self.rotation = (x, y, z)
        return {"ok": True}

    def set_node_fixed_scale_by_automation_id(
        self,
        automation_node_id: str,
        x: float,
        y: float,
        z: float,
    ) -> dict[str, bool]:
        self.calls.append(
            (
                "set_node_fixed_scale_by_automation_id",
                (automation_node_id, x, y, z),
            )
        )
        self.undo_stack.append(("scale", self.scale))
        self.redo_stack.clear()
        self.scale = (x, y, z)
        return {"ok": True}

    def set_node_generation_time_by_automation_id(
        self,
        automation_node_id: str,
        center: float,
        min: float,
        max: float,
    ) -> dict[str, bool]:
        self.calls.append(
            (
                "set_node_generation_time_by_automation_id",
                (automation_node_id, center, min, max),
            )
        )
        self.undo_stack.append(("generation_time", self.generation_time))
        self.redo_stack.clear()
        self.generation_time = (center, min, max)
        return {"ok": True}

    def set_node_location_type_by_automation_id(
        self,
        automation_node_id: str,
        location_type: str,
    ) -> dict[str, bool]:
        self.calls.append(
            ("set_node_location_type_by_automation_id", (automation_node_id, location_type))
        )
        self.undo_stack.append(("location_type", self.location_type))
        self.redo_stack.clear()
        self.location_type = location_type
        return {"ok": True}

    def set_node_location_pva_by_automation_id(
        self,
        automation_node_id: str,
        location: dict[str, dict[str, float]],
        velocity: dict[str, dict[str, float]],
        acceleration: dict[str, dict[str, float]],
    ) -> dict[str, bool]:
        self.calls.append(
            (
                "set_node_location_pva_by_automation_id",
                (automation_node_id, location, velocity, acceleration),
            )
        )
        self.undo_stack.append(
            (
                "location_pva",
                (self.location_pva, self.velocity_pva, self.acceleration_pva),
            )
        )
        self.redo_stack.clear()
        self.location_pva = self._tuple_vector_random(location)
        self.velocity_pva = self._tuple_vector_random(velocity)
        self.acceleration_pva = self._tuple_vector_random(acceleration)
        return {"ok": True}

    def set_node_scale_type_by_automation_id(
        self,
        automation_node_id: str,
        scale_type: str,
    ) -> dict[str, bool]:
        self.calls.append(
            ("set_node_scale_type_by_automation_id", (automation_node_id, scale_type))
        )
        self.undo_stack.append(("scale_type", self.scale_type))
        self.redo_stack.clear()
        self.scale_type = scale_type
        return {"ok": True}

    def set_node_scale_pva_by_automation_id(
        self,
        automation_node_id: str,
        scale: dict[str, dict[str, float]],
        velocity: dict[str, dict[str, float]],
        acceleration: dict[str, dict[str, float]],
    ) -> dict[str, bool]:
        self.calls.append(
            (
                "set_node_scale_pva_by_automation_id",
                (automation_node_id, scale, velocity, acceleration),
            )
        )
        self.undo_stack.append(
            (
                "scale_pva",
                (self.scale_pva, self.scale_velocity_pva, self.scale_acceleration_pva),
            )
        )
        self.redo_stack.clear()
        self.scale_pva = self._tuple_vector_random(scale)
        self.scale_velocity_pva = self._tuple_vector_random(velocity)
        self.scale_acceleration_pva = self._tuple_vector_random(acceleration)
        return {"ok": True}

    def set_node_fade_in_out_by_automation_id(
        self,
        automation_node_id: str,
        fade_in_type: str,
        fade_in_frame: float,
        fade_out_type: str,
        fade_out_frame: float,
    ) -> dict[str, bool]:
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
        self.undo_stack.append(
            (
                "fade",
                (
                    self.fade_in_type,
                    self.fade_in_frame,
                    self.fade_out_type,
                    self.fade_out_frame,
                ),
            )
        )
        self.redo_stack.clear()
        self.fade_in_type = fade_in_type
        self.fade_in_frame = fade_in_frame
        self.fade_out_type = fade_out_type
        self.fade_out_frame = fade_out_frame
        return {"ok": True}

    def set_node_color_all_fixed_rgba_by_automation_id(
        self,
        automation_node_id: str,
        r: int,
        g: int,
        b: int,
        a: int,
    ) -> dict[str, bool]:
        self.calls.append(
            (
                "set_node_color_all_fixed_rgba_by_automation_id",
                (automation_node_id, r, g, b, a),
            )
        )
        self.undo_stack.append(("color_all", self.color_all.copy()))
        self.redo_stack.clear()
        self.color_all = {"r": r, "g": g, "b": b, "a": a}
        return {"ok": True}

    def set_node_sprite_corner_colors_fixed_rgba_by_automation_id(
        self,
        automation_node_id: str,
        lower_left: dict[str, int],
        lower_right: dict[str, int],
        upper_left: dict[str, int],
        upper_right: dict[str, int],
    ) -> dict[str, bool]:
        self.calls.append(
            (
                "set_node_sprite_corner_colors_fixed_rgba_by_automation_id",
                (automation_node_id, lower_left, lower_right, upper_left, upper_right),
            )
        )
        self.undo_stack.append(("corner_colors", self._copy_corner_colors()))
        self.redo_stack.clear()
        self.corner_colors = {
            "lowerLeft": lower_left.copy(),
            "lowerRight": lower_right.copy(),
            "upperLeft": upper_left.copy(),
            "upperRight": upper_right.copy(),
        }
        return {"ok": True}

    def set_node_alpha_blend_by_automation_id(
        self,
        automation_node_id: str,
        alpha_blend: str,
    ) -> dict[str, bool]:
        self.calls.append(
            ("set_node_alpha_blend_by_automation_id", (automation_node_id, alpha_blend))
        )
        self.undo_stack.append(("alpha_blend", self.alpha_blend))
        self.redo_stack.clear()
        self.alpha_blend = alpha_blend
        return {"ok": True}

    def set_node_z_write_by_automation_id(
        self,
        automation_node_id: str,
        z_write: bool,
    ) -> dict[str, bool]:
        self.calls.append(
            ("set_node_z_write_by_automation_id", (automation_node_id, z_write))
        )
        self.undo_stack.append(("z_write", self.z_write))
        self.redo_stack.clear()
        self.z_write = z_write
        return {"ok": True}

    def set_node_z_test_by_automation_id(
        self,
        automation_node_id: str,
        z_test: bool,
    ) -> dict[str, bool]:
        self.calls.append(
            ("set_node_z_test_by_automation_id", (automation_node_id, z_test))
        )
        self.undo_stack.append(("z_test", self.z_test))
        self.redo_stack.clear()
        self.z_test = z_test
        return {"ok": True}

    def set_node_renderer_type_by_automation_id(
        self,
        automation_node_id: str,
        renderer_type: str,
    ) -> dict[str, bool]:
        self.calls.append(
            (
                "set_node_renderer_type_by_automation_id",
                (automation_node_id, renderer_type),
            )
        )
        self.undo_stack.append(("renderer_type", self.renderer_type))
        self.redo_stack.clear()
        self.renderer_type = renderer_type
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
        self.color_texture_path = path
        return {"ok": True, "result": {"path": path}}

    def set_node_normal_texture_from_workspace_by_automation_id(
        self,
        automation_node_id: str,
        path: str,
    ) -> dict[str, Any]:
        self.calls.append(
            (
                "set_node_normal_texture_from_workspace_by_automation_id",
                (automation_node_id, path),
            )
        )
        self.normal_texture_path = path
        return {"ok": True, "result": {"path": path}}

    def clear_node_color_texture_by_automation_id(
        self,
        automation_node_id: str,
    ) -> dict[str, bool]:
        self.calls.append(("clear_node_color_texture_by_automation_id", (automation_node_id,)))
        self.color_texture_path = None
        return {"ok": True}

    def clear_node_normal_texture_by_automation_id(
        self,
        automation_node_id: str,
    ) -> dict[str, bool]:
        self.calls.append(("clear_node_normal_texture_by_automation_id", (automation_node_id,)))
        self.normal_texture_path = None
        return {"ok": True}

    def set_node_material_from_workspace_by_automation_id(
        self,
        automation_node_id: str,
        path: str,
    ) -> dict[str, Any]:
        self.calls.append(
            (
                "set_node_material_from_workspace_by_automation_id",
                (automation_node_id, path),
            )
        )
        self.material_path = path
        return {"ok": True, "result": {"path": path}}

    def clear_node_material_by_automation_id(
        self,
        automation_node_id: str,
    ) -> dict[str, bool]:
        self.calls.append(("clear_node_material_by_automation_id", (automation_node_id,)))
        self.material_path = None
        return {"ok": True}

    def set_node_model_from_workspace_by_automation_id(
        self,
        automation_node_id: str,
        path: str,
    ) -> dict[str, Any]:
        self.calls.append(
            (
                "set_node_model_from_workspace_by_automation_id",
                (automation_node_id, path),
            )
        )
        self.model_path = path
        self.renderer_type = "Model"
        return {"ok": True, "result": {"path": path}}

    def _copy_corner_colors(self) -> dict[str, dict[str, int]]:
        return {key: value.copy() for key, value in self.corner_colors.items()}

    def _tuple_vector_random(
        self,
        payload: dict[str, dict[str, float]],
    ) -> tuple[
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
    ]:
        return (
            (payload["x"]["center"], payload["x"]["min"], payload["x"]["max"]),
            (payload["y"]["center"], payload["y"]["min"], payload["y"]["max"]),
            (payload["z"]["center"], payload["z"]["min"], payload["z"]["max"]),
        )

    def duplicate_node_by_automation_id(
        self,
        automation_node_id: str,
        name: str | None = None,
    ) -> dict[str, str]:
        self.calls.append(("duplicate_node_by_automation_id", (automation_node_id, name)))
        self.duplicate_name = name or "Duplicate"
        return {"automationNodeId": self.duplicate_automation_node_id}

    def insert_parent_node_by_automation_id(
        self,
        automation_node_id: str,
        name: str | None = None,
    ) -> dict[str, str]:
        self.calls.append(
            ("insert_parent_node_by_automation_id", (automation_node_id, name))
        )
        self.wrapper_name = name or "Wrapper"
        self.wrapper_present = True
        return {"automationNodeId": self.wrapper_automation_node_id}

    def remove_node_by_automation_id(self, automation_node_id: str) -> dict[str, bool]:
        self.calls.append(("remove_node_by_automation_id", (automation_node_id,)))
        if automation_node_id == self.smoke_root_automation_node_id:
            self.smoke_root_present = False
            self.node_name = ""
            self.duplicate_name = ""
            self.wrapper_name = ""
            self.wrapper_present = False
        elif automation_node_id == self.legacy_renamed_automation_node_id:
            self.legacy_renamed_present = False
        elif automation_node_id == self.wrapper_automation_node_id:
            self.undo_stack.append(("wrapper_present", self.wrapper_present))
            self.redo_stack.clear()
            self.wrapper_present = False
        return {"ok": True}

    def undo(self) -> dict[str, bool]:
        self.calls.append(("undo", ()))
        if self.undo_stack:
            key, previous_value = self.undo_stack.pop()
            if key == "is_rendered":
                self.redo_stack.append((key, self.is_rendered))
                self.is_rendered = previous_value
            elif key == "max_generation":
                self.redo_stack.append((key, self.max_generation))
                self.max_generation = previous_value
            elif key == "life":
                self.redo_stack.append((key, self.life))
                self.life = previous_value
            elif key == "location":
                self.redo_stack.append((key, self.location))
                self.location = previous_value
            elif key == "rotation":
                self.redo_stack.append((key, self.rotation))
                self.rotation = previous_value
            elif key == "scale":
                self.redo_stack.append((key, self.scale))
                self.scale = previous_value
            elif key == "generation_time":
                self.redo_stack.append((key, self.generation_time))
                self.generation_time = previous_value
            elif key == "location_type":
                self.redo_stack.append((key, self.location_type))
                self.location_type = previous_value
            elif key == "location_pva":
                self.redo_stack.append(
                    (
                        key,
                        (
                            self.location_pva,
                            self.velocity_pva,
                            self.acceleration_pva,
                        ),
                    )
                )
                (
                    self.location_pva,
                    self.velocity_pva,
                    self.acceleration_pva,
                ) = previous_value
            elif key == "scale_type":
                self.redo_stack.append((key, self.scale_type))
                self.scale_type = previous_value
            elif key == "scale_pva":
                self.redo_stack.append(
                    (
                        key,
                        (
                            self.scale_pva,
                            self.scale_velocity_pva,
                            self.scale_acceleration_pva,
                        ),
                    )
                )
                (
                    self.scale_pva,
                    self.scale_velocity_pva,
                    self.scale_acceleration_pva,
                ) = previous_value
            elif key == "color_all":
                self.redo_stack.append((key, self.color_all.copy()))
                self.color_all = previous_value
            elif key == "corner_colors":
                self.redo_stack.append((key, self._copy_corner_colors()))
                self.corner_colors = previous_value
            elif key == "alpha_blend":
                self.redo_stack.append((key, self.alpha_blend))
                self.alpha_blend = previous_value
            elif key == "z_write":
                self.redo_stack.append((key, self.z_write))
                self.z_write = previous_value
            elif key == "z_test":
                self.redo_stack.append((key, self.z_test))
                self.z_test = previous_value
            elif key == "renderer_type":
                self.redo_stack.append((key, self.renderer_type))
                self.renderer_type = previous_value
            elif key == "fade":
                self.redo_stack.append(
                    (
                        key,
                        (
                            self.fade_in_type,
                            self.fade_in_frame,
                            self.fade_out_type,
                            self.fade_out_frame,
                        ),
                    )
                )
                (
                    self.fade_in_type,
                    self.fade_in_frame,
                    self.fade_out_type,
                    self.fade_out_frame,
                ) = previous_value
            elif key == "wrapper_present":
                self.redo_stack.append((key, self.wrapper_present))
                self.wrapper_present = previous_value
        return {"ok": True}

    def redo(self) -> dict[str, bool]:
        self.calls.append(("redo", ()))
        if self.redo_stack:
            key, next_value = self.redo_stack.pop()
            if key == "is_rendered":
                self.undo_stack.append((key, self.is_rendered))
                self.is_rendered = next_value
            elif key == "max_generation":
                self.undo_stack.append((key, self.max_generation))
                self.max_generation = next_value
            elif key == "life":
                self.undo_stack.append((key, self.life))
                self.life = next_value
            elif key == "location":
                self.undo_stack.append((key, self.location))
                self.location = next_value
            elif key == "rotation":
                self.undo_stack.append((key, self.rotation))
                self.rotation = next_value
            elif key == "scale":
                self.undo_stack.append((key, self.scale))
                self.scale = next_value
            elif key == "generation_time":
                self.undo_stack.append((key, self.generation_time))
                self.generation_time = next_value
            elif key == "location_type":
                self.undo_stack.append((key, self.location_type))
                self.location_type = next_value
            elif key == "location_pva":
                self.undo_stack.append(
                    (
                        key,
                        (
                            self.location_pva,
                            self.velocity_pva,
                            self.acceleration_pva,
                        ),
                    )
                )
                (
                    self.location_pva,
                    self.velocity_pva,
                    self.acceleration_pva,
                ) = next_value
            elif key == "scale_type":
                self.undo_stack.append((key, self.scale_type))
                self.scale_type = next_value
            elif key == "scale_pva":
                self.undo_stack.append(
                    (
                        key,
                        (
                            self.scale_pva,
                            self.scale_velocity_pva,
                            self.scale_acceleration_pva,
                        ),
                    )
                )
                (
                    self.scale_pva,
                    self.scale_velocity_pva,
                    self.scale_acceleration_pva,
                ) = next_value
            elif key == "color_all":
                self.undo_stack.append((key, self.color_all.copy()))
                self.color_all = next_value
            elif key == "corner_colors":
                self.undo_stack.append((key, self._copy_corner_colors()))
                self.corner_colors = next_value
            elif key == "alpha_blend":
                self.undo_stack.append((key, self.alpha_blend))
                self.alpha_blend = next_value
            elif key == "z_write":
                self.undo_stack.append((key, self.z_write))
                self.z_write = next_value
            elif key == "z_test":
                self.undo_stack.append((key, self.z_test))
                self.z_test = next_value
            elif key == "renderer_type":
                self.undo_stack.append((key, self.renderer_type))
                self.renderer_type = next_value
            elif key == "fade":
                self.undo_stack.append(
                    (
                        key,
                        (
                            self.fade_in_type,
                            self.fade_in_frame,
                            self.fade_out_type,
                            self.fade_out_frame,
                        ),
                    )
                )
                (
                    self.fade_in_type,
                    self.fade_in_frame,
                    self.fade_out_type,
                    self.fade_out_frame,
                ) = next_value
            elif key == "wrapper_present":
                self.undo_stack.append((key, self.wrapper_present))
                self.wrapper_present = next_value
        return {"ok": True}

    def play_viewer(self) -> dict[str, bool]:
        self.calls.append(("play_viewer", ()))
        return {"ok": True}

    def step_viewer(self) -> dict[str, bool]:
        self.calls.append(("step_viewer", ()))
        return {"ok": True}

    def stop_viewer(self) -> dict[str, bool]:
        self.calls.append(("stop_viewer", ()))
        return {"ok": True}

    def back_step_viewer(self) -> dict[str, bool]:
        self.calls.append(("back_step_viewer", ()))
        return {"ok": True}


def test_smoke_bridge_logic_runs_expected_sequence() -> None:
    client = FakeBridgeClient()
    names = make_smoke_names("abcd1234")
    stdout = StringIO()
    stderr = StringIO()

    run_smoke_test(
        client,
        run_id=names.run_id,
        smoke_texture_path="inputs/textures/smoke_color.png",
        smoke_material_path="inputs/materials/smoke.efkmat",
        smoke_model_path="inputs/models/smoke.efkmodel",
        stdout=stdout,
        stderr=stderr,
    )

    white = {"r": 255, "g": 255, "b": 255, "a": 255}
    lower_left = {"r": 255, "g": 0, "b": 0, "a": 255}
    lower_right = {"r": 0, "g": 255, "b": 0, "a": 255}
    upper_left = {"r": 0, "g": 0, "b": 255, "a": 255}
    upper_right = {"r": 255, "g": 255, "b": 0, "a": 255}
    location_pva = vector_random_payload(
        ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    )
    velocity_pva = vector_random_payload(
        ((0.0, 0.0, 0.0), (12.0, 12.0, 12.0), (0.0, 0.0, 0.0))
    )
    acceleration_pva = vector_random_payload(
        ((0.0, 0.0, 0.0), (-0.5, -0.5, -0.5), (0.0, 0.0, 0.0))
    )
    scale_pva = vector_random_payload(
        ((1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0))
    )
    scale_velocity_pva = vector_random_payload(
        ((-0.02, -0.02, -0.02), (-0.02, -0.02, -0.02), (-0.02, -0.02, -0.02))
    )
    scale_acceleration_pva = vector_random_payload(
        ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    )

    assert client.calls == [
        ("ping", ()),
        ("get_status", ()),
        ("get_bridge_capabilities", ()),
        ("get_workspace_status", ()),
        ("get_node_tree", ()),
        ("get_node_tree", ()),
        ("add_node_to_parent_by_automation_id", ("auto-root", names.root)),
        ("get_node_tree", ()),
        (
            "add_node_to_parent_by_automation_id",
            ("auto-smoke-root", names.node),
        ),
        ("get_node_tree", ()),
        ("rename_node_by_automation_id", ("auto-child", names.renamed)),
        ("get_node_tree", ()),
        ("get_node_basic_info_by_automation_id", ("auto-child",)),
        ("get_node_parameter_groups_by_automation_id", ("auto-child",)),
        ("get_node_tree", ()),
        ("get_node_base_parameters_by_automation_id", ("auto-child",)),
        ("get_node_generation_parameters_by_automation_id", ("auto-child",)),
        ("get_node_transform_parameters_by_automation_id", ("auto-child",)),
        ("get_node_drawing_parameters_by_automation_id", ("auto-child",)),
        ("get_node_renderer_parameters_by_automation_id", ("auto-child",)),
        ("get_node_tree", ()),
        ("set_node_is_rendered_by_automation_id", ("auto-child", False)),
        ("get_node_base_parameters_by_automation_id", ("auto-child",)),
        ("undo", ()),
        ("get_node_base_parameters_by_automation_id", ("auto-child",)),
        ("redo", ()),
        ("get_node_base_parameters_by_automation_id", ("auto-child",)),
        ("set_node_is_rendered_by_automation_id", ("auto-child", True)),
        ("get_node_base_parameters_by_automation_id", ("auto-child",)),
        ("set_node_max_generation_by_automation_id", ("auto-child", 2)),
        ("set_node_life_by_automation_id", ("auto-child", 11, 3, 21)),
        (
            "set_node_fixed_location_by_automation_id",
            ("auto-child", 1.0, 2.0, 3.0),
        ),
        (
            "set_node_fixed_rotation_by_automation_id",
            ("auto-child", 10.0, 20.0, 30.0),
        ),
        (
            "set_node_fixed_scale_by_automation_id",
            ("auto-child", 1.5, 1.25, 1.75),
        ),
        ("get_node_generation_parameters_by_automation_id", ("auto-child",)),
        ("get_node_transform_parameters_by_automation_id", ("auto-child",)),
        ("undo", ()),
        ("get_node_transform_parameters_by_automation_id", ("auto-child",)),
        ("redo", ()),
        ("get_node_transform_parameters_by_automation_id", ("auto-child",)),
        ("set_node_max_generation_by_automation_id", ("auto-child", 1)),
        ("set_node_life_by_automation_id", ("auto-child", 10, 2, 20)),
        (
            "set_node_fixed_location_by_automation_id",
            ("auto-child", 0.0, 0.0, 0.0),
        ),
        (
            "set_node_fixed_rotation_by_automation_id",
            ("auto-child", 0.0, 0.0, 0.0),
        ),
        (
            "set_node_fixed_scale_by_automation_id",
            ("auto-child", 1.0, 1.0, 1.0),
        ),
        ("get_node_generation_parameters_by_automation_id", ("auto-child",)),
        ("get_node_transform_parameters_by_automation_id", ("auto-child",)),
        ("get_node_generation_parameters_by_automation_id", ("auto-child",)),
        ("get_node_transform_parameters_by_automation_id", ("auto-child",)),
        ("get_node_renderer_parameters_by_automation_id", ("auto-child",)),
        (
            "set_node_generation_time_by_automation_id",
            ("auto-child", 1.25, 1.25, 1.25),
        ),
        ("set_node_location_type_by_automation_id", ("auto-child", "PVA")),
        (
            "set_node_location_pva_by_automation_id",
            ("auto-child", location_pva, velocity_pva, acceleration_pva),
        ),
        ("set_node_scale_type_by_automation_id", ("auto-child", "PVA")),
        (
            "set_node_scale_pva_by_automation_id",
            ("auto-child", scale_pva, scale_velocity_pva, scale_acceleration_pva),
        ),
        (
            "set_node_fade_in_out_by_automation_id",
            ("auto-child", "Use", 2.0, "WithinLifetime", 2.0),
        ),
        ("get_node_generation_parameters_by_automation_id", ("auto-child",)),
        ("get_node_transform_parameters_by_automation_id", ("auto-child",)),
        ("get_node_renderer_parameters_by_automation_id", ("auto-child",)),
        ("undo", ()),
        ("get_node_generation_parameters_by_automation_id", ("auto-child",)),
        ("get_node_transform_parameters_by_automation_id", ("auto-child",)),
        ("get_node_renderer_parameters_by_automation_id", ("auto-child",)),
        ("redo", ()),
        ("get_node_generation_parameters_by_automation_id", ("auto-child",)),
        ("get_node_transform_parameters_by_automation_id", ("auto-child",)),
        ("get_node_renderer_parameters_by_automation_id", ("auto-child",)),
        ("set_node_generation_time_by_automation_id", ("auto-child", 1.0, 1.0, 1.0)),
        ("set_node_location_type_by_automation_id", ("auto-child", "Fixed")),
        (
            "set_node_location_pva_by_automation_id",
            (
                "auto-child",
                vector_random_payload(
                    ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
                ),
                vector_random_payload(
                    ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
                ),
                vector_random_payload(
                    ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
                ),
            ),
        ),
        ("set_node_scale_type_by_automation_id", ("auto-child", "Fixed")),
        (
            "set_node_scale_pva_by_automation_id",
            (
                "auto-child",
                vector_random_payload(
                    ((1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0))
                ),
                vector_random_payload(
                    ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
                ),
                vector_random_payload(
                    ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
                ),
            ),
        ),
        ("set_node_fade_in_out_by_automation_id", ("auto-child", "None", 1.0, "None", 1.0)),
        ("get_node_generation_parameters_by_automation_id", ("auto-child",)),
        ("get_node_transform_parameters_by_automation_id", ("auto-child",)),
        ("get_node_renderer_parameters_by_automation_id", ("auto-child",)),
        (
            "set_node_color_all_fixed_rgba_by_automation_id",
            ("auto-child", 32, 96, 192, 224),
        ),
        (
            "set_node_sprite_corner_colors_fixed_rgba_by_automation_id",
            ("auto-child", lower_left, lower_right, upper_left, upper_right),
        ),
        ("set_node_alpha_blend_by_automation_id", ("auto-child", "Add")),
        ("set_node_z_write_by_automation_id", ("auto-child", False)),
        ("set_node_z_test_by_automation_id", ("auto-child", False)),
        ("set_node_renderer_type_by_automation_id", ("auto-child", "Ribbon")),
        ("get_node_drawing_parameters_by_automation_id", ("auto-child",)),
        ("get_node_renderer_parameters_by_automation_id", ("auto-child",)),
        ("undo", ()),
        ("get_node_drawing_parameters_by_automation_id", ("auto-child",)),
        ("get_node_renderer_parameters_by_automation_id", ("auto-child",)),
        ("redo", ()),
        ("get_node_drawing_parameters_by_automation_id", ("auto-child",)),
        ("get_node_renderer_parameters_by_automation_id", ("auto-child",)),
        ("set_node_renderer_type_by_automation_id", ("auto-child", "Sprite")),
        (
            "set_node_color_all_fixed_rgba_by_automation_id",
            ("auto-child", 255, 255, 255, 255),
        ),
        (
            "set_node_sprite_corner_colors_fixed_rgba_by_automation_id",
            ("auto-child", white, white, white, white),
        ),
        ("set_node_alpha_blend_by_automation_id", ("auto-child", "Blend")),
        ("set_node_z_write_by_automation_id", ("auto-child", True)),
        ("set_node_z_test_by_automation_id", ("auto-child", True)),
        ("get_node_drawing_parameters_by_automation_id", ("auto-child",)),
        ("get_node_renderer_parameters_by_automation_id", ("auto-child",)),
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("auto-child", "inputs/textures/smoke_color.png"),
        ),
        ("get_node_renderer_parameters_by_automation_id", ("auto-child",)),
        (
            "set_node_normal_texture_from_workspace_by_automation_id",
            ("auto-child", "inputs/textures/smoke_color.png"),
        ),
        ("get_node_renderer_parameters_by_automation_id", ("auto-child",)),
        (
            "set_node_material_from_workspace_by_automation_id",
            ("auto-child", "inputs/materials/smoke.efkmat"),
        ),
        ("get_node_renderer_parameters_by_automation_id", ("auto-child",)),
        ("duplicate_node_by_automation_id", ("auto-child", names.duplicate)),
        ("get_node_tree", ()),
        (
            "insert_parent_node_by_automation_id",
            ("auto-duplicate", names.wrapper),
        ),
        ("get_node_tree", ()),
        ("remove_node_by_automation_id", ("auto-wrapper",)),
        ("get_node_tree", ()),
        ("undo", ()),
        ("get_node_tree", ()),
        ("redo", ()),
        ("get_node_tree", ()),
        ("play_viewer", ()),
        ("step_viewer", ()),
        ("stop_viewer", ()),
        ("back_step_viewer", ()),
        ("save_project_to_workspace", ("outputs/smoke_resource_abcd1234.efkefc",)),
        ("open_project_from_workspace", ("outputs/smoke_resource_abcd1234.efkefc",)),
        ("get_node_tree", ()),
        ("get_node_renderer_parameters_by_automation_id", ("auto-child",)),
        (
            "export_runtime_effect_to_workspace",
            ("outputs/smoke_resource_abcd1234.efk",),
        ),
        ("clear_node_color_texture_by_automation_id", ("auto-child",)),
        ("get_node_renderer_parameters_by_automation_id", ("auto-child",)),
        ("clear_node_normal_texture_by_automation_id", ("auto-child",)),
        ("get_node_renderer_parameters_by_automation_id", ("auto-child",)),
        ("clear_node_material_by_automation_id", ("auto-child",)),
        ("get_node_renderer_parameters_by_automation_id", ("auto-child",)),
        (
            "set_node_model_from_workspace_by_automation_id",
            ("auto-child", "inputs/models/smoke.efkmodel"),
        ),
        ("get_node_drawing_parameters_by_automation_id", ("auto-child",)),
        ("save_project_to_workspace", ("outputs/smoke_model_abcd1234.efkefc",)),
        ("open_project_from_workspace", ("outputs/smoke_model_abcd1234.efkefc",)),
        ("get_node_tree", ()),
        ("get_node_drawing_parameters_by_automation_id", ("auto-child",)),
        (
            "export_runtime_effect_to_workspace",
            ("outputs/smoke_model_abcd1234.efk",),
        ),
        ("remove_node_by_automation_id", ("auto-smoke-root",)),
        ("get_node_tree", ()),
    ]
    assert find_run_smoke_node_names(client.get_node_tree(), names) == []
    assert client.is_rendered is True
    assert client.max_generation == 1
    assert client.life == (10, 2, 20)
    assert client.location == (0.0, 0.0, 0.0)
    assert client.rotation == (0.0, 0.0, 0.0)
    assert client.scale == (1.0, 1.0, 1.0)
    assert client.generation_time == (1.0, 1.0, 1.0)
    assert client.location_type == "Fixed"
    assert client.location_pva == (
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
    )
    assert client.velocity_pva == (
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
    )
    assert client.acceleration_pva == (
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
    )
    assert client.scale_type == "Fixed"
    assert client.scale_pva == (
        (1.0, 1.0, 1.0),
        (1.0, 1.0, 1.0),
        (1.0, 1.0, 1.0),
    )
    assert client.scale_velocity_pva == (
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
    )
    assert client.scale_acceleration_pva == (
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
    )
    assert client.renderer_type == "Model"
    assert client.color_all == white
    assert client.corner_colors == {
        "lowerLeft": white,
        "lowerRight": white,
        "upperLeft": white,
        "upperRight": white,
    }
    assert client.alpha_blend == "Blend"
    assert client.z_write is True
    assert client.z_test is True
    assert client.fade_in_type == "None"
    assert client.fade_in_frame == 1.0
    assert client.fade_out_type == "None"
    assert client.fade_out_frame == 1.0
    assert client.color_texture_path is None
    assert client.normal_texture_path is None
    assert client.material_path is None
    assert client.model_path == "inputs/models/smoke.efkmodel"
    assert "Smoke test passed" in stdout.getvalue()
    assert stderr.getvalue() == ""


def test_smoke_bridge_uses_current_subtree_when_legacy_name_exists() -> None:
    client = FakeBridgeClient(include_legacy_renamed=True)
    names = make_smoke_names("deadbeef")
    stdout = StringIO()
    stderr = StringIO()

    run_smoke_test(
        client,
        run_id=names.run_id,
        smoke_texture_path="inputs/textures/smoke_color.png",
        smoke_material_path="inputs/materials/smoke.efkmat",
        smoke_model_path="inputs/models/smoke.efkmodel",
        stdout=stdout,
        stderr=stderr,
    )

    assert (
        "duplicate_node_by_automation_id",
        ("auto-child", names.duplicate),
    ) in client.calls
    assert (
        "duplicate_node_by_automation_id",
        ("auto-legacy-renamed", names.duplicate),
    ) not in client.calls
    assert ("remove_node_by_automation_id", ("auto-legacy-renamed",)) in client.calls
    assert find_run_smoke_node_names(client.get_node_tree(), names) == []
    assert "WARNING: removing legacy smoke node SmokeTestRenamed" in stderr.getvalue()


def test_restore_drawing_renderer_values_restores_renderer_type_before_sprite_colors() -> None:
    client = FakeBridgeClient()
    values = DrawingRendererWriteValues(
        renderer_type="Sprite",
        color_all=RgbaValues(r=255, g=255, b=255, a=255),
        corner_colors=SpriteCornerColors(
            lower_left=RgbaValues(r=1, g=2, b=3, a=4),
            lower_right=RgbaValues(r=5, g=6, b=7, a=8),
            upper_left=RgbaValues(r=9, g=10, b=11, a=12),
            upper_right=RgbaValues(r=13, g=14, b=15, a=16),
        ),
        alpha_blend="Blend",
        z_write=True,
        z_test=True,
    )

    restore_drawing_renderer_write_values(client, "auto-child", values)

    call_names = [name for name, _ in client.calls]
    assert call_names == [
        "set_node_renderer_type_by_automation_id",
        "set_node_color_all_fixed_rgba_by_automation_id",
        "set_node_sprite_corner_colors_fixed_rgba_by_automation_id",
        "set_node_alpha_blend_by_automation_id",
        "set_node_z_write_by_automation_id",
        "set_node_z_test_by_automation_id",
    ]


def test_restore_motion_timing_fade_values_restores_all_fields() -> None:
    client = FakeBridgeClient()
    values = MotionTimingFadeWriteValues(
        generation_time=RandomFloatValues(center=1.0, min=1.0, max=1.0),
        location_type="Fixed",
        location_pva=VectorRandomValues(
            x=RandomFloatValues(center=0.0, min=0.0, max=0.0),
            y=RandomFloatValues(center=0.0, min=0.0, max=0.0),
            z=RandomFloatValues(center=0.0, min=0.0, max=0.0),
        ),
        velocity_pva=VectorRandomValues(
            x=RandomFloatValues(center=0.0, min=0.0, max=0.0),
            y=RandomFloatValues(center=1.0, min=1.0, max=1.0),
            z=RandomFloatValues(center=0.0, min=0.0, max=0.0),
        ),
        acceleration_pva=VectorRandomValues(
            x=RandomFloatValues(center=0.0, min=0.0, max=0.0),
            y=RandomFloatValues(center=-1.0, min=-1.0, max=-1.0),
            z=RandomFloatValues(center=0.0, min=0.0, max=0.0),
        ),
        scale_type="PVA",
        scale_pva=VectorRandomValues(
            x=RandomFloatValues(center=1.0, min=1.0, max=1.0),
            y=RandomFloatValues(center=1.0, min=1.0, max=1.0),
            z=RandomFloatValues(center=1.0, min=1.0, max=1.0),
        ),
        scale_velocity_pva=VectorRandomValues(
            x=RandomFloatValues(center=-0.1, min=-0.1, max=-0.1),
            y=RandomFloatValues(center=-0.1, min=-0.1, max=-0.1),
            z=RandomFloatValues(center=-0.1, min=-0.1, max=-0.1),
        ),
        scale_acceleration_pva=VectorRandomValues(
            x=RandomFloatValues(center=0.0, min=0.0, max=0.0),
            y=RandomFloatValues(center=0.0, min=0.0, max=0.0),
            z=RandomFloatValues(center=0.0, min=0.0, max=0.0),
        ),
        fade_in_type="Use",
        fade_in_frame=2.0,
        fade_out_type="WithinLifetime",
        fade_out_frame=5.0,
    )

    restore_motion_timing_fade_write_values(client, "auto-child", values)

    call_names = [name for name, _ in client.calls]
    assert call_names == [
        "set_node_generation_time_by_automation_id",
        "set_node_location_type_by_automation_id",
        "set_node_location_pva_by_automation_id",
        "set_node_scale_type_by_automation_id",
        "set_node_scale_pva_by_automation_id",
        "set_node_fade_in_out_by_automation_id",
    ]


def test_smoke_bridge_fails_early_when_required_command_is_missing() -> None:
    commands = set(REQUIRED_BRIDGE_COMMANDS)
    commands.remove("set_node_max_generation_by_automation_id")
    client = FakeBridgeClient(capability_commands=commands)

    try:
        run_smoke_test(client, run_id="missing1", stdout=StringIO(), stderr=StringIO())
    except SmokeBridgeError as exc:
        message = str(exc)
        assert "Bridge is missing required commands" in message
        assert "set_node_max_generation_by_automation_id" in message
        assert "Rebuild and restart Effekseer.exe" in message
    else:
        raise AssertionError("expected SmokeBridgeError")

    assert client.calls == [
        ("ping", ()),
        ("get_status", ()),
        ("get_bridge_capabilities", ()),
        ("get_node_tree", ()),
    ]


def test_smoke_bridge_capabilities_reports_bridge_error() -> None:
    client = FakeBridgeClient(
        capabilities_response={
            "ok": False,
            "error": "unknown command: get_bridge_capabilities",
        }
    )

    try:
        run_smoke_test(client, run_id="oldbuild", stdout=StringIO(), stderr=StringIO())
    except SmokeBridgeError as exc:
        message = str(exc)
        assert "Bridge capabilities check failed" in message
        assert "unknown command: get_bridge_capabilities" in message
        assert "Rebuild and restart Effekseer.exe" in message
    else:
        raise AssertionError("expected SmokeBridgeError")


def test_smoke_bridge_capabilities_rejects_invalid_commands_shape() -> None:
    try:
        assert_bridge_capabilities(
            {"ok": True, "result": {"commands": ["ping", 123]}},
            REQUIRED_BRIDGE_COMMANDS,
        )
    except SmokeBridgeError as exc:
        assert "result.commands as list[str]" in str(exc)
    else:
        raise AssertionError("expected SmokeBridgeError")


def test_smoke_helpers_find_root_and_node_by_name() -> None:
    tree = {
        "root": {
            "editorNodeId": 1,
            "automationNodeId": "auto-root",
            "name": "Root",
            "children": [
                {
                    "editorNodeId": 2,
                    "automationNodeId": "auto-child",
                    "name": "Child",
                }
            ],
        }
    }

    assert find_root_node(tree)["name"] == "Root"
    assert find_node_id_by_name(tree, "Child") == 2
    assert find_automation_node_id_by_name(tree, "Child") == "auto-child"


def test_smoke_assert_basic_info_unwraps_bridge_result() -> None:
    assert_basic_info(
        {
            "ok": True,
            "result": {
                "automationNodeId": "auto-child",
                "name": "Child",
                "childCount": 0,
                "isRendered": True,
                "nodeType": "Normal",
                "className": "Effekseer.InternalScript.EffectNode",
            },
        },
        automation_node_id="auto-child",
        name="Child",
    )


def test_smoke_assert_parameter_groups_accepts_string_groups() -> None:
    assert_parameter_groups(
        {
            "ok": True,
            "result": {
                "groups": [
                    "node_base",
                    "common",
                    "generation",
                    "location",
                    "rotation",
                    "scale",
                ]
            },
        },
        EXPECTED_PARAMETER_GROUPS,
    )


def test_smoke_assert_parameter_values_unwrap_bridge_result() -> None:
    assert_required_parameter_keys(
        {
            "ok": True,
            "result": {
                "automationNodeId": "auto-child",
                "name": "Child",
                "location": {},
                "rotation": {},
                "scale": {},
            },
        },
        TRANSFORM_PARAMETERS_REQUIRED_KEYS,
        label="transform parameters",
        automation_node_id="auto-child",
        name="Child",
    )


def test_smoke_assert_drawing_parameters_unwrap_bridge_result() -> None:
    assert_required_parameter_keys(
        {
            "ok": True,
            "result": {
                "automationNodeId": "auto-child",
                "name": "Child",
                "rendererType": "Sprite",
                "textureUVType": "Default",
                "colorAll": {},
                "sprite": {},
            },
        },
        DRAWING_PARAMETERS_REQUIRED_KEYS,
        label="drawing parameters",
        automation_node_id="auto-child",
        name="Child",
    )


def test_smoke_assert_renderer_parameters_unwrap_bridge_result() -> None:
    assert_required_parameter_keys(
        {
            "ok": True,
            "result": {
                "automationNodeId": "auto-child",
                "name": "Child",
                "material": {},
                "textures": [],
                "blend": {},
                "uv": {},
            },
        },
        RENDERER_PARAMETERS_REQUIRED_KEYS,
        label="renderer parameters",
        automation_node_id="auto-child",
        name="Child",
    )


def test_smoke_texture_reference_accepts_textures_list_entry() -> None:
    assert_texture_reference_has_value(
        {
            "ok": True,
            "result": {
                "textures": [
                    {
                        "key": "colorTexture",
                        "reference": {
                            "hasValue": True,
                            "path": "inputs/textures/smoke_color.png",
                        },
                    }
                ],
            },
        },
        "colorTexture",
        label="color texture readback",
    )


def test_smoke_texture_reference_accepts_enum_slot_alias() -> None:
    assert_texture_reference_has_value(
        {
            "ok": True,
            "result": {
                "textures": [
                    {
                        "slot": {"value": "Normal Texture", "valueId": 1},
                        "reference": {
                            "hasValue": True,
                            "path": "inputs/textures/smoke_color.png",
                        },
                    }
                ],
            },
        },
        "normalTexture",
        label="normal texture readback",
    )


def test_smoke_texture_reference_rejects_absolute_path_in_textures_list() -> None:
    try:
        assert_texture_reference_has_value(
            {
                "ok": True,
                "result": {
                    "textures": [
                        {
                            "key": "colorTexture",
                            "reference": {
                                "hasValue": True,
                                "path": "C:/outside/smoke_color.png",
                            },
                        }
                    ],
                },
            },
            "colorTexture",
            label="color texture readback",
        )
    except SmokeBridgeError as exc:
        assert "absolute path" in str(exc)
    else:
        raise AssertionError("expected SmokeBridgeError")


def test_smoke_drawing_renderer_values_accept_enum_payloads() -> None:
    values = get_drawing_renderer_write_values(
        {
            "ok": True,
            "result": {
                "rendererType": {"value": "Sprite", "valueId": 0},
                "colorAll": {
                    "type": {"value": "Fixed", "valueId": 0},
                    "fixed": {"r": 255, "g": 255, "b": 255, "a": 255},
                    "random": {},
                    "easing": {},
                    "fcurve": {},
                    "gradient": {},
                },
                "sprite": {
                    "fixedColors": {
                        "lowerLeft": {"r": 255, "g": 0, "b": 0, "a": 255},
                        "lowerRight": {"r": 0, "g": 255, "b": 0, "a": 255},
                        "upperLeft": {"r": 0, "g": 0, "b": 255, "a": 255},
                        "upperRight": {"r": 255, "g": 255, "b": 0, "a": 255},
                    }
                },
            },
        },
        {
            "ok": True,
            "result": {
                "blend": {
                    "alphaBlend": {"value": "Add", "valueId": 1},
                    "zWrite": True,
                    "zTest": False,
                }
            },
        },
    )

    assert values.renderer_type == "Sprite"
    assert values.alpha_blend == "Add"


def test_smoke_rgba_payload_accepts_standard_color_fixed() -> None:
    assert extract_rgba_payload(
        {
            "type": {"value": "Fixed", "valueId": 0},
            "fixed": {"r": 1, "g": 2, "b": 3, "a": 4, "colorSpace": "sRGB"},
            "random": {},
            "easing": {},
            "fcurve": {},
            "gradient": {},
        },
        "colorAll",
    ) == RgbaValues(r=1, g=2, b=3, a=4)


def test_smoke_rgba_payload_accepts_direct_rgba() -> None:
    assert extract_rgba_payload(
        {"r": 1, "g": 2, "b": 3, "a": 4},
        "fixedColors.lowerLeft",
    ) == RgbaValues(r=1, g=2, b=3, a=4)


@pytest.mark.parametrize("invalid_value", [True, -1, 256])
def test_smoke_rgba_payload_rejects_invalid_channels(invalid_value: object) -> None:
    try:
        extract_rgba_payload(
            {"r": invalid_value, "g": 2, "b": 3, "a": 4},
            "colorAll.fixed",
        )
    except SmokeBridgeError as exc:
        assert "colorAll.fixed.r" in str(exc)
    else:
        raise AssertionError("expected SmokeBridgeError")


def test_smoke_rgba_payload_rejects_standard_color_missing_fixed() -> None:
    try:
        extract_rgba_payload(
            {
                "type": {"value": "Fixed", "valueId": 0},
                "random": {},
                "easing": {},
                "fcurve": {},
                "gradient": {},
            },
            "colorAll",
        )
    except SmokeBridgeError as exc:
        assert "colorAll.fixed" in str(exc)
    else:
        raise AssertionError("expected SmokeBridgeError")


def test_smoke_enum_payload_accepts_raw_string_compatibility() -> None:
    assert extract_enum_payload("Sprite", "rendererType") == "Sprite"


@pytest.mark.parametrize(
    "invalid_value",
    [
        "",
        True,
        1,
        {"value": True, "valueId": 0},
        {"value": 1, "valueId": 0},
        {"valueId": 0},
    ],
)
def test_smoke_enum_payload_rejects_invalid_values(invalid_value: object) -> None:
    try:
        extract_enum_payload(invalid_value, "rendererType")
    except SmokeBridgeError as exc:
        assert "rendererType" in str(exc)
    else:
        raise AssertionError("expected SmokeBridgeError")


def test_smoke_generation_values_accept_payload_objects() -> None:
    max_generation, life = get_generation_write_values(
        {
            "ok": True,
            "result": {
                "maxGeneration": {"value": 1, "infinite": False},
                "life": {"center": 60, "min": 60, "max": 60},
            },
        }
    )

    assert max_generation == MaxGenerationValue(
        value=1,
        infinite=False,
        payload={"value": 1, "infinite": False},
    )
    assert life == LifeValues(center=60, min=60, max=60)


def test_smoke_motion_timing_fade_values_accept_nested_payloads() -> None:
    values = get_motion_timing_fade_write_values(
        {
            "ok": True,
            "result": {
                "generation": {
                    "generationTime": {"center": 1.0, "min": 0.5, "max": 2.0}
                }
            },
        },
        {
            "ok": True,
            "result": {
                "location": {
                    "type": {"value": "PVA", "valueId": 1},
                    "pva": {
                        "location": vector_random_payload(
                            ((0.0, 0.0, 0.0), (1.0, 1.0, 1.0), (2.0, 2.0, 2.0))
                        ),
                        "velocity": vector_random_payload(
                            ((3.0, 3.0, 3.0), (4.0, 4.0, 4.0), (5.0, 5.0, 5.0))
                        ),
                        "acceleration": vector_random_payload(
                            ((6.0, 6.0, 6.0), (7.0, 7.0, 7.0), (8.0, 8.0, 8.0))
                        ),
                    },
                },
                "scale": {
                    "type": "PVA",
                    "pva": {
                        "scale": vector_random_payload(
                            ((1.0, 1.0, 1.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0))
                        ),
                        "velocity": vector_random_payload(
                            (
                                (-0.1, -0.1, -0.1),
                                (-0.1, -0.1, -0.1),
                                (-0.1, -0.1, -0.1),
                            )
                        ),
                        "acceleration": vector_random_payload(
                            ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
                        ),
                    },
                },
            },
        },
        {
            "ok": True,
            "result": {
                "fade": {
                    "fadeInType": {"value": "Use", "valueId": 1},
                    "fadeIn": {"frame": {"value": 2.0}},
                    "fadeOutType": {"value": "WithinLifetime", "valueId": 1},
                    "fadeOut": {"frame": {"value": 8.0}},
                }
            },
        },
    )

    assert values.generation_time == RandomFloatValues(
        center=1.0,
        min=0.5,
        max=2.0,
    )
    assert values.location_type == "PVA"
    assert values.scale_type == "PVA"
    assert values.fade_in_type == "Use"
    assert values.fade_in_frame == 2.0
    assert values.fade_out_type == "WithinLifetime"
    assert values.fade_out_frame == 8.0


@pytest.mark.parametrize("invalid_value", [True, math.nan, math.inf])
def test_smoke_motion_timing_fade_values_reject_invalid_random_payload(
    invalid_value: object,
) -> None:
    with pytest.raises(SmokeBridgeError):
        get_motion_timing_fade_write_values(
            {
                "ok": True,
                "result": {
                    "generation": {
                        "generationTime": {
                            "center": invalid_value,
                            "min": 0.0,
                            "max": 1.0,
                        }
                    }
                },
            },
            FakeBridgeClient().get_node_transform_parameters_by_automation_id(
                "auto-child"
            ),
            FakeBridgeClient().get_node_renderer_parameters_by_automation_id(
                "auto-child"
            ),
        )


def test_smoke_generation_values_accept_raw_int_compatibility() -> None:
    max_generation, life = get_generation_write_values(
        {
            "ok": True,
            "result": {
                "maxGeneration": 1,
                "life": 60,
            },
        }
    )

    assert max_generation == MaxGenerationValue(value=1, infinite=None, payload=1)
    assert life == LifeValues(center=60, min=60, max=60)


def test_smoke_generation_values_accept_infinite_true_by_value() -> None:
    max_generation, life = get_generation_write_values(
        {
            "ok": True,
            "result": {
                "maxGeneration": {"value": 1, "infinite": True},
                "life": {"center": 60, "min": 60, "max": 60},
            },
        }
    )

    assert max_generation.value == 1
    assert max_generation.infinite is True
    assert life == LifeValues(center=60, min=60, max=60)


def test_smoke_max_generation_write_response_accepts_after_int() -> None:
    actual = get_max_generation_write_response_value(
        {"ok": True, "result": {"after": 2}}
    )

    assert actual == MaxGenerationValue(value=2, infinite=None, payload=2)


def test_smoke_max_generation_write_response_accepts_after_payload() -> None:
    actual = get_max_generation_write_response_value(
        {"ok": True, "result": {"after": {"value": 2, "infinite": False}}}
    )

    assert actual == MaxGenerationValue(
        value=2,
        infinite=False,
        payload={"value": 2, "infinite": False},
    )


def test_smoke_max_generation_write_response_accepts_generation_parameters() -> None:
    actual = get_max_generation_write_response_value(
        {
            "ok": True,
            "result": {
                "generationParameters": {
                    "maxGeneration": {"value": 2, "infinite": False}
                }
            },
        }
    )

    assert actual == MaxGenerationValue(
        value=2,
        infinite=False,
        payload={"value": 2, "infinite": False},
    )


def test_smoke_generation_values_reject_bool_payloads() -> None:
    try:
        get_generation_write_values(
            {
                "ok": True,
                "result": {
                    "maxGeneration": {"value": True},
                    "life": {"center": 60, "min": 60, "max": 60},
                },
            }
        )
    except SmokeBridgeError as exc:
        assert "maxGeneration was not an int payload" in str(exc)
    else:
        raise AssertionError("expected SmokeBridgeError")


def test_smoke_transform_values_read_fixed_location_path() -> None:
    location, rotation, scale = get_transform_write_values(
        {
            "ok": True,
            "result": {
                "location": {
                    "fixed": {"location": {"x": 0, "y": 10, "z": 0}},
                },
                "rotation": {
                    "fixed": {"rotation": {"x": 1, "y": 2, "z": 3}},
                },
                "scale": {
                    "fixed": {"scale": {"x": 1, "y": 1, "z": 1}},
                },
            },
        }
    )

    assert location == VectorValues(x=0, y=10, z=0)
    assert rotation == VectorValues(x=1, y=2, z=3)
    assert scale == VectorValues(x=1, y=1, z=1)


def test_smoke_transform_values_ignore_pva_payloads() -> None:
    location, _, _ = get_transform_write_values(
        {
            "ok": True,
            "result": {
                "location": {
                    "fixed": {"location": {"x": 0, "y": 10, "z": 0}},
                    "pva": {"location": pva_vector_payload()},
                },
                "rotation": {
                    "fixed": {"rotation": {"x": 1, "y": 2, "z": 3}},
                    "pva": {"rotation": pva_vector_payload()},
                },
                "scale": {
                    "fixed": {"scale": {"x": 1, "y": 1, "z": 1}},
                    "pva": {"scale": pva_vector_payload()},
                },
            },
        }
    )

    assert location == VectorValues(x=0, y=10, z=0)


@pytest.mark.parametrize("invalid_value", [True, math.nan, math.inf, -math.inf])
def test_smoke_transform_values_reject_invalid_fixed_numbers(
    invalid_value: object,
) -> None:
    try:
        get_transform_write_values(
            {
                "ok": True,
                "result": {
                    "location": {
                        "fixed": {
                            "location": {"x": invalid_value, "y": 10, "z": 0}
                        },
                    },
                    "rotation": {
                        "fixed": {"rotation": {"x": 1, "y": 2, "z": 3}},
                    },
                    "scale": {
                        "fixed": {"scale": {"x": 1, "y": 1, "z": 1}},
                    },
                },
            }
        )
    except SmokeBridgeError as exc:
        assert "location.fixed.location.x" in str(exc)
    else:
        raise AssertionError("expected SmokeBridgeError")


def test_smoke_life_values_reject_bool_payloads() -> None:
    try:
        get_generation_write_values(
            {
                "ok": True,
                "result": {
                    "maxGeneration": {"value": 1},
                    "life": {"center": True, "min": 60, "max": 60},
                },
            }
        )
    except SmokeBridgeError as exc:
        assert "life was not an int payload" in str(exc)
    else:
        raise AssertionError("expected SmokeBridgeError")


def test_smoke_assert_basic_info_reports_bridge_error() -> None:
    try:
        assert_basic_info(
            {
                "ok": False,
                "error": "node not found",
            },
            automation_node_id="missing",
            name="Missing",
        )
    except SmokeBridgeError as exc:
        assert "node not found" in str(exc)
    else:
        raise AssertionError("expected SmokeBridgeError")


def test_smoke_duplicate_node_ids_are_warning_only() -> None:
    tree = {
        "nodes": [
            {"automationNodeId": "auto-1", "name": "A"},
            {"automationNodeId": "auto-1", "name": "B"},
        ]
    }
    stderr = StringIO()

    duplicates = warn_about_duplicate_node_ids(tree, stderr=stderr)

    assert duplicates == ["auto-1"]
    assert "WARNING: duplicate automationNodeId detected: auto-1" in stderr.getvalue()

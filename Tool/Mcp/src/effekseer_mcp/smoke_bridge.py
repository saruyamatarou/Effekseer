from __future__ import annotations

import math
import sys
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

from effekseer_mcp.bridge_client import EffekseerBridgeClient, EffekseerBridgeError
from effekseer_mcp.config import load_config

SMOKE_ROOT_PREFIX = "SmokeTestRoot"
SMOKE_NODE_PREFIX = "SmokeTestNode"
RENAMED_NODE_PREFIX = "SmokeTestRenamed"
DUPLICATE_NODE_PREFIX = "SmokeTestDuplicate"
WRAPPER_NODE_PREFIX = "SmokeTestWrapper"
LEGACY_SMOKE_NODE_NAMES = frozenset(
    {
        SMOKE_ROOT_PREFIX,
        SMOKE_NODE_PREFIX,
        RENAMED_NODE_PREFIX,
        DUPLICATE_NODE_PREFIX,
        WRAPPER_NODE_PREFIX,
    }
)
AUTOMATION_NODE_ID_KEYS = ("automationNodeId", "automation_node_id")
NODE_ID_KEYS = ("editorNodeId", "editor_node_id", "id")
NODE_NAME_KEYS = ("name", "nodeName", "node_name")
ROOT_KEYS = ("root", "rootNode", "nodeTree", "tree")
PARENT_AUTOMATION_ID_KEYS = (
    "parentAutomationNodeId",
    "parent_automation_node_id",
)
BASIC_INFO_REQUIRED_KEYS = frozenset(
    {
        "automationNodeId",
        "name",
        "childCount",
        "isRendered",
        "nodeType",
        "className",
    }
)
EXPECTED_PARAMETER_GROUPS = frozenset(
    {
        "node_base",
        "common",
        "generation",
        "location",
        "rotation",
        "scale",
    }
)
REQUIRED_BRIDGE_COMMANDS = frozenset(
    {
        "ping",
        "get_status",
        "get_bridge_capabilities",
        "get_workspace_status",
        "save_project_to_workspace",
        "open_project_from_workspace",
        "export_runtime_effect_to_workspace",
        "get_node_tree",
        "add_node_to_parent_by_automation_id",
        "rename_node_by_automation_id",
        "get_node_basic_info_by_automation_id",
        "get_node_parameter_groups_by_automation_id",
        "get_node_base_parameters_by_automation_id",
        "get_node_generation_parameters_by_automation_id",
        "get_node_transform_parameters_by_automation_id",
        "get_node_drawing_parameters_by_automation_id",
        "get_node_renderer_parameters_by_automation_id",
        "set_node_is_rendered_by_automation_id",
        "set_node_max_generation_by_automation_id",
        "set_node_life_by_automation_id",
        "set_node_fixed_location_by_automation_id",
        "set_node_fixed_rotation_by_automation_id",
        "set_node_fixed_scale_by_automation_id",
        "set_node_generation_time_by_automation_id",
        "set_node_location_type_by_automation_id",
        "set_node_location_pva_by_automation_id",
        "set_node_scale_type_by_automation_id",
        "set_node_scale_pva_by_automation_id",
        "set_node_fade_in_out_by_automation_id",
        "set_node_color_all_fixed_rgba_by_automation_id",
        "set_node_sprite_corner_colors_fixed_rgba_by_automation_id",
        "set_node_alpha_blend_by_automation_id",
        "set_node_z_write_by_automation_id",
        "set_node_z_test_by_automation_id",
        "set_node_renderer_type_by_automation_id",
        "set_node_color_texture_from_workspace_by_automation_id",
        "set_node_normal_texture_from_workspace_by_automation_id",
        "clear_node_color_texture_by_automation_id",
        "clear_node_normal_texture_by_automation_id",
        "set_node_material_from_workspace_by_automation_id",
        "clear_node_material_by_automation_id",
        "set_node_model_from_workspace_by_automation_id",
        "duplicate_node_by_automation_id",
        "insert_parent_node_by_automation_id",
        "remove_node_by_automation_id",
        "undo",
        "redo",
        "play_viewer",
        "step_viewer",
        "stop_viewer",
        "back_step_viewer",
    }
)
BASE_PARAMETERS_REQUIRED_KEYS = BASIC_INFO_REQUIRED_KEYS
GENERATION_PARAMETERS_REQUIRED_KEYS = frozenset(
    {
        "automationNodeId",
        "name",
        "maxGeneration",
        "life",
        "generation",
    }
)
TRANSFORM_PARAMETERS_REQUIRED_KEYS = frozenset(
    {
        "automationNodeId",
        "name",
        "location",
        "rotation",
        "scale",
    }
)
DRAWING_PARAMETERS_REQUIRED_KEYS = frozenset(
    {
        "automationNodeId",
        "name",
        "rendererType",
        "textureUVType",
        "colorAll",
        "sprite",
    }
)
RENDERER_PARAMETERS_REQUIRED_KEYS = frozenset(
    {
        "automationNodeId",
        "name",
        "material",
        "textures",
        "blend",
        "uv",
    }
)
SMOKE_TEXTURE_RELATIVE_PATH = "inputs/textures/smoke_color.png"
SMOKE_MATERIAL_RELATIVE_PATH = "inputs/materials/smoke.efkmat"
SMOKE_MODEL_RELATIVE_PATH = "inputs/models/smoke.efkmodel"
SMOKE_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c63f8cfc0f01f00050001ff89993d1d0000000049454e44"
    "ae426082"
)


class SmokeBridgeError(RuntimeError):
    """Raised when the bridge smoke test cannot complete."""


@dataclass(frozen=True)
class SmokeNames:
    run_id: str
    root: str
    node: str
    renamed: str
    duplicate: str
    wrapper: str

    @property
    def all_names(self) -> frozenset[str]:
        return frozenset(
            {
                self.root,
                self.node,
                self.renamed,
                self.duplicate,
                self.wrapper,
            }
        )


@dataclass(frozen=True)
class LifeValues:
    center: int
    min: int
    max: int


@dataclass(frozen=True)
class MaxGenerationValue:
    value: int
    infinite: bool | None
    payload: Any


@dataclass(frozen=True)
class VectorValues:
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class RandomFloatValues:
    center: float
    min: float
    max: float

    def as_dict(self) -> dict[str, float]:
        return {"center": self.center, "min": self.min, "max": self.max}


@dataclass(frozen=True)
class VectorRandomValues:
    x: RandomFloatValues
    y: RandomFloatValues
    z: RandomFloatValues

    def as_dict(self) -> dict[str, dict[str, float]]:
        return {
            "x": self.x.as_dict(),
            "y": self.y.as_dict(),
            "z": self.z.as_dict(),
        }


@dataclass(frozen=True)
class RgbaValues:
    r: int
    g: int
    b: int
    a: int

    def as_dict(self) -> dict[str, int]:
        return {"r": self.r, "g": self.g, "b": self.b, "a": self.a}


@dataclass(frozen=True)
class SpriteCornerColors:
    lower_left: RgbaValues
    lower_right: RgbaValues
    upper_left: RgbaValues
    upper_right: RgbaValues


@dataclass(frozen=True)
class DrawingRendererWriteValues:
    renderer_type: str
    color_all: RgbaValues
    corner_colors: SpriteCornerColors
    alpha_blend: str
    z_write: bool
    z_test: bool


@dataclass(frozen=True)
class BasicWriteValues:
    max_generation: MaxGenerationValue
    life: LifeValues
    location: VectorValues
    rotation: VectorValues
    scale: VectorValues


@dataclass(frozen=True)
class MotionTimingFadeWriteValues:
    generation_time: RandomFloatValues
    location_type: str
    location_pva: VectorRandomValues
    velocity_pva: VectorRandomValues
    acceleration_pva: VectorRandomValues
    scale_type: str
    scale_pva: VectorRandomValues
    scale_velocity_pva: VectorRandomValues
    scale_acceleration_pva: VectorRandomValues
    fade_in_type: str
    fade_in_frame: float
    fade_out_type: str
    fade_out_frame: float


def make_smoke_names(run_id: str | None = None) -> SmokeNames:
    resolved_run_id = run_id or uuid.uuid4().hex[:8]
    return SmokeNames(
        run_id=resolved_run_id,
        root=f"{SMOKE_ROOT_PREFIX}_{resolved_run_id}",
        node=f"{SMOKE_NODE_PREFIX}_{resolved_run_id}",
        renamed=f"{RENAMED_NODE_PREFIX}_{resolved_run_id}",
        duplicate=f"{DUPLICATE_NODE_PREFIX}_{resolved_run_id}",
        wrapper=f"{WRAPPER_NODE_PREFIX}_{resolved_run_id}",
    )


def run_smoke_test(
    client: Any,
    *,
    run_id: str | None = None,
    smoke_texture_path: str | None = None,
    smoke_material_path: str | None = None,
    smoke_model_path: str | None = None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> None:
    names = make_smoke_names(run_id)
    smoke_root_automation_id: str | None = None
    rendered_restore_target_id: str | None = None
    original_is_rendered: bool | None = None
    basic_write_restore_target_id: str | None = None
    original_basic_write_values: BasicWriteValues | None = None
    motion_timing_fade_restore_target_id: str | None = None
    original_motion_timing_fade_values: MotionTimingFadeWriteValues | None = None
    drawing_renderer_restore_target_id: str | None = None
    original_drawing_renderer_values: DrawingRendererWriteValues | None = None
    primary_error: Exception | None = None
    cleanup_error: Exception | None = None

    try:
        _print_step(stdout, "ping")
        client.ping()

        _print_step(stdout, "get_status")
        client.get_status()

        _print_step(stdout, "get_bridge_capabilities")
        assert_bridge_capabilities(
            client.get_bridge_capabilities(),
            REQUIRED_BRIDGE_COMMANDS,
        )

        _print_step(stdout, "get_workspace_status")
        assert_workspace_status(client.get_workspace_status())

        _print_step(stdout, "cleanup legacy smoke nodes")
        cleanup_legacy_smoke_nodes(client, stderr=stderr)

        _print_step(stdout, "get_node_tree")
        tree = client.get_node_tree()
        warn_about_duplicate_node_ids(tree, stderr=stderr)

        root = find_root_node(tree)
        root_automation_id = get_automation_node_id(root)
        if root_automation_id is None:
            raise SmokeBridgeError("root node does not have an automationNodeId")

        _print_step(
            stdout,
            f"add_node_to_parent_by_automation_id({root_automation_id}, "
            f"{names.root})",
        )
        smoke_root_response = client.add_node_to_parent_by_automation_id(
            root_automation_id,
            names.root,
        )

        _print_step(stdout, f"verify {names.root}")
        tree = client.get_node_tree()
        warn_about_duplicate_node_ids(tree, stderr=stderr)
        smoke_root_automation_id = extract_automation_node_id(
            smoke_root_response,
            "added_node",
        ) or find_automation_node_id_by_name(tree, names.root)
        if smoke_root_automation_id is None:
            raise SmokeBridgeError(f"{names.root} was not found in node tree")

        _print_step(
            stdout,
            f"add_node_to_parent_by_automation_id({smoke_root_automation_id}, "
            f"{names.node})",
        )
        add_response = client.add_node_to_parent_by_automation_id(
            smoke_root_automation_id,
            names.node,
        )

        _print_step(stdout, f"verify {names.node}")
        tree = client.get_node_tree()
        warn_about_duplicate_node_ids(tree, stderr=stderr)
        added_automation_id = extract_automation_node_id(
            add_response,
            "added_node",
        ) or find_automation_node_id_by_name_under(
            tree,
            smoke_root_automation_id,
            names.node,
        )
        if added_automation_id is None:
            raise SmokeBridgeError(f"{names.node} was not found under {names.root}")

        _print_step(
            stdout,
            f"rename_node_by_automation_id({added_automation_id}, {names.renamed})",
        )
        client.rename_node_by_automation_id(added_automation_id, names.renamed)

        _print_step(stdout, f"verify {names.renamed}")
        tree = client.get_node_tree()
        warn_about_duplicate_node_ids(tree, stderr=stderr)
        renamed_automation_id = find_automation_node_id_by_name_under(
            tree,
            smoke_root_automation_id,
            names.renamed,
        )
        if renamed_automation_id is None:
            raise SmokeBridgeError(f"{names.renamed} was not found under {names.root}")

        _print_step(stdout, f"inspect node parameters {renamed_automation_id}")
        tree_signature_before_inspection = get_node_tree_signature(tree)
        basic_info = client.get_node_basic_info_by_automation_id(renamed_automation_id)
        assert_basic_info(
            basic_info,
            automation_node_id=renamed_automation_id,
            name=names.renamed,
        )
        parameter_groups = client.get_node_parameter_groups_by_automation_id(
            renamed_automation_id,
        )
        assert_parameter_groups(parameter_groups, EXPECTED_PARAMETER_GROUPS)
        tree_after_inspection = client.get_node_tree()
        warn_about_duplicate_node_ids(tree_after_inspection, stderr=stderr)
        if get_node_tree_signature(tree_after_inspection) != (
            tree_signature_before_inspection
        ):
            raise SmokeBridgeError("read-only parameter inspection changed node tree")
        tree = tree_after_inspection

        _print_step(stdout, f"inspect parameter values {renamed_automation_id}")
        tree_signature_before_value_inspection = get_node_tree_signature(tree)
        base_parameters = client.get_node_base_parameters_by_automation_id(
            renamed_automation_id,
        )
        rendered_restore_target_id = renamed_automation_id
        original_is_rendered = get_is_rendered(base_parameters)
        assert_required_parameter_keys(
            base_parameters,
            BASE_PARAMETERS_REQUIRED_KEYS,
            label="base parameters",
            automation_node_id=renamed_automation_id,
            name=names.renamed,
        )
        generation_parameters = client.get_node_generation_parameters_by_automation_id(
            renamed_automation_id,
        )
        original_max_generation, original_life = get_generation_write_values(
            generation_parameters,
        )
        assert_required_parameter_keys(
            generation_parameters,
            GENERATION_PARAMETERS_REQUIRED_KEYS,
            label="generation parameters",
            automation_node_id=renamed_automation_id,
            name=names.renamed,
        )
        transform_parameters = client.get_node_transform_parameters_by_automation_id(
            renamed_automation_id,
        )
        original_location, original_rotation, original_scale = (
            get_transform_write_values(transform_parameters)
        )
        basic_write_restore_target_id = renamed_automation_id
        original_basic_write_values = BasicWriteValues(
            max_generation=original_max_generation,
            life=original_life,
            location=original_location,
            rotation=original_rotation,
            scale=original_scale,
        )
        assert_required_parameter_keys(
            transform_parameters,
            TRANSFORM_PARAMETERS_REQUIRED_KEYS,
            label="transform parameters",
            automation_node_id=renamed_automation_id,
            name=names.renamed,
        )
        drawing_parameters = client.get_node_drawing_parameters_by_automation_id(
            renamed_automation_id,
        )
        assert_required_parameter_keys(
            drawing_parameters,
            DRAWING_PARAMETERS_REQUIRED_KEYS,
            label="drawing parameters",
            automation_node_id=renamed_automation_id,
            name=names.renamed,
        )
        renderer_parameters = client.get_node_renderer_parameters_by_automation_id(
            renamed_automation_id,
        )
        drawing_renderer_restore_target_id = renamed_automation_id
        original_drawing_renderer_values = get_drawing_renderer_write_values(
            drawing_parameters,
            renderer_parameters,
        )
        assert_required_parameter_keys(
            renderer_parameters,
            RENDERER_PARAMETERS_REQUIRED_KEYS,
            label="renderer parameters",
            automation_node_id=renamed_automation_id,
            name=names.renamed,
        )
        tree_after_value_inspection = client.get_node_tree()
        warn_about_duplicate_node_ids(tree_after_value_inspection, stderr=stderr)
        if get_node_tree_signature(tree_after_value_inspection) != (
            tree_signature_before_value_inspection
        ):
            raise SmokeBridgeError(
                "read-only parameter value inspection changed node tree"
            )
        tree = tree_after_value_inspection

        toggled_is_rendered = not original_is_rendered
        _print_step(
            stdout,
            f"set_node_is_rendered_by_automation_id({renamed_automation_id}, "
            f"{toggled_is_rendered})",
        )
        client.set_node_is_rendered_by_automation_id(
            renamed_automation_id,
            toggled_is_rendered,
        )
        assert_is_rendered(
            client.get_node_base_parameters_by_automation_id(renamed_automation_id),
            toggled_is_rendered,
            label="set isRendered",
        )

        _print_step(stdout, "undo isRendered")
        client.undo()
        assert_is_rendered(
            client.get_node_base_parameters_by_automation_id(renamed_automation_id),
            original_is_rendered,
            label="undo isRendered",
        )

        _print_step(stdout, "redo isRendered")
        client.redo()
        assert_is_rendered(
            client.get_node_base_parameters_by_automation_id(renamed_automation_id),
            toggled_is_rendered,
            label="redo isRendered",
        )

        _print_step(stdout, f"restore isRendered {original_is_rendered}")
        client.set_node_is_rendered_by_automation_id(
            renamed_automation_id,
            original_is_rendered,
        )
        assert_is_rendered(
            client.get_node_base_parameters_by_automation_id(renamed_automation_id),
            original_is_rendered,
            label="restore isRendered",
        )
        rendered_restore_target_id = None
        original_is_rendered = None

        updated_basic_write_values = make_updated_basic_write_values(
            original_basic_write_values,
        )
        _print_step(
            stdout,
            f"set_node_max_generation_by_automation_id({renamed_automation_id}, "
            f"{updated_basic_write_values.max_generation.value})",
        )
        max_generation_response = client.set_node_max_generation_by_automation_id(
            renamed_automation_id,
            updated_basic_write_values.max_generation.value,
        )
        assert_max_generation_write_response(
            max_generation_response,
            updated_basic_write_values.max_generation.value,
            label="set maxGeneration response",
        )

        _print_step(stdout, f"set_node_life_by_automation_id({renamed_automation_id})")
        client.set_node_life_by_automation_id(
            renamed_automation_id,
            updated_basic_write_values.life.center,
            updated_basic_write_values.life.min,
            updated_basic_write_values.life.max,
        )

        _print_step(
            stdout,
            f"set_node_fixed_location_by_automation_id({renamed_automation_id})",
        )
        client.set_node_fixed_location_by_automation_id(
            renamed_automation_id,
            updated_basic_write_values.location.x,
            updated_basic_write_values.location.y,
            updated_basic_write_values.location.z,
        )

        _print_step(
            stdout,
            f"set_node_fixed_rotation_by_automation_id({renamed_automation_id})",
        )
        client.set_node_fixed_rotation_by_automation_id(
            renamed_automation_id,
            updated_basic_write_values.rotation.x,
            updated_basic_write_values.rotation.y,
            updated_basic_write_values.rotation.z,
        )

        _print_step(
            stdout,
            f"set_node_fixed_scale_by_automation_id({renamed_automation_id})",
        )
        client.set_node_fixed_scale_by_automation_id(
            renamed_automation_id,
            updated_basic_write_values.scale.x,
            updated_basic_write_values.scale.y,
            updated_basic_write_values.scale.z,
        )

        assert_basic_write_values(
            client,
            renamed_automation_id,
            updated_basic_write_values,
            label="basic parameter write",
        )

        _print_step(stdout, "undo fixed scale")
        client.undo()
        assert_vector_parameter(
            client.get_node_transform_parameters_by_automation_id(
                renamed_automation_id,
            ),
            "scale",
            original_basic_write_values.scale,
            label="undo fixed scale",
        )

        _print_step(stdout, "redo fixed scale")
        client.redo()
        assert_vector_parameter(
            client.get_node_transform_parameters_by_automation_id(
                renamed_automation_id,
            ),
            "scale",
            updated_basic_write_values.scale,
            label="redo fixed scale",
        )

        _print_step(stdout, "restore basic parameter writes")
        restore_basic_write_values(
            client,
            renamed_automation_id,
            original_basic_write_values,
        )
        assert_basic_write_values(
            client,
            renamed_automation_id,
            original_basic_write_values,
            label="restore basic parameter writes",
        )
        basic_write_restore_target_id = None
        original_basic_write_values = None

        motion_generation_parameters = (
            client.get_node_generation_parameters_by_automation_id(
                renamed_automation_id,
            )
        )
        motion_transform_parameters = client.get_node_transform_parameters_by_automation_id(
            renamed_automation_id,
        )
        motion_renderer_parameters = client.get_node_renderer_parameters_by_automation_id(
            renamed_automation_id,
        )
        original_motion_timing_fade_values = get_motion_timing_fade_write_values(
            motion_generation_parameters,
            motion_transform_parameters,
            motion_renderer_parameters,
        )
        motion_timing_fade_restore_target_id = renamed_automation_id
        updated_motion_timing_fade_values = make_updated_motion_timing_fade_values(
            original_motion_timing_fade_values,
        )

        _print_step(stdout, "set_node_generation_time_by_automation_id")
        client.set_node_generation_time_by_automation_id(
            renamed_automation_id,
            updated_motion_timing_fade_values.generation_time.center,
            updated_motion_timing_fade_values.generation_time.min,
            updated_motion_timing_fade_values.generation_time.max,
        )

        _print_step(stdout, "set_node_location_type_by_automation_id")
        client.set_node_location_type_by_automation_id(
            renamed_automation_id,
            updated_motion_timing_fade_values.location_type,
        )

        _print_step(stdout, "set_node_location_pva_by_automation_id")
        client.set_node_location_pva_by_automation_id(
            renamed_automation_id,
            updated_motion_timing_fade_values.location_pva.as_dict(),
            updated_motion_timing_fade_values.velocity_pva.as_dict(),
            updated_motion_timing_fade_values.acceleration_pva.as_dict(),
        )

        _print_step(stdout, "set_node_scale_type_by_automation_id")
        client.set_node_scale_type_by_automation_id(
            renamed_automation_id,
            updated_motion_timing_fade_values.scale_type,
        )

        _print_step(stdout, "set_node_scale_pva_by_automation_id")
        client.set_node_scale_pva_by_automation_id(
            renamed_automation_id,
            updated_motion_timing_fade_values.scale_pva.as_dict(),
            updated_motion_timing_fade_values.scale_velocity_pva.as_dict(),
            updated_motion_timing_fade_values.scale_acceleration_pva.as_dict(),
        )

        _print_step(stdout, "set_node_fade_in_out_by_automation_id")
        client.set_node_fade_in_out_by_automation_id(
            renamed_automation_id,
            updated_motion_timing_fade_values.fade_in_type,
            updated_motion_timing_fade_values.fade_in_frame,
            updated_motion_timing_fade_values.fade_out_type,
            updated_motion_timing_fade_values.fade_out_frame,
        )

        assert_motion_timing_fade_write_values(
            client,
            renamed_automation_id,
            updated_motion_timing_fade_values,
            label="motion timing fade write",
        )

        _print_step(stdout, "undo fade")
        client.undo()
        assert_motion_timing_fade_write_values(
            client,
            renamed_automation_id,
            MotionTimingFadeWriteValues(
                generation_time=updated_motion_timing_fade_values.generation_time,
                location_type=updated_motion_timing_fade_values.location_type,
                location_pva=updated_motion_timing_fade_values.location_pva,
                velocity_pva=updated_motion_timing_fade_values.velocity_pva,
                acceleration_pva=updated_motion_timing_fade_values.acceleration_pva,
                scale_type=updated_motion_timing_fade_values.scale_type,
                scale_pva=updated_motion_timing_fade_values.scale_pva,
                scale_velocity_pva=updated_motion_timing_fade_values.scale_velocity_pva,
                scale_acceleration_pva=(
                    updated_motion_timing_fade_values.scale_acceleration_pva
                ),
                fade_in_type=original_motion_timing_fade_values.fade_in_type,
                fade_in_frame=original_motion_timing_fade_values.fade_in_frame,
                fade_out_type=original_motion_timing_fade_values.fade_out_type,
                fade_out_frame=original_motion_timing_fade_values.fade_out_frame,
            ),
            label="undo fade",
        )

        _print_step(stdout, "redo fade")
        client.redo()
        assert_motion_timing_fade_write_values(
            client,
            renamed_automation_id,
            updated_motion_timing_fade_values,
            label="redo fade",
        )

        _print_step(stdout, "restore motion timing fade writes")
        restore_motion_timing_fade_write_values(
            client,
            renamed_automation_id,
            original_motion_timing_fade_values,
        )
        assert_motion_timing_fade_write_values(
            client,
            renamed_automation_id,
            original_motion_timing_fade_values,
            label="restore motion timing fade writes",
        )
        motion_timing_fade_restore_target_id = None
        original_motion_timing_fade_values = None

        updated_drawing_renderer_values = make_updated_drawing_renderer_values(
            original_drawing_renderer_values,
        )
        _print_step(stdout, "set_node_color_all_fixed_rgba_by_automation_id")
        client.set_node_color_all_fixed_rgba_by_automation_id(
            renamed_automation_id,
            updated_drawing_renderer_values.color_all.r,
            updated_drawing_renderer_values.color_all.g,
            updated_drawing_renderer_values.color_all.b,
            updated_drawing_renderer_values.color_all.a,
        )

        _print_step(
            stdout,
            "set_node_sprite_corner_colors_fixed_rgba_by_automation_id",
        )
        client.set_node_sprite_corner_colors_fixed_rgba_by_automation_id(
            renamed_automation_id,
            updated_drawing_renderer_values.corner_colors.lower_left.as_dict(),
            updated_drawing_renderer_values.corner_colors.lower_right.as_dict(),
            updated_drawing_renderer_values.corner_colors.upper_left.as_dict(),
            updated_drawing_renderer_values.corner_colors.upper_right.as_dict(),
        )

        _print_step(stdout, "set_node_alpha_blend_by_automation_id")
        client.set_node_alpha_blend_by_automation_id(
            renamed_automation_id,
            updated_drawing_renderer_values.alpha_blend,
        )

        _print_step(stdout, "set_node_z_write_by_automation_id")
        client.set_node_z_write_by_automation_id(
            renamed_automation_id,
            updated_drawing_renderer_values.z_write,
        )

        _print_step(stdout, "set_node_z_test_by_automation_id")
        client.set_node_z_test_by_automation_id(
            renamed_automation_id,
            updated_drawing_renderer_values.z_test,
        )

        _print_step(stdout, "set_node_renderer_type_by_automation_id")
        client.set_node_renderer_type_by_automation_id(
            renamed_automation_id,
            updated_drawing_renderer_values.renderer_type,
        )

        assert_drawing_renderer_write_values(
            client,
            renamed_automation_id,
            updated_drawing_renderer_values,
            label="drawing renderer write",
        )

        _print_step(stdout, "undo renderer type")
        client.undo()
        assert_drawing_renderer_write_values(
            client,
            renamed_automation_id,
            DrawingRendererWriteValues(
                renderer_type=original_drawing_renderer_values.renderer_type,
                color_all=updated_drawing_renderer_values.color_all,
                corner_colors=updated_drawing_renderer_values.corner_colors,
                alpha_blend=updated_drawing_renderer_values.alpha_blend,
                z_write=updated_drawing_renderer_values.z_write,
                z_test=updated_drawing_renderer_values.z_test,
            ),
            label="undo renderer type",
        )

        _print_step(stdout, "redo renderer type")
        client.redo()
        assert_drawing_renderer_write_values(
            client,
            renamed_automation_id,
            updated_drawing_renderer_values,
            label="redo renderer type",
        )

        _print_step(stdout, "restore drawing renderer writes")
        restore_drawing_renderer_write_values(
            client,
            renamed_automation_id,
            original_drawing_renderer_values,
        )
        assert_drawing_renderer_write_values(
            client,
            renamed_automation_id,
            original_drawing_renderer_values,
            label="restore drawing renderer writes",
        )
        drawing_renderer_restore_target_id = None
        original_drawing_renderer_values = None

        _print_step(stdout, "prepare smoke texture")
        smoke_texture_path = smoke_texture_path or ensure_smoke_texture_file()

        _print_step(stdout, "set_node_color_texture_from_workspace_by_automation_id")
        assert_workspace_texture_assignment_response(
            client.set_node_color_texture_from_workspace_by_automation_id(
                renamed_automation_id,
                smoke_texture_path,
            ),
            smoke_texture_path,
            label="color texture assignment",
        )
        assert_texture_reference_has_value(
            client.get_node_renderer_parameters_by_automation_id(renamed_automation_id),
            "colorTexture",
            label="color texture readback",
        )

        _print_step(stdout, "set_node_normal_texture_from_workspace_by_automation_id")
        assert_workspace_texture_assignment_response(
            client.set_node_normal_texture_from_workspace_by_automation_id(
                renamed_automation_id,
                smoke_texture_path,
            ),
            smoke_texture_path,
            label="normal texture assignment",
        )
        assert_texture_reference_has_value(
            client.get_node_renderer_parameters_by_automation_id(renamed_automation_id),
            "normalTexture",
            label="normal texture readback",
        )

        smoke_material_path = smoke_material_path or find_existing_smoke_material_file()
        material_assignment_enabled = smoke_material_path is not None
        if smoke_material_path is None:
            print(
                f"WARNING: skipping material assignment smoke; "
                f"{SMOKE_MATERIAL_RELATIVE_PATH} was not found",
                file=stderr,
            )
        else:
            _print_step(stdout, "set_node_material_from_workspace_by_automation_id")
            assert_workspace_material_assignment_response(
                client.set_node_material_from_workspace_by_automation_id(
                    renamed_automation_id,
                    smoke_material_path,
                ),
                smoke_material_path,
                label="material assignment",
            )
            assert_material_assignment_readback(
                client.get_node_renderer_parameters_by_automation_id(
                    renamed_automation_id
                ),
                label="material assignment readback",
            )

        _print_step(
            stdout,
            f"duplicate_node_by_automation_id({renamed_automation_id}, "
            f"{names.duplicate})",
        )
        duplicate_response = client.duplicate_node_by_automation_id(
            renamed_automation_id,
            names.duplicate,
        )

        _print_step(stdout, f"verify {names.duplicate}")
        tree = client.get_node_tree()
        warn_about_duplicate_node_ids(tree, stderr=stderr)
        duplicate_automation_id = extract_automation_node_id(
            duplicate_response,
            "duplicated_node",
        ) or find_automation_node_id_by_name_under(
            tree,
            smoke_root_automation_id,
            names.duplicate,
        )
        if duplicate_automation_id is None:
            raise SmokeBridgeError(f"{names.duplicate} was not found under {names.root}")

        _print_step(
            stdout,
            f"insert_parent_node_by_automation_id({duplicate_automation_id}, "
            f"{names.wrapper})",
        )
        wrapper_response = client.insert_parent_node_by_automation_id(
            duplicate_automation_id,
            names.wrapper,
        )

        _print_step(stdout, f"verify {names.wrapper} wraps {names.duplicate}")
        tree = client.get_node_tree()
        warn_about_duplicate_node_ids(tree, stderr=stderr)
        wrapper_automation_id = extract_automation_node_id(
            wrapper_response,
            "inserted_node",
        ) or find_automation_node_id_by_name_under(
            tree,
            smoke_root_automation_id,
            names.wrapper,
        )
        if wrapper_automation_id is None:
            raise SmokeBridgeError(f"{names.wrapper} was not found under {names.root}")
        if (
            find_automation_node_id_by_name_under(
                tree,
                smoke_root_automation_id,
                names.duplicate,
            )
            is None
        ):
            raise SmokeBridgeError(f"{names.duplicate} was not found after wrapping")

        _print_step(stdout, f"remove_node_by_automation_id({wrapper_automation_id})")
        client.remove_node_by_automation_id(wrapper_automation_id)

        _print_step(stdout, f"verify {names.wrapper} removed")
        tree = client.get_node_tree()
        warn_about_duplicate_node_ids(tree, stderr=stderr)
        if (
            find_automation_node_id_by_name_under(
                tree,
                smoke_root_automation_id,
                names.wrapper,
            )
            is not None
        ):
            raise SmokeBridgeError(f"{names.wrapper} was not removed")

        _print_step(stdout, "undo")
        client.undo()

        _print_step(stdout, f"verify undo restored {names.wrapper}")
        tree = client.get_node_tree()
        warn_about_duplicate_node_ids(tree, stderr=stderr)
        if (
            find_automation_node_id_by_name_under(
                tree,
                smoke_root_automation_id,
                names.wrapper,
            )
            is None
        ):
            raise SmokeBridgeError(f"undo did not restore {names.wrapper}")

        _print_step(stdout, "redo")
        client.redo()

        _print_step(stdout, f"verify redo removed {names.wrapper}")
        tree = client.get_node_tree()
        warn_about_duplicate_node_ids(tree, stderr=stderr)
        if (
            find_automation_node_id_by_name_under(
                tree,
                smoke_root_automation_id,
                names.wrapper,
            )
            is not None
        ):
            raise SmokeBridgeError(f"redo did not remove {names.wrapper}")

        _print_step(stdout, "play_viewer")
        client.play_viewer()

        _print_step(stdout, "step_viewer")
        client.step_viewer()

        _print_step(stdout, "stop_viewer")
        client.stop_viewer()

        _print_step(stdout, "back_step_viewer")
        client.back_step_viewer()

        smoke_resource_project_path = f"outputs/smoke_resource_{names.run_id}.efkefc"
        smoke_resource_export_path = f"outputs/smoke_resource_{names.run_id}.efk"
        _print_step(
            stdout,
            f"save_project_to_workspace({smoke_resource_project_path})",
        )
        assert_workspace_project_response(
            client.save_project_to_workspace(smoke_resource_project_path),
            smoke_resource_project_path,
            label="resource project save",
        )

        _print_step(
            stdout,
            f"open_project_from_workspace({smoke_resource_project_path})",
        )
        assert_workspace_project_response(
            client.open_project_from_workspace(smoke_resource_project_path),
            smoke_resource_project_path,
            label="resource project open",
        )

        _print_step(stdout, "verify resource assignments after project open")
        tree = client.get_node_tree()
        warn_about_duplicate_node_ids(tree, stderr=stderr)
        smoke_root_automation_id = find_automation_node_id_by_name(tree, names.root)
        if smoke_root_automation_id is None:
            raise SmokeBridgeError(f"{names.root} was not found after project open")
        renamed_automation_id = find_automation_node_id_by_name_under(
            tree,
            smoke_root_automation_id,
            names.renamed,
        )
        if renamed_automation_id is None:
            raise SmokeBridgeError(f"{names.renamed} was not found after project open")

        renderer_after_open = client.get_node_renderer_parameters_by_automation_id(
            renamed_automation_id,
        )
        assert_texture_reference_has_value(
            renderer_after_open,
            "colorTexture",
            label="persisted color texture readback",
        )
        assert_texture_reference_has_value(
            renderer_after_open,
            "normalTexture",
            label="persisted normal texture readback",
        )
        if material_assignment_enabled:
            assert_material_assignment_readback(
                renderer_after_open,
                label="persisted material assignment readback",
            )

        _print_step(
            stdout,
            f"export_runtime_effect_to_workspace({smoke_resource_export_path})",
        )
        assert_runtime_export_response(
            client.export_runtime_effect_to_workspace(smoke_resource_export_path),
            smoke_resource_export_path,
        )

        _print_step(stdout, "clear_node_color_texture_by_automation_id")
        client.clear_node_color_texture_by_automation_id(renamed_automation_id)
        assert_texture_reference_has_value(
            client.get_node_renderer_parameters_by_automation_id(renamed_automation_id),
            "colorTexture",
            expected_has_value=False,
            label="color texture clear readback",
        )

        _print_step(stdout, "clear_node_normal_texture_by_automation_id")
        client.clear_node_normal_texture_by_automation_id(renamed_automation_id)
        assert_texture_reference_has_value(
            client.get_node_renderer_parameters_by_automation_id(renamed_automation_id),
            "normalTexture",
            expected_has_value=False,
            label="normal texture clear readback",
        )

        if material_assignment_enabled:
            _print_step(stdout, "clear_node_material_by_automation_id")
            client.clear_node_material_by_automation_id(renamed_automation_id)
            assert_material_assignment_readback(
                client.get_node_renderer_parameters_by_automation_id(
                    renamed_automation_id
                ),
                expected_has_value=False,
                expected_material_type="Default",
                label="material clear readback",
            )

        smoke_model_path = smoke_model_path or find_existing_smoke_model_file()
        if smoke_model_path is None:
            print(
                f"WARNING: skipping model assignment smoke; "
                f"{SMOKE_MODEL_RELATIVE_PATH} was not found",
                file=stderr,
            )
        else:
            _print_step(stdout, "set_node_model_from_workspace_by_automation_id")
            assert_workspace_model_assignment_response(
                client.set_node_model_from_workspace_by_automation_id(
                    renamed_automation_id,
                    smoke_model_path,
                ),
                smoke_model_path,
                label="model assignment",
            )
            assert_model_assignment_readback(
                client.get_node_drawing_parameters_by_automation_id(
                    renamed_automation_id
                ),
                label="model assignment readback",
            )

            smoke_model_project_path = f"outputs/smoke_model_{names.run_id}.efkefc"
            smoke_model_export_path = f"outputs/smoke_model_{names.run_id}.efk"
            _print_step(
                stdout,
                f"save_project_to_workspace({smoke_model_project_path})",
            )
            assert_workspace_project_response(
                client.save_project_to_workspace(smoke_model_project_path),
                smoke_model_project_path,
                label="model project save",
            )

            _print_step(
                stdout,
                f"open_project_from_workspace({smoke_model_project_path})",
            )
            assert_workspace_project_response(
                client.open_project_from_workspace(smoke_model_project_path),
                smoke_model_project_path,
                label="model project open",
            )

            _print_step(stdout, "verify model assignment after project open")
            tree = client.get_node_tree()
            warn_about_duplicate_node_ids(tree, stderr=stderr)
            smoke_root_automation_id = find_automation_node_id_by_name(
                tree,
                names.root,
            )
            if smoke_root_automation_id is None:
                raise SmokeBridgeError(
                    f"{names.root} was not found after model project open"
                )
            renamed_automation_id = find_automation_node_id_by_name_under(
                tree,
                smoke_root_automation_id,
                names.renamed,
            )
            if renamed_automation_id is None:
                raise SmokeBridgeError(
                    f"{names.renamed} was not found after model project open"
                )
            assert_model_assignment_readback(
                client.get_node_drawing_parameters_by_automation_id(
                    renamed_automation_id
                ),
                label="persisted model assignment readback",
            )

            _print_step(
                stdout,
                f"export_runtime_effect_to_workspace({smoke_model_export_path})",
            )
            assert_runtime_export_response(
                client.export_runtime_effect_to_workspace(smoke_model_export_path),
                smoke_model_export_path,
            )
    except Exception as exc:
        primary_error = exc
    finally:
        try:
            if (
                rendered_restore_target_id is not None
                and original_is_rendered is not None
            ):
                _print_step(
                    stdout,
                    f"cleanup restore isRendered {original_is_rendered}",
                )
                client.set_node_is_rendered_by_automation_id(
                    rendered_restore_target_id,
                    original_is_rendered,
                )

            if (
                basic_write_restore_target_id is not None
                and original_basic_write_values is not None
            ):
                _print_step(stdout, "cleanup restore basic parameter writes")
                restore_basic_write_values(
                    client,
                    basic_write_restore_target_id,
                    original_basic_write_values,
                )

            if (
                motion_timing_fade_restore_target_id is not None
                and original_motion_timing_fade_values is not None
            ):
                _print_step(stdout, "cleanup restore motion timing fade writes")
                restore_motion_timing_fade_write_values(
                    client,
                    motion_timing_fade_restore_target_id,
                    original_motion_timing_fade_values,
                )

            if (
                drawing_renderer_restore_target_id is not None
                and original_drawing_renderer_values is not None
            ):
                _print_step(stdout, "cleanup restore drawing renderer writes")
                restore_drawing_renderer_write_values(
                    client,
                    drawing_renderer_restore_target_id,
                    original_drawing_renderer_values,
                )

            if smoke_root_automation_id is not None:
                _print_step(
                    stdout,
                    f"cleanup remove_node_by_automation_id({smoke_root_automation_id})",
                )
                client.remove_node_by_automation_id(smoke_root_automation_id)

            _print_step(stdout, f"verify run cleanup {names.run_id}")
            tree = client.get_node_tree()
            warn_about_duplicate_node_ids(tree, stderr=stderr)
            assert_no_run_smoke_nodes(tree, names)
            warn_about_legacy_smoke_nodes(tree, stderr=stderr)
        except Exception as exc:
            cleanup_error = exc

    if primary_error is not None and cleanup_error is not None:
        raise SmokeBridgeError(
            f"{primary_error}; cleanup also failed: {cleanup_error}"
        ) from primary_error
    if primary_error is not None:
        raise primary_error
    if cleanup_error is not None:
        raise cleanup_error

    print("Smoke test passed", file=stdout)


def iter_nodes(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        if get_automation_node_id(value) is not None or get_node_id(value) is not None:
            yield value

        for child_value in value.values():
            yield from iter_nodes(child_value)
    elif isinstance(value, list):
        for item in value:
            yield from iter_nodes(item)


def iter_subtree_nodes(node: dict[str, Any]) -> Iterable[dict[str, Any]]:
    yield node

    for value in node.values():
        if isinstance(value, list):
            for item in value:
                yield from iter_nodes(item)
        elif isinstance(value, dict):
            yield from iter_nodes(value)


def find_root_node(tree: dict[str, Any]) -> dict[str, Any]:
    for key in ROOT_KEYS:
        value = tree.get(key)
        if isinstance(value, dict):
            node = first_node(value)
            if node is not None:
                return node

    nodes = list(iter_nodes(tree))
    if not nodes:
        raise SmokeBridgeError("node tree did not contain any nodes")

    for node in nodes:
        if get_parent_automation_node_id(node) is None:
            return node

    return nodes[0]


def first_node(value: Any) -> dict[str, Any] | None:
    return next(iter(iter_nodes(value)), None)


def find_node_by_automation_id(
    tree: dict[str, Any],
    automation_node_id: str,
) -> dict[str, Any] | None:
    for node in iter_nodes(tree):
        if get_automation_node_id(node) == automation_node_id:
            return node

    return None


def find_node_id_by_name(tree: dict[str, Any], name: str) -> int | None:
    for node in iter_nodes(tree):
        if get_node_name(node) == name:
            return get_node_id(node)

    return None


def find_automation_node_id_by_name(tree: dict[str, Any], name: str) -> str | None:
    for node in iter_nodes(tree):
        if get_node_name(node) == name:
            return get_automation_node_id(node)

    return None


def find_automation_node_id_by_name_under(
    tree: dict[str, Any],
    parent_automation_id: str,
    name: str,
) -> str | None:
    parent_node = find_node_by_automation_id(tree, parent_automation_id)
    if parent_node is None:
        return None

    for node in iter_subtree_nodes(parent_node):
        if get_node_name(node) == name:
            return get_automation_node_id(node)

    return None


def find_run_smoke_node_names(tree: dict[str, Any], names: SmokeNames) -> list[str]:
    found_names = {
        name
        for node in iter_nodes(tree)
        if (name := get_node_name(node)) in names.all_names
    }
    return sorted(found_names)


def find_legacy_smoke_node_names(tree: dict[str, Any]) -> list[str]:
    found_names = {
        name
        for node in iter_nodes(tree)
        if (name := get_node_name(node)) in LEGACY_SMOKE_NODE_NAMES
    }
    return sorted(found_names)


def get_node_tree_signature(tree: dict[str, Any]) -> list[tuple[str | None, str | None]]:
    return sorted(
        (get_automation_node_id(node), get_node_name(node))
        for node in iter_nodes(tree)
    )


def assert_basic_info(
    response: dict[str, Any],
    *,
    automation_node_id: str,
    name: str,
) -> None:
    basic_info = unwrap_mapping(
        unwrap_bridge_result(response),
        "basicInfo",
        "basic_info",
        "node",
    )
    missing_keys = BASIC_INFO_REQUIRED_KEYS - basic_info.keys()
    if missing_keys:
        raise SmokeBridgeError(
            "basic info missing keys: " + ", ".join(sorted(missing_keys))
        )
    if basic_info["automationNodeId"] != automation_node_id:
        raise SmokeBridgeError("basic info automationNodeId did not match")
    if basic_info["name"] != name:
        raise SmokeBridgeError("basic info name did not match")


def assert_parameter_groups(
    response: dict[str, Any],
    expected_groups: frozenset[str],
) -> None:
    group_names = get_parameter_group_names(unwrap_bridge_result(response))
    missing_groups = expected_groups - group_names
    if missing_groups:
        raise SmokeBridgeError(
            "parameter groups missing: " + ", ".join(sorted(missing_groups))
        )


def assert_bridge_capabilities(
    response: dict[str, Any],
    required_commands: frozenset[str],
) -> None:
    capabilities = unwrap_bridge_capabilities_result(response)
    commands = capabilities.get("commands")
    if not isinstance(commands, list) or not all(
        isinstance(command, str) for command in commands
    ):
        raise SmokeBridgeError(
            "Bridge capabilities response did not contain result.commands as list[str]. "
            "Rebuild and restart Effekseer.exe."
        )

    missing_commands = sorted(required_commands - set(commands))
    if missing_commands:
        raise SmokeBridgeError(
            "Bridge is missing required commands: "
            + ", ".join(missing_commands)
            + ". Rebuild and restart Effekseer.exe."
        )


def assert_workspace_status(response: dict[str, Any]) -> None:
    status = unwrap_bridge_result(response)
    enabled = status.get("enabled")
    exists = status.get("exists")
    if enabled is not True or exists is not True:
        raise SmokeBridgeError(
            "Bridge workspace is not ready: expected enabled=true and "
            f"exists=true, got enabled={enabled}, exists={exists}. "
            "Restart Effekseer.exe with --automation-workspace."
        )


def assert_runtime_export_response(
    response: dict[str, Any],
    expected_path: str,
) -> None:
    assert_no_absolute_path_strings(response, label="runtime export")
    result = unwrap_bridge_result(response)
    actual_path = result.get("path")
    if actual_path != expected_path:
        raise SmokeBridgeError(
            "runtime export path did not match: "
            f"expected {expected_path}, got {actual_path}"
        )

    byte_count = result.get("bytes")
    if isinstance(byte_count, bool) or not isinstance(byte_count, int):
        raise SmokeBridgeError("runtime export bytes was not an int")
    if byte_count <= 0:
        raise SmokeBridgeError(
            f"runtime export bytes must be greater than 0, got {byte_count}"
        )


def assert_workspace_project_response(
    response: dict[str, Any],
    expected_path: str,
    *,
    label: str,
) -> None:
    assert_no_absolute_path_strings(response, label=label)
    result = unwrap_bridge_result(response)
    actual_path = result.get("path")
    if actual_path is not None and actual_path != expected_path:
        raise SmokeBridgeError(
            f"{label} path did not match: expected {expected_path}, got {actual_path}"
        )


def ensure_smoke_texture_file() -> str:
    workspace = load_config().workspace
    texture_path = workspace / SMOKE_TEXTURE_RELATIVE_PATH
    texture_path.parent.mkdir(parents=True, exist_ok=True)
    if not texture_path.exists():
        texture_path.write_bytes(SMOKE_PNG_BYTES)

    return SMOKE_TEXTURE_RELATIVE_PATH


def find_existing_smoke_material_file() -> str | None:
    workspace = load_config().workspace
    material_path = workspace / SMOKE_MATERIAL_RELATIVE_PATH
    if material_path.exists() and material_path.is_file():
        return SMOKE_MATERIAL_RELATIVE_PATH

    return None


def find_existing_smoke_model_file() -> str | None:
    workspace = load_config().workspace
    model_path = workspace / SMOKE_MODEL_RELATIVE_PATH
    if model_path.exists() and model_path.is_file():
        return SMOKE_MODEL_RELATIVE_PATH

    return None


def assert_workspace_texture_assignment_response(
    response: dict[str, Any],
    expected_path: str,
    *,
    label: str,
) -> None:
    assert_no_absolute_path_strings(response, label=label)
    result = unwrap_bridge_result(response)
    actual_path = result.get("path")
    if actual_path != expected_path:
        raise SmokeBridgeError(
            f"{label} path did not match: expected {expected_path}, got {actual_path}"
        )


def assert_workspace_material_assignment_response(
    response: dict[str, Any],
    expected_path: str,
    *,
    label: str,
) -> None:
    assert_no_absolute_path_strings(response, label=label)
    result = unwrap_bridge_result(response)
    actual_path = result.get("path")
    if actual_path != expected_path:
        raise SmokeBridgeError(
            f"{label} path did not match: expected {expected_path}, got {actual_path}"
        )


def assert_workspace_model_assignment_response(
    response: dict[str, Any],
    expected_path: str,
    *,
    label: str,
) -> None:
    assert_no_absolute_path_strings(response, label=label)
    result = unwrap_bridge_result(response)
    actual_path = result.get("path")
    if actual_path != expected_path:
        raise SmokeBridgeError(
            f"{label} path did not match: expected {expected_path}, got {actual_path}"
        )


def assert_texture_reference_has_value(
    response: dict[str, Any],
    texture_key: str,
    *,
    expected_has_value: bool = True,
    label: str,
) -> None:
    assert_no_absolute_path_strings(response, label=label)
    renderer = unwrap_bridge_result(response)
    texture = find_texture_payload(renderer, texture_key)
    if not isinstance(texture, dict):
        raise SmokeBridgeError(f"{label} {texture_key} was not found")

    reference = texture.get("reference")
    if not isinstance(reference, dict):
        raise SmokeBridgeError(f"{label} {texture_key}.reference was not an object")
    if reference.get("hasValue") is not expected_has_value:
        raise SmokeBridgeError(
            f"{label} {texture_key}.reference.hasValue was not "
            f"{expected_has_value}"
        )


def assert_material_assignment_readback(
    response: dict[str, Any],
    *,
    expected_has_value: bool = True,
    expected_material_type: str = "File",
    label: str,
) -> None:
    assert_no_absolute_path_strings(response, label=label)
    renderer = unwrap_bridge_result(response)
    material = renderer.get("material")
    if not isinstance(material, dict):
        raise SmokeBridgeError(f"{label} material was not an object")

    material_type = extract_enum_payload(material.get("type"), "material.type")
    if material_type != expected_material_type:
        raise SmokeBridgeError(
            f"{label} material.type was not {expected_material_type}: "
            f"actual={material_type}"
        )

    material_file = material.get("materialFile")
    if not isinstance(material_file, dict):
        raise SmokeBridgeError(f"{label} material.materialFile was not an object")
    if material_file.get("hasValue") is not expected_has_value:
        raise SmokeBridgeError(
            f"{label} material.materialFile.hasValue was not {expected_has_value}"
        )


def assert_model_assignment_readback(
    response: dict[str, Any],
    *,
    label: str,
) -> None:
    assert_no_absolute_path_strings(response, label=label)
    drawing = unwrap_bridge_result(response)
    renderer_type = extract_enum_payload(drawing.get("rendererType"), "rendererType")
    if renderer_type != "Model":
        raise SmokeBridgeError(
            f"{label} rendererType was not Model: actual={renderer_type}"
        )

    model = drawing.get("model")
    if not isinstance(model, dict):
        raise SmokeBridgeError(f"{label} model was not an object")

    for key in ("model", "reference"):
        reference = model.get(key)
        if isinstance(reference, dict) and reference.get("hasValue") is True:
            return

    if model.get("hasValue") is True:
        return

    raise SmokeBridgeError(f"{label} model reference did not have a value")




def find_texture_payload(renderer: dict[str, Any], texture_key: str) -> dict[str, Any] | None:
    texture = renderer.get(texture_key)
    if isinstance(texture, dict):
        return texture

    textures = renderer.get("textures")
    if isinstance(textures, dict):
        texture = textures.get(texture_key)
        if isinstance(texture, dict):
            return texture

    if isinstance(textures, list):
        for item in textures:
            if not isinstance(item, dict):
                continue
            if texture_item_matches_key(item, texture_key):
                return item

    return None


def texture_item_matches_key(item: dict[str, Any], texture_key: str) -> bool:
    expected_names = texture_key_names(texture_key)
    for key in ("key", "name", "slot", "textureType", "type"):
        value = item.get(key)
        if isinstance(value, str) and normalize_texture_name(value) in expected_names:
            return True
        if isinstance(value, dict):
            enum_value = value.get("value")
            if (
                isinstance(enum_value, str)
                and normalize_texture_name(enum_value) in expected_names
            ):
                return True

    return False


def texture_key_names(texture_key: str) -> frozenset[str]:
    normalized = normalize_texture_name(texture_key)
    aliases = {
        "colortexture": frozenset({"colortexture", "color"}),
        "normaltexture": frozenset({"normaltexture", "normal"}),
    }
    return aliases.get(normalized, frozenset({normalized}))


def normalize_texture_name(value: str) -> str:
    return value.replace("_", "").replace("-", "").replace(" ", "").lower()


def assert_no_absolute_path_strings(value: Any, *, label: str) -> None:
    for string_value in iter_string_values(value):
        if Path(string_value).is_absolute():
            raise SmokeBridgeError(
                f"{label} response contained an absolute path: {string_value}"
            )


def iter_string_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for nested_value in value.values():
            yield from iter_string_values(nested_value)
    elif isinstance(value, list | tuple):
        for nested_value in value:
            yield from iter_string_values(nested_value)


def unwrap_bridge_capabilities_result(response: dict[str, Any]) -> dict[str, Any]:
    if response.get("ok") is False:
        error = response.get("error", "unknown bridge error")
        raise SmokeBridgeError(
            f"Bridge capabilities check failed: {error}. "
            "Rebuild and restart Effekseer.exe."
        )

    return unwrap_bridge_result(response)


def assert_required_parameter_keys(
    response: dict[str, Any],
    required_keys: frozenset[str],
    *,
    label: str,
    automation_node_id: str,
    name: str,
) -> None:
    parameters = unwrap_bridge_result(response)
    missing_keys = required_keys - parameters.keys()
    if missing_keys:
        raise SmokeBridgeError(
            f"{label} missing keys: " + ", ".join(sorted(missing_keys))
        )
    if parameters["automationNodeId"] != automation_node_id:
        raise SmokeBridgeError(f"{label} automationNodeId did not match")
    if parameters["name"] != name:
        raise SmokeBridgeError(f"{label} name did not match")


def get_is_rendered(response: dict[str, Any]) -> bool:
    parameters = unwrap_bridge_result(response)
    is_rendered = parameters.get("isRendered")
    if not isinstance(is_rendered, bool):
        raise SmokeBridgeError("isRendered was not a bool")

    return is_rendered


def assert_is_rendered(
    response: dict[str, Any],
    expected: bool,
    *,
    label: str,
) -> None:
    actual = get_is_rendered(response)
    if actual is not expected:
        raise SmokeBridgeError(
            f"{label} expected isRendered={expected}, got {actual}"
        )


def get_generation_write_values(
    response: dict[str, Any],
) -> tuple[MaxGenerationValue, LifeValues]:
    parameters = unwrap_bridge_result(response)

    return (
        get_max_generation_value_payload(
            parameters.get("maxGeneration"),
            "maxGeneration",
        ),
        get_life_value_payload(parameters.get("life"), "life"),
    )


def get_max_generation_value_payload(value: Any, label: str) -> MaxGenerationValue:
    if isinstance(value, bool):
        raise SmokeBridgeError(f"{label} was not an int payload")
    if isinstance(value, int):
        return MaxGenerationValue(value=value, infinite=None, payload=value)
    if isinstance(value, dict):
        infinite = value.get("infinite")
        return MaxGenerationValue(
            value=get_required_int(value, "value", label=label),
            infinite=infinite if isinstance(infinite, bool) else None,
            payload=value,
        )

    raise SmokeBridgeError(f"{label} was not an int payload")


def get_max_generation_write_response_value(
    response: dict[str, Any],
) -> MaxGenerationValue | None:
    result = unwrap_bridge_result(response)
    if "after" in result:
        return get_max_generation_value_payload(result["after"], "after")

    generation_parameters = result.get("generationParameters")
    if isinstance(generation_parameters, dict) and "maxGeneration" in (
        generation_parameters
    ):
        return get_max_generation_value_payload(
            generation_parameters["maxGeneration"],
            "generationParameters.maxGeneration",
        )

    if "maxGeneration" in result:
        return get_max_generation_value_payload(
            result["maxGeneration"],
            "maxGeneration",
        )

    return None


def assert_max_generation_write_response(
    response: dict[str, Any],
    expected_value: int,
    *,
    label: str,
) -> None:
    actual = get_max_generation_write_response_value(response)
    if actual is None:
        return
    if actual.value != expected_value:
        raise SmokeBridgeError(
            f"{label} maxGeneration did not match: expected value="
            f"{expected_value}, actual={actual.payload}"
        )


def get_int_value_payload(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise SmokeBridgeError(f"{label} was not an int payload")
    if isinstance(value, int):
        return value
    if isinstance(value, dict):
        return get_required_int(value, "value", label=label)

    raise SmokeBridgeError(f"{label} was not an int payload")


def get_life_value_payload(value: Any, label: str) -> LifeValues:
    if isinstance(value, dict):
        return LifeValues(
            center=get_required_int(value, "center", label=label),
            min=get_required_int(value, "min", label=label),
            max=get_required_int(value, "max", label=label),
        )

    center = get_int_value_payload(value, label)
    return LifeValues(center=center, min=center, max=center)


def get_transform_write_values(
    response: dict[str, Any],
) -> tuple[VectorValues, VectorValues, VectorValues]:
    parameters = unwrap_bridge_result(response)
    return (
        extract_vector3(parameters, ("location", "fixed", "location")),
        extract_vector3(parameters, ("rotation", "fixed", "rotation")),
        extract_vector3(parameters, ("scale", "fixed", "scale")),
    )


def get_required_int(
    mapping: dict[str, Any],
    key: str,
    *,
    label: str | None = None,
) -> int:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise SmokeBridgeError(f"{label or key} was not an int payload")

    return value


def extract_vector3(payload: dict[str, Any], path: tuple[str, ...]) -> VectorValues:
    value: Any = payload
    for key in path:
        if not isinstance(value, dict):
            raise SmokeBridgeError(f"{'.'.join(path)} was not a vector")
        value = value.get(key)

    if not isinstance(value, dict):
        raise SmokeBridgeError(f"{'.'.join(path)} was not a vector")

    label = ".".join(path)
    return VectorValues(
        x=extract_number_payload(value.get("x"), f"{label}.x"),
        y=extract_number_payload(value.get("y"), f"{label}.y"),
        z=extract_number_payload(value.get("z"), f"{label}.z"),
    )


def extract_number_payload(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise SmokeBridgeError(f"{label} was not a number")
    if isinstance(value, int | float):
        if not math.isfinite(value):
            raise SmokeBridgeError(f"{label} was not a finite number")
        return value
    if isinstance(value, dict):
        if "value" in value:
            return extract_number_payload(value["value"], label)
        if "center" in value:
            return extract_number_payload(value["center"], label)

    raise SmokeBridgeError(f"{label} was not a number")


def make_updated_basic_write_values(values: BasicWriteValues) -> BasicWriteValues:
    return BasicWriteValues(
        max_generation=MaxGenerationValue(
            value=values.max_generation.value + 1,
            infinite=values.max_generation.infinite,
            payload={
                "value": values.max_generation.value + 1,
                "infinite": values.max_generation.infinite,
            },
        ),
        life=LifeValues(
            center=values.life.center + 1,
            min=values.life.min + 1,
            max=values.life.max + 1,
        ),
        location=offset_vector(values.location, 1.0, 2.0, 3.0),
        rotation=offset_vector(values.rotation, 10.0, 20.0, 30.0),
        scale=offset_vector(values.scale, 0.5, 0.25, 0.75),
    )


def offset_vector(
    values: VectorValues,
    x_offset: float,
    y_offset: float,
    z_offset: float,
) -> VectorValues:
    return VectorValues(
        x=values.x + x_offset,
        y=values.y + y_offset,
        z=values.z + z_offset,
    )


def restore_basic_write_values(
    client: Any,
    automation_node_id: str,
    values: BasicWriteValues,
) -> None:
    client.set_node_max_generation_by_automation_id(
        automation_node_id,
        values.max_generation.value,
    )
    client.set_node_life_by_automation_id(
        automation_node_id,
        values.life.center,
        values.life.min,
        values.life.max,
    )
    client.set_node_fixed_location_by_automation_id(
        automation_node_id,
        values.location.x,
        values.location.y,
        values.location.z,
    )
    client.set_node_fixed_rotation_by_automation_id(
        automation_node_id,
        values.rotation.x,
        values.rotation.y,
        values.rotation.z,
    )
    client.set_node_fixed_scale_by_automation_id(
        automation_node_id,
        values.scale.x,
        values.scale.y,
        values.scale.z,
    )


def assert_basic_write_values(
    client: Any,
    automation_node_id: str,
    expected: BasicWriteValues,
    *,
    label: str,
) -> None:
    generation_parameters = client.get_node_generation_parameters_by_automation_id(
        automation_node_id,
    )
    actual_max_generation, actual_life = get_generation_write_values(
        generation_parameters,
    )
    if actual_max_generation.value != expected.max_generation.value:
        raise SmokeBridgeError(
            f"{label} maxGeneration did not match: expected value="
            f"{expected.max_generation.value}, actual={actual_max_generation.payload}"
        )
    if actual_life != expected.life:
        raise SmokeBridgeError(f"{label} life did not match")

    transform_parameters = client.get_node_transform_parameters_by_automation_id(
        automation_node_id,
    )
    actual_location, actual_rotation, actual_scale = get_transform_write_values(
        transform_parameters,
    )
    if actual_location != expected.location:
        raise SmokeBridgeError(f"{label} location did not match")
    if actual_rotation != expected.rotation:
        raise SmokeBridgeError(f"{label} rotation did not match")
    if actual_scale != expected.scale:
        raise SmokeBridgeError(f"{label} scale did not match")


def assert_vector_parameter(
    response: dict[str, Any],
    key: str,
    expected: VectorValues,
    *,
    label: str,
) -> None:
    parameters = unwrap_bridge_result(response)
    actual = extract_vector3(parameters, get_fixed_vector_path(key))
    if actual != expected:
        raise SmokeBridgeError(f"{label} {key} did not match")


def get_fixed_vector_path(key: str) -> tuple[str, ...]:
    if key == "location":
        return ("location", "fixed", "location")
    if key == "rotation":
        return ("rotation", "fixed", "rotation")
    if key == "scale":
        return ("scale", "fixed", "scale")

    raise SmokeBridgeError(f"unknown fixed vector parameter: {key}")


def get_motion_timing_fade_write_values(
    generation_response: dict[str, Any],
    transform_response: dict[str, Any],
    renderer_response: dict[str, Any],
) -> MotionTimingFadeWriteValues:
    generation_parameters = unwrap_bridge_result(generation_response)
    transform_parameters = unwrap_bridge_result(transform_response)
    renderer_parameters = unwrap_bridge_result(renderer_response)
    generation = generation_parameters.get("generation")
    fade = renderer_parameters.get("fade")
    if not isinstance(generation, dict):
        raise SmokeBridgeError("generation parameters generation was not an object")
    if not isinstance(fade, dict):
        raise SmokeBridgeError("renderer parameters fade was not an object")

    return MotionTimingFadeWriteValues(
        generation_time=extract_random_float_payload(
            generation.get("generationTime"),
            "generation.generationTime",
        ),
        location_type=extract_enum_payload(
            get_nested_mapping(transform_parameters, ("location",)).get("type"),
            "location.type",
        ),
        location_pva=extract_vector3_random(
            transform_parameters,
            ("location", "pva", "location"),
        ),
        velocity_pva=extract_vector3_random(
            transform_parameters,
            ("location", "pva", "velocity"),
        ),
        acceleration_pva=extract_vector3_random(
            transform_parameters,
            ("location", "pva", "acceleration"),
        ),
        scale_type=extract_enum_payload(
            get_nested_mapping(transform_parameters, ("scale",)).get("type"),
            "scale.type",
        ),
        scale_pva=extract_vector3_random(
            transform_parameters,
            ("scale", "pva", "scale"),
        ),
        scale_velocity_pva=extract_vector3_random(
            transform_parameters,
            ("scale", "pva", "velocity"),
        ),
        scale_acceleration_pva=extract_vector3_random(
            transform_parameters,
            ("scale", "pva", "acceleration"),
        ),
        fade_in_type=extract_enum_payload(
            fade.get("fadeInType"),
            "fade.fadeInType",
        ),
        fade_in_frame=extract_number_payload(
            get_nested_mapping(fade, ("fadeIn",)).get("frame"),
            "fade.fadeIn.frame",
        ),
        fade_out_type=extract_enum_payload(
            fade.get("fadeOutType"),
            "fade.fadeOutType",
        ),
        fade_out_frame=extract_number_payload(
            get_nested_mapping(fade, ("fadeOut",)).get("frame"),
            "fade.fadeOut.frame",
        ),
    )


def get_nested_mapping(payload: dict[str, Any], path: tuple[str, ...]) -> dict[str, Any]:
    value: Any = payload
    for key in path:
        if not isinstance(value, dict):
            raise SmokeBridgeError(f"{'.'.join(path)} was not an object")
        value = value.get(key)

    if not isinstance(value, dict):
        raise SmokeBridgeError(f"{'.'.join(path)} was not an object")

    return value


def extract_vector3_random(
    payload: dict[str, Any],
    path: tuple[str, ...],
) -> VectorRandomValues:
    value = get_nested_mapping(payload, path)
    label = ".".join(path)
    return VectorRandomValues(
        x=extract_random_float_payload(value.get("x"), f"{label}.x"),
        y=extract_random_float_payload(value.get("y"), f"{label}.y"),
        z=extract_random_float_payload(value.get("z"), f"{label}.z"),
    )


def extract_random_float_payload(value: Any, label: str) -> RandomFloatValues:
    if not isinstance(value, dict):
        raise SmokeBridgeError(f"{label} was not a random number payload")

    return RandomFloatValues(
        center=extract_number_payload(value.get("center"), f"{label}.center"),
        min=extract_number_payload(value.get("min"), f"{label}.min"),
        max=extract_number_payload(value.get("max"), f"{label}.max"),
    )


def make_updated_motion_timing_fade_values(
    values: MotionTimingFadeWriteValues,
) -> MotionTimingFadeWriteValues:
    return MotionTimingFadeWriteValues(
        generation_time=offset_random_float(values.generation_time, 0.25),
        location_type="PVA",
        location_pva=make_vector_random(0.0, 0.0, 0.0),
        velocity_pva=make_vector_random(0.0, 12.0, 0.0),
        acceleration_pva=make_vector_random(0.0, -0.5, 0.0),
        scale_type="PVA",
        scale_pva=make_vector_random(1.0, 1.0, 1.0),
        scale_velocity_pva=make_vector_random(-0.02, -0.02, -0.02),
        scale_acceleration_pva=make_vector_random(0.0, 0.0, 0.0),
        fade_in_type="Use",
        fade_in_frame=values.fade_in_frame + 1.0,
        fade_out_type="WithinLifetime",
        fade_out_frame=values.fade_out_frame + 1.0,
    )


def offset_random_float(values: RandomFloatValues, offset: float) -> RandomFloatValues:
    return RandomFloatValues(
        center=values.center + offset,
        min=values.min + offset,
        max=values.max + offset,
    )


def make_vector_random(x: float, y: float, z: float) -> VectorRandomValues:
    return VectorRandomValues(
        x=RandomFloatValues(center=x, min=x, max=x),
        y=RandomFloatValues(center=y, min=y, max=y),
        z=RandomFloatValues(center=z, min=z, max=z),
    )


def restore_motion_timing_fade_write_values(
    client: Any,
    automation_node_id: str,
    values: MotionTimingFadeWriteValues,
) -> None:
    client.set_node_generation_time_by_automation_id(
        automation_node_id,
        values.generation_time.center,
        values.generation_time.min,
        values.generation_time.max,
    )
    client.set_node_location_type_by_automation_id(
        automation_node_id,
        values.location_type,
    )
    client.set_node_location_pva_by_automation_id(
        automation_node_id,
        values.location_pva.as_dict(),
        values.velocity_pva.as_dict(),
        values.acceleration_pva.as_dict(),
    )
    client.set_node_scale_type_by_automation_id(
        automation_node_id,
        values.scale_type,
    )
    client.set_node_scale_pva_by_automation_id(
        automation_node_id,
        values.scale_pva.as_dict(),
        values.scale_velocity_pva.as_dict(),
        values.scale_acceleration_pva.as_dict(),
    )
    client.set_node_fade_in_out_by_automation_id(
        automation_node_id,
        values.fade_in_type,
        values.fade_in_frame,
        values.fade_out_type,
        values.fade_out_frame,
    )


def assert_motion_timing_fade_write_values(
    client: Any,
    automation_node_id: str,
    expected: MotionTimingFadeWriteValues,
    *,
    label: str,
) -> None:
    actual = get_motion_timing_fade_write_values(
        client.get_node_generation_parameters_by_automation_id(automation_node_id),
        client.get_node_transform_parameters_by_automation_id(automation_node_id),
        client.get_node_renderer_parameters_by_automation_id(automation_node_id),
    )
    if actual != expected:
        raise SmokeBridgeError(
            f"{label} did not match: expected={expected}, actual={actual}"
        )


def get_drawing_renderer_write_values(
    drawing_response: dict[str, Any],
    renderer_response: dict[str, Any],
) -> DrawingRendererWriteValues:
    drawing = unwrap_bridge_result(drawing_response)
    renderer = unwrap_bridge_result(renderer_response)
    sprite = drawing.get("sprite")
    blend = renderer.get("blend")
    if not isinstance(sprite, dict):
        raise SmokeBridgeError("drawing sprite was not an object")
    if not isinstance(blend, dict):
        raise SmokeBridgeError("renderer blend was not an object")

    return DrawingRendererWriteValues(
        renderer_type=extract_enum_payload(
            drawing.get("rendererType"),
            "rendererType",
        ),
        color_all=extract_rgba_payload(drawing.get("colorAll"), "colorAll"),
        corner_colors=extract_sprite_corner_colors(sprite),
        alpha_blend=extract_enum_payload(
            blend.get("alphaBlend"),
            "blend.alphaBlend",
        ),
        z_write=get_required_bool(blend, "zWrite"),
        z_test=get_required_bool(blend, "zTest"),
    )


def extract_sprite_corner_colors(sprite: dict[str, Any]) -> SpriteCornerColors:
    raw_corner_colors = sprite.get(
        "fixedColors",
        sprite.get("fixed_colors", sprite.get("cornerColors", sprite.get("corner_colors"))),
    )
    if not isinstance(raw_corner_colors, dict):
        raise SmokeBridgeError("sprite fixedColors was not an object")

    return SpriteCornerColors(
        lower_left=extract_rgba_payload(
            raw_corner_colors.get("lowerLeft", raw_corner_colors.get("lower_left")),
            "fixedColors.lowerLeft",
        ),
        lower_right=extract_rgba_payload(
            raw_corner_colors.get("lowerRight", raw_corner_colors.get("lower_right")),
            "fixedColors.lowerRight",
        ),
        upper_left=extract_rgba_payload(
            raw_corner_colors.get("upperLeft", raw_corner_colors.get("upper_left")),
            "fixedColors.upperLeft",
        ),
        upper_right=extract_rgba_payload(
            raw_corner_colors.get("upperRight", raw_corner_colors.get("upper_right")),
            "fixedColors.upperRight",
        ),
    )


def extract_rgba_payload(value: Any, label: str) -> RgbaValues:
    if isinstance(value, dict):
        if all(key in value for key in ("r", "g", "b", "a")):
            return RgbaValues(
                r=get_rgba_channel(value, "r", label),
                g=get_rgba_channel(value, "g", label),
                b=get_rgba_channel(value, "b", label),
                a=get_rgba_channel(value, "a", label),
            )
        if "fixed" in value:
            return extract_rgba_payload(value["fixed"], f"{label}.fixed")
        if "rgba" in value:
            return extract_rgba_payload(value["rgba"], label)
        if "color" in value:
            return extract_rgba_payload(value["color"], label)
        if any(
            key in value
            for key in ("type", "random", "easing", "fcurve", "gradient")
        ):
            raise SmokeBridgeError(f"{label}.fixed was not an rgba payload")
    if isinstance(value, list) and len(value) == 4:
        return RgbaValues(
            r=get_rgba_channel({"r": value[0]}, "r", label),
            g=get_rgba_channel({"g": value[1]}, "g", label),
            b=get_rgba_channel({"b": value[2]}, "b", label),
            a=get_rgba_channel({"a": value[3]}, "a", label),
        )

    raise SmokeBridgeError(f"{label} was not an rgba payload")


def get_rgba_channel(mapping: dict[str, Any], key: str, label: str) -> int:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise SmokeBridgeError(f"{label}.{key} was not an int")
    if not 0 <= value <= 255:
        raise SmokeBridgeError(f"{label}.{key} was not between 0 and 255")

    return value


def get_required_string(mapping: dict[str, Any], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str):
        raise SmokeBridgeError(f"{key} was not a string")

    return value


def extract_enum_payload(value: Any, label: str) -> str:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, dict):
        raw_value = value.get("value")
        if isinstance(raw_value, str) and raw_value:
            return raw_value
        raise SmokeBridgeError(f"{label}.value was not a non-empty string")

    raise SmokeBridgeError(f"{label} was not an enum payload")


def get_required_bool(mapping: dict[str, Any], key: str) -> bool:
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise SmokeBridgeError(f"{key} was not a bool")

    return value


def make_updated_drawing_renderer_values(
    values: DrawingRendererWriteValues,
) -> DrawingRendererWriteValues:
    return DrawingRendererWriteValues(
        renderer_type=next_distinct_value(
            values.renderer_type,
            ("Sprite", "Ribbon"),
        ),
        color_all=RgbaValues(r=32, g=96, b=192, a=224),
        corner_colors=SpriteCornerColors(
            lower_left=RgbaValues(r=255, g=0, b=0, a=255),
            lower_right=RgbaValues(r=0, g=255, b=0, a=255),
            upper_left=RgbaValues(r=0, g=0, b=255, a=255),
            upper_right=RgbaValues(r=255, g=255, b=0, a=255),
        ),
        alpha_blend=next_distinct_value(values.alpha_blend, ("Blend", "Add")),
        z_write=not values.z_write,
        z_test=not values.z_test,
    )


def next_distinct_value(current: str, candidates: tuple[str, str]) -> str:
    return candidates[1] if current == candidates[0] else candidates[0]


def restore_drawing_renderer_write_values(
    client: Any,
    automation_node_id: str,
    values: DrawingRendererWriteValues,
) -> None:
    client.set_node_renderer_type_by_automation_id(
        automation_node_id,
        values.renderer_type,
    )
    client.set_node_color_all_fixed_rgba_by_automation_id(
        automation_node_id,
        values.color_all.r,
        values.color_all.g,
        values.color_all.b,
        values.color_all.a,
    )
    client.set_node_sprite_corner_colors_fixed_rgba_by_automation_id(
        automation_node_id,
        values.corner_colors.lower_left.as_dict(),
        values.corner_colors.lower_right.as_dict(),
        values.corner_colors.upper_left.as_dict(),
        values.corner_colors.upper_right.as_dict(),
    )
    client.set_node_alpha_blend_by_automation_id(
        automation_node_id,
        values.alpha_blend,
    )
    client.set_node_z_write_by_automation_id(automation_node_id, values.z_write)
    client.set_node_z_test_by_automation_id(automation_node_id, values.z_test)


def assert_drawing_renderer_write_values(
    client: Any,
    automation_node_id: str,
    expected: DrawingRendererWriteValues,
    *,
    label: str,
) -> None:
    actual = get_drawing_renderer_write_values(
        client.get_node_drawing_parameters_by_automation_id(automation_node_id),
        client.get_node_renderer_parameters_by_automation_id(automation_node_id),
    )
    if actual != expected:
        raise SmokeBridgeError(
            f"{label} did not match: expected={expected}, actual={actual}"
        )


def unwrap_mapping(
    response: dict[str, Any],
    *keys: str,
) -> dict[str, Any]:
    for key in keys:
        value = response.get(key)
        if isinstance(value, dict):
            return value

    return response


def unwrap_bridge_result(response: dict[str, Any]) -> dict[str, Any]:
    ok = response.get("ok")
    if ok is False:
        error = response.get("error", "unknown bridge error")
        raise SmokeBridgeError(f"bridge command failed: {error}")

    result = response.get("result")
    if isinstance(result, dict):
        return result

    return response


def get_parameter_group_names(response: dict[str, Any]) -> set[str]:
    for key in ("parameterGroups", "parameter_groups", "groups"):
        value = response.get(key)
        if isinstance(value, list):
            return {
                group_name
                for item in value
                if (group_name := get_parameter_group_name(item)) is not None
            }
        if isinstance(value, dict):
            return set(value)

    return {
        group_name
        for item in response.values()
        if isinstance(item, dict)
        if (group_name := get_parameter_group_name(item)) is not None
    }


def get_parameter_group_name(group: Any) -> str | None:
    if isinstance(group, str) and group:
        return group
    if not isinstance(group, dict):
        return None

    for key in ("key", "id", "name", "groupName", "group_name"):
        value = group.get(key)
        if isinstance(value, str) and value:
            return value

    return None


def assert_no_run_smoke_nodes(tree: dict[str, Any], names: SmokeNames) -> None:
    remaining_names = find_run_smoke_node_names(tree, names)
    if remaining_names:
        raise SmokeBridgeError(
            "smoke nodes remained after cleanup: " + ", ".join(remaining_names)
        )


def warn_about_legacy_smoke_nodes(
    tree: dict[str, Any],
    *,
    stderr: TextIO = sys.stderr,
) -> None:
    legacy_names = find_legacy_smoke_node_names(tree)
    if legacy_names:
        print(
            "WARNING: legacy smoke nodes remain: " + ", ".join(legacy_names),
            file=stderr,
        )


def cleanup_legacy_smoke_nodes(
    client: Any,
    *,
    stderr: TextIO = sys.stderr,
) -> None:
    while True:
        tree = client.get_node_tree()
        root_id = get_automation_node_id(find_root_node(tree))
        legacy_node_id: str | None = None
        legacy_node_name: str | None = None

        for node in iter_nodes(tree):
            node_id = get_automation_node_id(node)
            node_name = get_node_name(node)
            if node_id is None or node_id == root_id:
                continue
            if node_name in LEGACY_SMOKE_NODE_NAMES:
                legacy_node_id = node_id
                legacy_node_name = node_name
                break

        if legacy_node_id is None:
            return

        print(
            f"WARNING: removing legacy smoke node {legacy_node_name} "
            f"({legacy_node_id})",
            file=stderr,
        )
        client.remove_node_by_automation_id(legacy_node_id)


def extract_automation_node_id(
    response: dict[str, Any],
    nested_key: str,
) -> str | None:
    automation_node_id = get_automation_node_id(response)
    if automation_node_id is not None:
        return automation_node_id

    nested_value = response.get(nested_key)
    if isinstance(nested_value, dict):
        return get_automation_node_id(nested_value)

    return None


def warn_about_duplicate_node_ids(
    tree: dict[str, Any],
    *,
    stderr: TextIO = sys.stderr,
) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()

    for node in iter_nodes(tree):
        node_id = get_automation_node_id(node)
        if node_id is None:
            continue
        if node_id in seen:
            duplicates.add(node_id)
        seen.add(node_id)

    for node_id in sorted(duplicates):
        print(
            f"WARNING: duplicate automationNodeId detected: {node_id}",
            file=stderr,
        )

    return sorted(duplicates)


def get_automation_node_id(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None

    for key in AUTOMATION_NODE_ID_KEYS:
        raw_value = value.get(key)
        if isinstance(raw_value, str) and raw_value:
            return raw_value

    return None


def get_node_id(value: Any) -> int | None:
    if not isinstance(value, dict):
        return None

    for key in NODE_ID_KEYS:
        raw_value = value.get(key)
        if isinstance(raw_value, bool):
            continue
        if isinstance(raw_value, int):
            return raw_value
        if isinstance(raw_value, str) and raw_value.isdecimal():
            return int(raw_value)

    return None


def get_parent_automation_node_id(value: dict[str, Any]) -> str | None:
    for key in PARENT_AUTOMATION_ID_KEYS:
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


def main() -> int:
    try:
        run_smoke_test(EffekseerBridgeClient())
    except (EffekseerBridgeError, SmokeBridgeError) as exc:
        print(f"Smoke test failed: {exc}", file=sys.stderr)
        return 1

    return 0


def _print_step(stdout: TextIO, message: str) -> None:
    print(f"[smoke] {message}", file=stdout)

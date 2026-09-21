import os

from mcp.server.fastmcp import FastMCP

from effekseer_mcp.assets import (
    inspect_asset as inspect_workspace_asset,
    list_asset_kinds as list_workspace_asset_kinds,
    list_assets as list_workspace_assets,
)
from effekseer_mcp.bridge_client import EffekseerBridgeClient
from effekseer_mcp.config import load_config
from effekseer_mcp.recipes import (
    create_basic_sprite_burst_effect,
    create_elemental_burst_effect,
    create_effect_from_spec,
    create_firework_burst_effect,
    create_heal_sparkle_effect,
    create_projectile_trail_effect,
    create_slash_effect,
    describe_effect_recipe,
    list_effect_recipes,
)
from effekseer_mcp.sample_analyzer import (
    analyze_sample_effects,
    get_sample_analysis_summary,
)
from effekseer_mcp.sample_library import (
    create_effect_from_sample_template,
    describe_sample_template,
    import_sample_effects,
    list_sample_templates,
)

mcp = FastMCP("effekseer-mcp")


@mcp.tool()
def ping() -> str:
    """Check whether the Effekseer MCP server is running."""
    return "effekseer-mcp is ready"


@mcp.tool()
def get_effekseer_config() -> dict:
    """Return the configured Effekseer executable path and workspace."""
    return load_config().as_dict()


@mcp.tool()
def list_workspace_files() -> list[str]:
    """List files under the MCP workspace."""
    workspace = load_config().workspace
    return [
        str(asset["relative_path"])
        for asset in list_workspace_assets(workspace=workspace)
    ]


@mcp.tool()
def list_assets(kind: str | None = None) -> list[dict]:
    """List read-only asset catalog entries under the MCP workspace."""
    workspace = load_config().workspace
    return list_workspace_assets(kind=kind, workspace=workspace)


@mcp.tool()
def inspect_asset(path: str) -> dict:
    """Inspect one workspace-relative asset without reading file contents."""
    workspace = load_config().workspace
    return inspect_workspace_asset(path, workspace=workspace)


@mcp.tool()
def list_asset_kinds() -> list[str]:
    """List supported read-only asset catalog kinds."""
    return list_workspace_asset_kinds()


@mcp.tool()
def effekseer_bridge_ping() -> dict:
    """Ping the local Effekseer Automation Bridge."""
    return EffekseerBridgeClient().ping()


@mcp.tool()
def effekseer_get_status() -> dict:
    """Get status from the local Effekseer Automation Bridge."""
    return EffekseerBridgeClient().get_status()


@mcp.tool()
def effekseer_get_bridge_capabilities() -> dict:
    """Get supported commands from the local Effekseer Automation Bridge."""
    return EffekseerBridgeClient().get_bridge_capabilities()


@mcp.tool()
def effekseer_get_workspace_status() -> dict:
    """Get the local Automation Bridge workspace status."""
    return EffekseerBridgeClient().get_workspace_status()


@mcp.tool()
def effekseer_save_project_to_workspace(path: str) -> dict:
    """Save the current project to a workspace-relative .efkefc path."""
    return EffekseerBridgeClient().save_project_to_workspace(path)


@mcp.tool()
def effekseer_open_project_from_workspace(path: str) -> dict:
    """Open a project from a workspace-relative .efkefc path."""
    return EffekseerBridgeClient().open_project_from_workspace(path)


@mcp.tool()
def effekseer_export_runtime_effect_to_workspace(path: str) -> dict:
    """Export the current project to a workspace-relative .efk path."""
    return EffekseerBridgeClient().export_runtime_effect_to_workspace(path)


@mcp.tool()
def effekseer_create_basic_sprite_burst_effect(
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
) -> dict:
    """Create a basic sprite burst effect, save the project, and export runtime .efk."""
    return create_basic_sprite_burst_effect(
        name=name,
        output_project_path=output_project_path,
        output_effect_path=output_effect_path,
        color=color,
        max_generation=max_generation,
        life=life,
        location=location,
        rotation=rotation,
        scale=scale,
        alpha_blend=alpha_blend,
        texture_path=texture_path,
    )


@mcp.tool()
def effekseer_create_firework_burst_effect(
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
    sample_tuning: str | dict | None = "auto",
) -> dict:
    """Create a firework burst effect, save the project, and export runtime .efk."""
    return create_firework_burst_effect(
        name=name,
        output_project_path=output_project_path,
        output_effect_path=output_effect_path,
        primary_color=primary_color,
        secondary_color=secondary_color,
        spark_count=spark_count,
        secondary_spark_count=secondary_spark_count,
        burst_life=burst_life,
        secondary_life=secondary_life,
        burst_radius=burst_radius,
        gravity=gravity,
        scale=scale,
        texture_path=texture_path,
        texture_set=texture_set,
        textures=textures,
        visual_profile=visual_profile,
        sample_tuning=sample_tuning,
    )


@mcp.tool()
def effekseer_create_slash_effect(
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
    sample_tuning: str | dict | None = "auto",
) -> dict:
    """Create a slash effect, save the project, and export runtime .efk."""
    return create_slash_effect(
        name=name,
        output_project_path=output_project_path,
        output_effect_path=output_effect_path,
        primary_color=primary_color,
        secondary_color=secondary_color,
        intensity=intensity,
        scale=scale,
        duration=duration,
        element=element,
        texture_path=texture_path,
        texture_set=texture_set,
        textures=textures,
        visual_profile=visual_profile,
        sample_tuning=sample_tuning,
    )


@mcp.tool()
def effekseer_create_heal_sparkle_effect(
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
    sample_tuning: str | dict | None = "auto",
) -> dict:
    """Create a heal sparkle effect, save the project, and export runtime .efk."""
    return create_heal_sparkle_effect(
        name=name,
        output_project_path=output_project_path,
        output_effect_path=output_effect_path,
        primary_color=primary_color,
        secondary_color=secondary_color,
        intensity=intensity,
        scale=scale,
        duration=duration,
        texture_path=texture_path,
        texture_set=texture_set,
        textures=textures,
        visual_profile=visual_profile,
        sample_tuning=sample_tuning,
    )


@mcp.tool()
def effekseer_create_elemental_burst_effect(
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
    sample_tuning: str | dict | None = "auto",
) -> dict:
    """Create an elemental burst effect, save the project, and export runtime .efk."""
    return create_elemental_burst_effect(
        name=name,
        output_project_path=output_project_path,
        output_effect_path=output_effect_path,
        primary_color=primary_color,
        secondary_color=secondary_color,
        intensity=intensity,
        scale=scale,
        duration=duration,
        element=element,
        texture_path=texture_path,
        texture_set=texture_set,
        textures=textures,
        visual_profile=visual_profile,
        sample_tuning=sample_tuning,
    )


@mcp.tool()
def effekseer_create_projectile_trail_effect(
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
    sample_tuning: str | dict | None = "auto",
) -> dict:
    """Create a projectile trail effect, save the project, and export runtime .efk."""
    return create_projectile_trail_effect(
        name=name,
        output_project_path=output_project_path,
        output_effect_path=output_effect_path,
        primary_color=primary_color,
        secondary_color=secondary_color,
        intensity=intensity,
        scale=scale,
        duration=duration,
        element=element,
        texture_path=texture_path,
        texture_set=texture_set,
        textures=textures,
        visual_profile=visual_profile,
        sample_tuning=sample_tuning,
    )


@mcp.tool()
def effekseer_list_effect_recipes() -> list[dict]:
    """List high-level effect recipes available for EffectSpec routing."""
    return list_effect_recipes()


@mcp.tool()
def effekseer_describe_effect_recipe(kind: str) -> dict:
    """Describe a high-level effect recipe by id or EffectSpec kind."""
    return describe_effect_recipe(kind)


@mcp.tool()
def effekseer_create_effect_from_spec(spec: dict) -> dict:
    """Create an effect by routing an EffectSpec v0 payload to a recipe."""
    return create_effect_from_spec(spec)


@mcp.tool()
def effekseer_import_sample_effects(repo_root: str | None = None) -> dict:
    """Import repo-local SampleEffects into workspace/samples/sample_effects."""
    return import_sample_effects(repo_root=repo_root)


@mcp.tool()
def effekseer_list_sample_templates() -> list[dict]:
    """List imported SampleEffects-derived templates."""
    return list_sample_templates()


@mcp.tool()
def effekseer_describe_sample_template(sample_id: str) -> dict:
    """Describe one imported SampleEffects-derived template."""
    return describe_sample_template(sample_id)


@mcp.tool()
def effekseer_create_effect_from_sample_template(
    sample_id: str,
    output_project_path: str,
    output_effect_path: str,
) -> dict:
    """Create/export an effect from an imported SampleEffects template."""
    return create_effect_from_sample_template(
        sample_id=sample_id,
        output_project_path=output_project_path,
        output_effect_path=output_effect_path,
    )


@mcp.tool()
def effekseer_analyze_sample_effects(sample_id: str | None = None) -> dict:
    """Analyze imported SampleEffects XML into workspace output summaries."""
    return analyze_sample_effects(sample_id=sample_id)


@mcp.tool()
def effekseer_get_sample_analysis_summary() -> dict:
    """Return the latest generated SampleEffects analysis summary."""
    return get_sample_analysis_summary()


@mcp.tool()
def effekseer_get_node_tree() -> dict:
    """Get the current node tree from the local Effekseer Automation Bridge."""
    return EffekseerBridgeClient().get_node_tree()


@mcp.tool()
def effekseer_add_node_to_selected() -> dict:
    """Ask the local Effekseer Automation Bridge to add a node."""
    return EffekseerBridgeClient().add_node_to_selected()


@mcp.tool()
def effekseer_select_node_by_automation_id(automation_node_id: str) -> dict:
    """Select a node by stable automation node id through the bridge."""
    return EffekseerBridgeClient().select_node_by_automation_id(automation_node_id)


@mcp.tool()
def effekseer_add_node_to_parent_by_automation_id(
    parent_automation_node_id: str,
    name: str | None = None,
) -> dict:
    """Add a node under a parent automation node id through the bridge."""
    return EffekseerBridgeClient().add_node_to_parent_by_automation_id(
        parent_automation_node_id,
        name,
    )


@mcp.tool()
def effekseer_rename_node_by_automation_id(
    automation_node_id: str,
    name: str,
) -> dict:
    """Rename a node by stable automation node id through the bridge."""
    return EffekseerBridgeClient().rename_node_by_automation_id(
        automation_node_id,
        name,
    )


@mcp.tool()
def effekseer_remove_node_by_automation_id(automation_node_id: str) -> dict:
    """Remove a node by stable automation node id through the bridge."""
    return EffekseerBridgeClient().remove_node_by_automation_id(automation_node_id)


@mcp.tool()
def effekseer_duplicate_node_by_automation_id(
    automation_node_id: str,
    name: str | None = None,
) -> dict:
    """Duplicate a node by stable automation node id through the bridge."""
    return EffekseerBridgeClient().duplicate_node_by_automation_id(
        automation_node_id,
        name,
    )


@mcp.tool()
def effekseer_insert_parent_node_by_automation_id(
    automation_node_id: str,
    name: str | None = None,
) -> dict:
    """Insert a parent node above a stable automation node id through the bridge."""
    return EffekseerBridgeClient().insert_parent_node_by_automation_id(
        automation_node_id,
        name,
    )


@mcp.tool()
def effekseer_undo() -> dict:
    """Undo the last bridge-supported editor operation."""
    return EffekseerBridgeClient().undo()


@mcp.tool()
def effekseer_redo() -> dict:
    """Redo the last bridge-supported editor operation."""
    return EffekseerBridgeClient().redo()


@mcp.tool()
def effekseer_play_viewer() -> dict:
    """Play the Effekseer viewer through the local Automation Bridge."""
    return EffekseerBridgeClient().play_viewer()


@mcp.tool()
def effekseer_stop_viewer() -> dict:
    """Stop the Effekseer viewer through the local Automation Bridge."""
    return EffekseerBridgeClient().stop_viewer()


@mcp.tool()
def effekseer_step_viewer() -> dict:
    """Step the Effekseer viewer forward through the local Automation Bridge."""
    return EffekseerBridgeClient().step_viewer()


@mcp.tool()
def effekseer_back_step_viewer() -> dict:
    """Step the Effekseer viewer backward through the local Automation Bridge."""
    return EffekseerBridgeClient().back_step_viewer()


@mcp.tool()
def effekseer_get_node_basic_info_by_automation_id(
    automation_node_id: str,
) -> dict:
    """Read basic node info by stable automation node id through the bridge."""
    return EffekseerBridgeClient().get_node_basic_info_by_automation_id(
        automation_node_id,
    )


@mcp.tool()
def effekseer_get_node_parameter_groups_by_automation_id(
    automation_node_id: str,
) -> dict:
    """Read node parameter group metadata by stable automation node id."""
    return EffekseerBridgeClient().get_node_parameter_groups_by_automation_id(
        automation_node_id,
    )


@mcp.tool()
def effekseer_get_node_base_parameters_by_automation_id(
    automation_node_id: str,
) -> dict:
    """Read base parameter values by stable automation node id."""
    return EffekseerBridgeClient().get_node_base_parameters_by_automation_id(
        automation_node_id,
    )


@mcp.tool()
def effekseer_get_node_generation_parameters_by_automation_id(
    automation_node_id: str,
) -> dict:
    """Read generation parameter values by stable automation node id."""
    return EffekseerBridgeClient().get_node_generation_parameters_by_automation_id(
        automation_node_id,
    )


@mcp.tool()
def effekseer_get_node_transform_parameters_by_automation_id(
    automation_node_id: str,
) -> dict:
    """Read transform parameter values by stable automation node id."""
    return EffekseerBridgeClient().get_node_transform_parameters_by_automation_id(
        automation_node_id,
    )


@mcp.tool()
def effekseer_get_node_drawing_parameters_by_automation_id(
    automation_node_id: str,
) -> dict:
    """Read drawing parameter values by stable automation node id."""
    return EffekseerBridgeClient().get_node_drawing_parameters_by_automation_id(
        automation_node_id,
    )


@mcp.tool()
def effekseer_get_node_renderer_parameters_by_automation_id(
    automation_node_id: str,
) -> dict:
    """Read renderer common parameter values by stable automation node id."""
    return EffekseerBridgeClient().get_node_renderer_parameters_by_automation_id(
        automation_node_id,
    )


@mcp.tool()
def effekseer_set_node_is_rendered_by_automation_id(
    automation_node_id: str,
    is_rendered: bool,
) -> dict:
    """Set the limited isRendered parameter by stable automation node id."""
    return EffekseerBridgeClient().set_node_is_rendered_by_automation_id(
        automation_node_id,
        is_rendered,
    )


@mcp.tool()
def effekseer_set_node_max_generation_by_automation_id(
    automation_node_id: str,
    max_generation: int,
) -> dict:
    """Set the limited maxGeneration parameter by stable automation node id."""
    return EffekseerBridgeClient().set_node_max_generation_by_automation_id(
        automation_node_id,
        max_generation,
    )


@mcp.tool()
def effekseer_set_node_life_by_automation_id(
    automation_node_id: str,
    center: int,
    min: int,
    max: int,
) -> dict:
    """Set the limited life parameter by stable automation node id."""
    return EffekseerBridgeClient().set_node_life_by_automation_id(
        automation_node_id,
        center,
        min,
        max,
    )


@mcp.tool()
def effekseer_set_node_fixed_location_by_automation_id(
    automation_node_id: str,
    x: float,
    y: float,
    z: float,
) -> dict:
    """Set the limited fixed location parameter by stable automation node id."""
    return EffekseerBridgeClient().set_node_fixed_location_by_automation_id(
        automation_node_id,
        x,
        y,
        z,
    )


@mcp.tool()
def effekseer_set_node_fixed_rotation_by_automation_id(
    automation_node_id: str,
    x: float,
    y: float,
    z: float,
) -> dict:
    """Set the limited fixed rotation parameter by stable automation node id."""
    return EffekseerBridgeClient().set_node_fixed_rotation_by_automation_id(
        automation_node_id,
        x,
        y,
        z,
    )


@mcp.tool()
def effekseer_set_node_fixed_scale_by_automation_id(
    automation_node_id: str,
    x: float,
    y: float,
    z: float,
) -> dict:
    """Set the limited fixed scale parameter by stable automation node id."""
    return EffekseerBridgeClient().set_node_fixed_scale_by_automation_id(
        automation_node_id,
        x,
        y,
        z,
    )


@mcp.tool()
def effekseer_set_node_generation_time_by_automation_id(
    automation_node_id: str,
    center: float,
    min: float,
    max: float,
) -> dict:
    """Set the generation time random payload by automation node id."""
    return EffekseerBridgeClient().set_node_generation_time_by_automation_id(
        automation_node_id,
        center,
        min,
        max,
    )


@mcp.tool()
def effekseer_set_node_location_type_by_automation_id(
    automation_node_id: str,
    location_type: str,
) -> dict:
    """Set the location type by automation node id."""
    return EffekseerBridgeClient().set_node_location_type_by_automation_id(
        automation_node_id,
        location_type,
    )


@mcp.tool()
def effekseer_set_node_location_pva_by_automation_id(
    automation_node_id: str,
    location: dict[str, dict[str, float]],
    velocity: dict[str, dict[str, float]],
    acceleration: dict[str, dict[str, float]],
) -> dict:
    """Set location PVA random payloads by automation node id."""
    return EffekseerBridgeClient().set_node_location_pva_by_automation_id(
        automation_node_id,
        location,
        velocity,
        acceleration,
    )


@mcp.tool()
def effekseer_set_node_scale_type_by_automation_id(
    automation_node_id: str,
    scale_type: str,
) -> dict:
    """Set the scale type by automation node id."""
    return EffekseerBridgeClient().set_node_scale_type_by_automation_id(
        automation_node_id,
        scale_type,
    )


@mcp.tool()
def effekseer_set_node_scale_pva_by_automation_id(
    automation_node_id: str,
    scale: dict[str, dict[str, float]],
    velocity: dict[str, dict[str, float]],
    acceleration: dict[str, dict[str, float]],
) -> dict:
    """Set scale PVA random payloads by automation node id."""
    return EffekseerBridgeClient().set_node_scale_pva_by_automation_id(
        automation_node_id,
        scale,
        velocity,
        acceleration,
    )


@mcp.tool()
def effekseer_set_node_fade_in_out_by_automation_id(
    automation_node_id: str,
    fade_in_type: str,
    fade_in_frame: float,
    fade_out_type: str,
    fade_out_frame: float,
) -> dict:
    """Set renderer fade-in/fade-out type and frame values by automation node id."""
    return EffekseerBridgeClient().set_node_fade_in_out_by_automation_id(
        automation_node_id,
        fade_in_type,
        fade_in_frame,
        fade_out_type,
        fade_out_frame,
    )


@mcp.tool()
def effekseer_set_node_color_all_fixed_rgba_by_automation_id(
    automation_node_id: str,
    r: int,
    g: int,
    b: int,
    a: int,
) -> dict:
    """Set the file-free fixed all-color RGBA value by automation node id."""
    return EffekseerBridgeClient().set_node_color_all_fixed_rgba_by_automation_id(
        automation_node_id,
        r,
        g,
        b,
        a,
    )


@mcp.tool()
def effekseer_set_node_sprite_corner_colors_fixed_rgba_by_automation_id(
    automation_node_id: str,
    lower_left: dict[str, int],
    lower_right: dict[str, int],
    upper_left: dict[str, int],
    upper_right: dict[str, int],
) -> dict:
    """Set file-free fixed sprite corner RGBA values by automation node id."""
    return EffekseerBridgeClient().set_node_sprite_corner_colors_fixed_rgba_by_automation_id(
        automation_node_id,
        lower_left,
        lower_right,
        upper_left,
        upper_right,
    )


@mcp.tool()
def effekseer_set_node_alpha_blend_by_automation_id(
    automation_node_id: str,
    alpha_blend: str,
) -> dict:
    """Set the alpha blend mode by automation node id."""
    return EffekseerBridgeClient().set_node_alpha_blend_by_automation_id(
        automation_node_id,
        alpha_blend,
    )


@mcp.tool()
def effekseer_set_node_z_write_by_automation_id(
    automation_node_id: str,
    z_write: bool,
) -> dict:
    """Set the renderer z-write flag by automation node id."""
    return EffekseerBridgeClient().set_node_z_write_by_automation_id(
        automation_node_id,
        z_write,
    )


@mcp.tool()
def effekseer_set_node_z_test_by_automation_id(
    automation_node_id: str,
    z_test: bool,
) -> dict:
    """Set the renderer z-test flag by automation node id."""
    return EffekseerBridgeClient().set_node_z_test_by_automation_id(
        automation_node_id,
        z_test,
    )


@mcp.tool()
def effekseer_set_node_renderer_type_by_automation_id(
    automation_node_id: str,
    renderer_type: str,
) -> dict:
    """Set the renderer type by automation node id."""
    return EffekseerBridgeClient().set_node_renderer_type_by_automation_id(
        automation_node_id,
        renderer_type,
    )


@mcp.tool()
def effekseer_set_node_color_texture_from_workspace_by_automation_id(
    automation_node_id: str,
    path: str,
) -> dict:
    """Assign a workspace-relative color texture by automation node id."""
    return EffekseerBridgeClient().set_node_color_texture_from_workspace_by_automation_id(
        automation_node_id,
        path,
    )


@mcp.tool()
def effekseer_set_node_normal_texture_from_workspace_by_automation_id(
    automation_node_id: str,
    path: str,
) -> dict:
    """Assign a workspace-relative normal texture by automation node id."""
    return EffekseerBridgeClient().set_node_normal_texture_from_workspace_by_automation_id(
        automation_node_id,
        path,
    )


@mcp.tool()
def effekseer_clear_node_color_texture_by_automation_id(
    automation_node_id: str,
) -> dict:
    """Clear the color texture assignment by automation node id."""
    return EffekseerBridgeClient().clear_node_color_texture_by_automation_id(
        automation_node_id,
    )


@mcp.tool()
def effekseer_clear_node_normal_texture_by_automation_id(
    automation_node_id: str,
) -> dict:
    """Clear the normal texture assignment by automation node id."""
    return EffekseerBridgeClient().clear_node_normal_texture_by_automation_id(
        automation_node_id,
    )


@mcp.tool()
def effekseer_set_node_material_from_workspace_by_automation_id(
    automation_node_id: str,
    path: str,
) -> dict:
    """Assign a workspace-relative .efkmat material by automation node id."""
    return EffekseerBridgeClient().set_node_material_from_workspace_by_automation_id(
        automation_node_id,
        path,
    )


@mcp.tool()
def effekseer_clear_node_material_by_automation_id(
    automation_node_id: str,
) -> dict:
    """Clear the material assignment by automation node id."""
    return EffekseerBridgeClient().clear_node_material_by_automation_id(
        automation_node_id,
    )


@mcp.tool()
def effekseer_set_node_model_from_workspace_by_automation_id(
    automation_node_id: str,
    path: str,
) -> dict:
    """Assign a workspace-relative .efkmodel file by automation node id."""
    return EffekseerBridgeClient().set_node_model_from_workspace_by_automation_id(
        automation_node_id,
        path,
    )


@mcp.tool()
def effekseer_select_node_by_id(editor_node_id: int) -> dict:
    """Select a node by editor node id through the local Automation Bridge."""
    return EffekseerBridgeClient().select_node_by_id(editor_node_id)


@mcp.tool()
def effekseer_add_node_to_parent(
    parent_editor_node_id: int,
    name: str | None = None,
) -> dict:
    """Add a node under a parent node through the local Automation Bridge."""
    return EffekseerBridgeClient().add_node_to_parent(parent_editor_node_id, name)


@mcp.tool()
def effekseer_rename_node(editor_node_id: int, name: str) -> dict:
    """Rename a node through the local Automation Bridge."""
    return EffekseerBridgeClient().rename_node(editor_node_id, name)


def main() -> None:
    transport = os.getenv("MCP_TRANSPORT", "stdio")

    if transport == "http":
        mcp.settings.host = "127.0.0.1"
        mcp.settings.port = int(os.getenv("EFFEKSEER_MCP_PORT", "50124"))
        if not 1 <= mcp.settings.port <= 65535:
            raise ValueError("EFFEKSEER_MCP_PORT must be between 1 and 65535")
        mcp.run(transport="streamable-http")
    else:
        mcp.run()


if __name__ == "__main__":
    main()

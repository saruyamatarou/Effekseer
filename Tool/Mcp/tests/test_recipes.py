from typing import Any

import pytest

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


class FakeRecipeClient:
    def __init__(self, *, fail_on: str | None = None) -> None:
        self.fail_on = fail_on
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self.removed_node_ids: list[str] = []

    def get_node_tree(self) -> dict[str, Any]:
        self.calls.append(("get_node_tree", ()))
        return {
            "root": {
                "automationNodeId": "root",
                "name": "Root",
                "children": [
                    {
                        "automationNodeId": "created",
                        "name": "Burst",
                        "children": [],
                    }
                ],
            }
        }

    def add_node_to_parent_by_automation_id(
        self,
        parent_automation_node_id: str,
        name: str | None = None,
    ) -> dict[str, Any]:
        self.calls.append(
            ("add_node_to_parent_by_automation_id", (parent_automation_node_id, name))
        )
        automation_node_id_by_name = {
            "FireworkRoot": "firework-root",
            "BurstCore": "burst-core",
            "BurstSparks": "burst-sparks",
            "SecondarySparkles": "secondary-sparkles",
            "SlashRoot": "slash-root",
            "SlashArc": "slash-arc",
            "ImpactSparks": "impact-sparks",
            "AfterimageParticles": "afterimage-particles",
            "HealRoot": "heal-root",
            "SoftGlowCore": "soft-glow-core",
            "UpwardSparkles": "upward-sparkles",
            "HealingRing": "healing-ring",
            "ElementalBurstRoot": "elemental-burst-root",
            "CoreGlow": "core-glow",
            "ElementSparks": "element-sparks",
            "ResidualParticles": "residual-particles",
            "ProjectileRoot": "projectile-root",
            "ProjectileCore": "projectile-core",
            "TrailParticles": "trail-particles",
        }
        automation_node_id = automation_node_id_by_name.get(name or "", "created")
        return {
            "ok": True,
            "result": {
                "added_node": {
                    "automationNodeId": automation_node_id,
                    "name": name,
                }
            },
        }

    def rename_node_by_automation_id(
        self,
        automation_node_id: str,
        name: str,
    ) -> dict[str, Any]:
        self.calls.append(("rename_node_by_automation_id", (automation_node_id, name)))
        return {"ok": True}

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

    def set_node_fixed_location_by_automation_id(
        self,
        automation_node_id: str,
        x: float,
        y: float,
        z: float,
    ) -> dict[str, Any]:
        self.calls.append(
            (
                "set_node_fixed_location_by_automation_id",
                (automation_node_id, x, y, z),
            )
        )
        return {"ok": True}

    def set_node_fixed_rotation_by_automation_id(
        self,
        automation_node_id: str,
        x: float,
        y: float,
        z: float,
    ) -> dict[str, Any]:
        self.calls.append(
            (
                "set_node_fixed_rotation_by_automation_id",
                (automation_node_id, x, y, z),
            )
        )
        return {"ok": True}

    def set_node_fixed_scale_by_automation_id(
        self,
        automation_node_id: str,
        x: float,
        y: float,
        z: float,
    ) -> dict[str, Any]:
        self.calls.append(
            ("set_node_fixed_scale_by_automation_id", (automation_node_id, x, y, z))
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

    def set_node_alpha_blend_by_automation_id(
        self,
        automation_node_id: str,
        alpha_blend: str,
    ) -> dict[str, Any]:
        self.calls.append(
            ("set_node_alpha_blend_by_automation_id", (automation_node_id, alpha_blend))
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

    def set_node_is_rendered_by_automation_id(
        self,
        automation_node_id: str,
        is_rendered: bool,
    ) -> dict[str, Any]:
        self.calls.append(
            (
                "set_node_is_rendered_by_automation_id",
                (automation_node_id, is_rendered),
            )
        )
        return {"ok": True}

    def save_project_to_workspace(self, path: str) -> dict[str, Any]:
        self.calls.append(("save_project_to_workspace", (path,)))
        if self.fail_on == "save_project_to_workspace":
            raise RuntimeError("save failed")
        return {"ok": True, "result": {"path": path}}

    def export_runtime_effect_to_workspace(self, path: str) -> dict[str, Any]:
        self.calls.append(("export_runtime_effect_to_workspace", (path,)))
        return {"ok": True, "result": {"path": path, "bytes": 128}}

    def remove_node_by_automation_id(self, automation_node_id: str) -> dict[str, Any]:
        self.calls.append(("remove_node_by_automation_id", (automation_node_id,)))
        self.removed_node_ids.append(automation_node_id)
        return {"ok": True}


def recipe_kwargs(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "name": "Burst",
        "output_project_path": "outputs/basic_burst.efkefc",
        "output_effect_path": "outputs/basic_burst.efk",
        "color": {"r": 255, "g": 128, "b": 32, "a": 255},
        "max_generation": 8,
        "life": {"center": 30, "min": 20, "max": 40},
        "location": {"x": 1.0, "y": 2.0, "z": 3.0},
        "rotation": {"x": 10.0, "y": 20.0, "z": 30.0},
        "scale": {"x": 1.5, "y": 1.5, "z": 1.5},
        "alpha_blend": "Add",
        "texture_path": "inputs/textures/smoke_color.png",
    }
    kwargs.update(overrides)
    return kwargs


def firework_recipe_kwargs(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "name": "FireworkRoot",
        "output_project_path": "outputs/firework.efkefc",
        "output_effect_path": "outputs/firework.efk",
        "primary_color": {"r": 255, "g": 180, "b": 64, "a": 255},
        "secondary_color": {"r": 96, "g": 160, "b": 255, "a": 220},
        "spark_count": 48,
        "secondary_spark_count": 24,
        "burst_life": 45,
        "secondary_life": 35,
        "burst_radius": 80.0,
        "gravity": -0.15,
        "scale": 1.0,
        "texture_path": "inputs/textures/smoke_color.png",
        "sample_tuning": "off",
    }
    kwargs.update(overrides)
    return kwargs


def slash_recipe_kwargs(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "name": "SlashRoot",
        "output_project_path": "outputs/slash.efkefc",
        "output_effect_path": "outputs/slash.efk",
        "primary_color": {"r": 180, "g": 240, "b": 255, "a": 255},
        "secondary_color": {"r": 80, "g": 180, "b": 255, "a": 160},
        "intensity": 1.5,
        "scale": 1.2,
        "duration": 30,
        "element": "wind",
        "texture_path": "inputs/textures/smoke_color.png",
        "sample_tuning": "off",
    }
    kwargs.update(overrides)
    return kwargs


def heal_recipe_kwargs(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "name": "HealRoot",
        "output_project_path": "outputs/heal.efkefc",
        "output_effect_path": "outputs/heal.efk",
        "primary_color": {"r": 255, "g": 230, "b": 128, "a": 255},
        "secondary_color": {"r": 160, "g": 255, "b": 220, "a": 180},
        "intensity": 1.5,
        "scale": 1.2,
        "duration": 45,
        "texture_path": "inputs/textures/smoke_color.png",
        "sample_tuning": "off",
    }
    kwargs.update(overrides)
    return kwargs


def elemental_recipe_kwargs(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "name": "ElementalBurstRoot",
        "output_project_path": "outputs/elemental.efkefc",
        "output_effect_path": "outputs/elemental.efk",
        "primary_color": {"r": 255, "g": 120, "b": 48, "a": 255},
        "secondary_color": {"r": 128, "g": 64, "b": 255, "a": 180},
        "intensity": 1.5,
        "scale": 1.2,
        "duration": 40,
        "element": "fire",
        "texture_path": "inputs/textures/smoke_color.png",
        "sample_tuning": "off",
    }
    kwargs.update(overrides)
    return kwargs


def projectile_recipe_kwargs(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "name": "ProjectileRoot",
        "output_project_path": "outputs/projectile.efkefc",
        "output_effect_path": "outputs/projectile.efk",
        "primary_color": {"r": 255, "g": 96, "b": 40, "a": 255},
        "secondary_color": {"r": 255, "g": 190, "b": 80, "a": 180},
        "intensity": 1.5,
        "scale": 1.2,
        "duration": 45,
        "element": "fire",
        "texture_path": None,
        "sample_tuning": "off",
    }
    kwargs.update(overrides)
    return kwargs


def effect_spec(**overrides: Any) -> dict[str, Any]:
    spec: dict[str, Any] = {
        "kind": "firework",
        "name": "SpecFirework",
        "output_project_path": "outputs/spec_firework.efkefc",
        "output_effect_path": "outputs/spec_firework.efk",
        "primary_color": {"r": 255, "g": 180, "b": 64, "a": 255},
        "secondary_color": {"r": 96, "g": 160, "b": 255, "a": 220},
        "intensity": 2.0,
        "scale": 1.25,
        "duration": 60,
        "texture_path": "inputs/textures/smoke_color.png",
        "sample_tuning": "off",
    }
    spec.update(overrides)
    return spec


def assert_only_container_hidden(
    client: FakeRecipeClient,
    container_id: str,
    child_ids: set[str],
) -> None:
    render_calls = [
        call
        for call in client.calls
        if call[0] == "set_node_is_rendered_by_automation_id"
    ]
    assert render_calls == [
        ("set_node_is_rendered_by_automation_id", (container_id, False))
    ]
    assert not any(call[1][0] in child_ids for call in render_calls)


def test_list_effect_recipes_includes_supported_recipes() -> None:
    recipe_ids = {recipe["id"] for recipe in list_effect_recipes()}

    assert recipe_ids == {
        "basic_sprite_burst",
        "elemental_burst",
        "firework_burst",
        "heal_sparkle",
        "projectile_trail",
        "slash",
    }


def test_describe_effect_recipe_accepts_firework_alias() -> None:
    recipe = describe_effect_recipe("firework")

    assert recipe["id"] == "firework_burst"
    assert "firework" in recipe["effect_spec_kinds"]


def test_describe_effect_recipe_accepts_slash_alias() -> None:
    recipe = describe_effect_recipe("wind_slash")

    assert recipe["id"] == "slash"
    assert "wind_slash" in recipe["effect_spec_kinds"]


def test_describe_effect_recipe_accepts_heal_alias() -> None:
    recipe = describe_effect_recipe("holy_heal")

    assert recipe["id"] == "heal_sparkle"
    assert "holy_heal" in recipe["effect_spec_kinds"]


def test_describe_effect_recipe_accepts_elemental_alias() -> None:
    recipe = describe_effect_recipe("water")

    assert recipe["id"] == "elemental_burst"
    assert "water" in recipe["effect_spec_kinds"]


def test_describe_effect_recipe_accepts_projectile_alias() -> None:
    recipe = describe_effect_recipe("fireball")

    assert recipe["id"] == "projectile_trail"
    assert "fireball" in recipe["effect_spec_kinds"]


def test_create_effect_from_spec_routes_firework_and_computes_intensity() -> None:
    client = FakeRecipeClient()

    result = create_effect_from_spec(effect_spec(), client=client)

    assert result["recipe"] == "firework_burst"
    assert result["effect_spec_version"] == "v0"
    assert result["project_path"] == "outputs/spec_firework.efkefc"
    assert result["effect_path"] == "outputs/spec_firework.efk"
    assert ("add_node_to_parent_by_automation_id", ("root", "SpecFirework")) in (
        client.calls
    )
    assert ("set_node_max_generation_by_automation_id", ("burst-sparks", 110)) in (
        client.calls
    )
    assert (
        "set_node_max_generation_by_automation_id",
        ("secondary-sparkles", 43),
    ) in client.calls
    assert ("set_node_life_by_automation_id", ("burst-sparks", 60, 45, 60)) in (
        client.calls
    )
    assert (
        "set_node_life_by_automation_id",
        ("secondary-sparkles", 59, 44, 59),
    ) in client.calls


def test_create_effect_from_spec_routes_basic_sprite_burst() -> None:
    client = FakeRecipeClient()

    result = create_effect_from_spec(
        effect_spec(
            kind="basic_sprite_burst",
            name="SpecBasic",
            output_project_path="outputs/spec_basic.efkefc",
            output_effect_path="outputs/spec_basic.efk",
            secondary_color=None,
            intensity=1.5,
            scale=2.0,
            duration=40,
            texture_path=None,
        ),
        client=client,
    )

    assert result["recipe"] == "basic_sprite_burst"
    assert ("add_node_to_parent_by_automation_id", ("root", "SpecBasic")) in (
        client.calls
    )
    assert ("set_node_max_generation_by_automation_id", ("created", 12)) in (
        client.calls
    )
    assert ("set_node_life_by_automation_id", ("created", 40, 30, 50)) in (
        client.calls
    )
    assert ("set_node_fixed_scale_by_automation_id", ("created", 2.0, 2.0, 2.0)) in (
        client.calls
    )
    assert not any(
        call[0] == "set_node_color_texture_from_workspace_by_automation_id"
        for call in client.calls
    )


def test_create_effect_from_spec_routes_slash_and_infers_element() -> None:
    client = FakeRecipeClient()

    result = create_effect_from_spec(
        effect_spec(
            kind="fire_slash",
            name="SlashRoot",
            output_project_path="outputs/spec_slash.efkefc",
            output_effect_path="outputs/spec_slash.efk",
            secondary_color=None,
            intensity=2.0,
            scale=1.5,
            duration=None,
            texture_path=None,
        ),
        client=client,
    )

    assert result["recipe"] == "slash"
    assert result["element"] == "fire"
    assert result["nodes"] == {
        "slash_root": "slash-root",
        "slash_arc": "slash-arc",
        "impact_sparks": "impact-sparks",
        "afterimage_particles": "afterimage-particles",
    }
    assert ("set_node_fixed_rotation_by_automation_id", ("slash-arc", 0.0, 0.0, -45.0)) in client.calls
    assert ("set_node_max_generation_by_automation_id", ("impact-sparks", 38)) in (
        client.calls
    )


def test_create_effect_from_spec_routes_heal_sparkle() -> None:
    client = FakeRecipeClient()

    result = create_effect_from_spec(
        effect_spec(
            kind="holy_heal",
            name="HealRoot",
            output_project_path="outputs/spec_heal.efkefc",
            output_effect_path="outputs/spec_heal.efk",
            secondary_color=None,
            intensity=2.0,
            scale=1.5,
            duration=None,
            texture_path=None,
        ),
        client=client,
    )

    assert result["recipe"] == "heal_sparkle"
    assert result["nodes"] == {
        "heal_root": "heal-root",
        "soft_glow_core": "soft-glow-core",
        "upward_sparkles": "upward-sparkles",
        "healing_ring": "healing-ring",
    }
    assert (
        "set_node_max_generation_by_automation_id",
        ("upward-sparkles", 36),
    ) in client.calls
    assert ("set_node_life_by_automation_id", ("healing-ring", 49, 39, 49)) in (
        client.calls
    )


def test_create_effect_from_spec_routes_elemental_kind() -> None:
    client = FakeRecipeClient()

    result = create_effect_from_spec(
        effect_spec(
            kind="dark",
            name="ElementalBurstRoot",
            output_project_path="outputs/spec_dark.efkefc",
            output_effect_path="outputs/spec_dark.efk",
            secondary_color=None,
            intensity=2.0,
            scale=1.5,
            duration=None,
            texture_path=None,
        ),
        client=client,
    )

    assert result["recipe"] == "elemental_burst"
    assert result["element"] == "dark"
    assert result["nodes"] == {
        "elemental_burst_root": "elemental-burst-root",
        "core_glow": "core-glow",
        "element_sparks": "element-sparks",
        "residual_particles": "residual-particles",
    }
    assert ("set_node_max_generation_by_automation_id", ("element-sparks", 66)) in (
        client.calls
    )
    assert ("set_node_life_by_automation_id", ("element-sparks", 50, 37, 50)) in (
        client.calls
    )


def test_create_effect_from_spec_elemental_burst_defaults_to_fire() -> None:
    client = FakeRecipeClient()

    result = create_effect_from_spec(
        effect_spec(
            kind="elemental_burst",
            name="ElementalBurstRoot",
            output_project_path="outputs/spec_elemental.efkefc",
            output_effect_path="outputs/spec_elemental.efk",
            intensity=1.0,
            scale=1.0,
            duration=40,
            texture_path=None,
        ),
        client=client,
    )

    assert result["element"] == "fire"


def test_create_effect_from_spec_routes_projectile_kind() -> None:
    client = FakeRecipeClient()

    result = create_effect_from_spec(
        effect_spec(
            kind="dark_projectile",
            name="ProjectileRoot",
            output_project_path="outputs/spec_projectile.efkefc",
            output_effect_path="outputs/spec_projectile.efk",
            secondary_color=None,
            intensity=2.0,
            scale=1.5,
            duration=None,
            texture_path=None,
        ),
        client=client,
    )

    assert result["recipe"] == "projectile_trail"
    assert result["element"] == "dark"
    assert result["nodes"] == {
        "projectile_root": "projectile-root",
        "projectile_core": "projectile-core",
        "trail_particles": "trail-particles",
        "impact_sparks": "impact-sparks",
    }
    assert (
        "set_node_max_generation_by_automation_id",
        ("trail-particles", 52),
    ) in client.calls
    assert ("set_node_life_by_automation_id", ("trail-particles", 70, 52, 70)) in (
        client.calls
    )


def test_create_effect_from_spec_projectile_defaults_to_fire() -> None:
    client = FakeRecipeClient()

    result = create_effect_from_spec(
        effect_spec(
            kind="projectile_trail",
            name="ProjectileRoot",
            output_project_path="outputs/spec_projectile.efkefc",
            output_effect_path="outputs/spec_projectile.efk",
            intensity=1.0,
            scale=1.0,
            duration=45,
            texture_path=None,
        ),
        client=client,
    )

    assert result["element"] == "fire"


def test_create_effect_from_spec_passes_texture_role_overrides() -> None:
    client = FakeRecipeClient()

    create_effect_from_spec(
        effect_spec(
            kind="water_projectile",
            name="ProjectileRoot",
            output_project_path="outputs/spec_projectile.efkefc",
            output_effect_path="outputs/spec_projectile.efk",
            texture_path=None,
            texture_set="builtin",
            textures={"trail": "inputs/textures/custom_trail.png"},
        ),
        client=client,
    )

    assert (
        "set_node_color_texture_from_workspace_by_automation_id",
        ("trail-particles", "inputs/textures/custom_trail.png"),
    ) in client.calls
    assert (
        "set_node_color_texture_from_workspace_by_automation_id",
        ("projectile-core", "inputs/textures/builtin/core_glow.png"),
    ) in client.calls


def test_create_effect_from_spec_uses_primary_color_when_secondary_is_null() -> None:
    client = FakeRecipeClient()
    primary_color = {"r": 20, "g": 30, "b": 40, "a": 255}

    create_effect_from_spec(
        effect_spec(primary_color=primary_color, secondary_color=None),
        client=client,
    )

    assert (
        "set_node_color_all_fixed_rgba_by_automation_id",
        ("secondary-sparkles", 20, 30, 40, 173),
    ) in client.calls


def test_create_effect_from_spec_rejects_unsupported_kind() -> None:
    with pytest.raises(RuntimeError, match="unsupported effect recipe kind"):
        create_effect_from_spec(effect_spec(kind="not_supported"))


def test_create_effect_from_spec_rejects_invalid_spec_values() -> None:
    with pytest.raises(RuntimeError, match="primary_color.r must be an int"):
        create_effect_from_spec(
            effect_spec(primary_color={"r": True, "g": 0, "b": 0, "a": 255})
        )


def test_create_basic_sprite_burst_effect_runs_expected_commands() -> None:
    client = FakeRecipeClient()

    result = create_basic_sprite_burst_effect(client=client, **recipe_kwargs())

    assert result["automationNodeId"] == "created"
    assert result["project_path"] == "outputs/basic_burst.efkefc"
    assert result["effect_path"] == "outputs/basic_burst.efk"
    assert [command["command"] for command in result["commands"]] == [
        "add_node_to_parent_by_automation_id",
        "rename_node_by_automation_id",
        "set_node_renderer_type_by_automation_id",
        "set_node_max_generation_by_automation_id",
        "set_node_life_by_automation_id",
        "set_node_fixed_location_by_automation_id",
        "set_node_fixed_rotation_by_automation_id",
        "set_node_fixed_scale_by_automation_id",
        "set_node_color_all_fixed_rgba_by_automation_id",
        "set_node_alpha_blend_by_automation_id",
        "set_node_color_texture_from_workspace_by_automation_id",
        "save_project_to_workspace",
        "export_runtime_effect_to_workspace",
    ]
    assert client.calls == [
        ("get_node_tree", ()),
        ("add_node_to_parent_by_automation_id", ("root", "Burst")),
        ("rename_node_by_automation_id", ("created", "Burst")),
        ("set_node_renderer_type_by_automation_id", ("created", "Sprite")),
        ("set_node_max_generation_by_automation_id", ("created", 8)),
        ("set_node_life_by_automation_id", ("created", 30, 20, 40)),
        ("set_node_fixed_location_by_automation_id", ("created", 1.0, 2.0, 3.0)),
        ("set_node_fixed_rotation_by_automation_id", ("created", 10.0, 20.0, 30.0)),
        ("set_node_fixed_scale_by_automation_id", ("created", 1.5, 1.5, 1.5)),
        (
            "set_node_color_all_fixed_rgba_by_automation_id",
            ("created", 255, 128, 32, 255),
        ),
        ("set_node_alpha_blend_by_automation_id", ("created", "Add")),
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("created", "inputs/textures/smoke_color.png"),
        ),
        ("save_project_to_workspace", ("outputs/basic_burst.efkefc",)),
        ("export_runtime_effect_to_workspace", ("outputs/basic_burst.efk",)),
    ]


def test_create_basic_sprite_burst_effect_skips_texture_when_not_requested() -> None:
    client = FakeRecipeClient()

    create_basic_sprite_burst_effect(
        client=client,
        **recipe_kwargs(texture_path=None),
    )

    assert not any(
        call[0] == "set_node_color_texture_from_workspace_by_automation_id"
        for call in client.calls
    )


def test_create_basic_sprite_burst_effect_cleans_up_created_node_on_failure() -> None:
    client = FakeRecipeClient(fail_on="save_project_to_workspace")

    with pytest.raises(RuntimeError, match="save failed"):
        create_basic_sprite_burst_effect(client=client, **recipe_kwargs())

    assert client.removed_node_ids == ["created"]


def test_create_firework_burst_effect_runs_expected_commands() -> None:
    client = FakeRecipeClient()

    result = create_firework_burst_effect(
        client=client,
        **firework_recipe_kwargs(),
    )

    assert result["automationNodeId"] == "firework-root"
    assert result["nodes"] == {
        "firework_root": "firework-root",
        "burst_core": "burst-core",
        "burst_sparks": "burst-sparks",
        "secondary_sparkles": "secondary-sparkles",
    }
    assert_only_container_hidden(
        client,
        "firework-root",
        {"burst-core", "burst-sparks", "secondary-sparkles"},
    )
    assert result["project_path"] == "outputs/firework.efkefc"
    assert result["effect_path"] == "outputs/firework.efk"
    assert client.calls[:5] == [
        ("get_node_tree", ()),
        ("add_node_to_parent_by_automation_id", ("root", "FireworkRoot")),
        ("set_node_is_rendered_by_automation_id", ("firework-root", False)),
        (
            "add_node_to_parent_by_automation_id",
            ("firework-root", "BurstCore"),
        ),
        (
            "add_node_to_parent_by_automation_id",
            ("firework-root", "BurstSparks"),
        ),
    ]
    assert client.calls[5] == (
        "add_node_to_parent_by_automation_id",
        ("firework-root", "SecondarySparkles"),
    )
    assert ("set_node_max_generation_by_automation_id", ("burst-core", 1)) in (
        client.calls
    )
    assert ("set_node_max_generation_by_automation_id", ("burst-sparks", 55)) in (
        client.calls
    )
    assert (
        "set_node_max_generation_by_automation_id",
        ("secondary-sparkles", 22),
    ) in client.calls
    assert ("set_node_generation_time_by_automation_id", ("burst-sparks", 0.0, 0.0, 0.0)) in client.calls
    assert (
        "set_node_generation_time_by_automation_id",
        ("secondary-sparkles", 0.12, 0.12, 0.12),
    ) in client.calls
    assert (
        "set_node_location_type_by_automation_id",
        ("burst-sparks", "PVA"),
    ) in client.calls
    assert (
        "set_node_scale_type_by_automation_id",
        ("secondary-sparkles", "PVA"),
    ) in client.calls
    assert client.calls[-2:] == [
        ("save_project_to_workspace", ("outputs/firework.efkefc",)),
        ("export_runtime_effect_to_workspace", ("outputs/firework.efk",)),
    ]


def test_create_firework_burst_effect_assigns_texture_to_all_nodes() -> None:
    client = FakeRecipeClient()

    create_firework_burst_effect(
        client=client,
        **firework_recipe_kwargs(texture_path="inputs/textures/smoke_color.png"),
    )

    texture_calls = [
        call
        for call in client.calls
        if call[0] == "set_node_color_texture_from_workspace_by_automation_id"
    ]
    assert texture_calls == [
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("burst-core", "inputs/textures/smoke_color.png"),
        ),
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("burst-sparks", "inputs/textures/smoke_color.png"),
        ),
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("secondary-sparkles", "inputs/textures/smoke_color.png"),
        ),
    ]


def test_create_firework_burst_effect_uses_builtin_textures_when_not_requested() -> None:
    client = FakeRecipeClient()

    create_firework_burst_effect(
        client=client,
        **firework_recipe_kwargs(texture_path=None),
    )

    texture_calls = [
        call
        for call in client.calls
        if call[0] == "set_node_color_texture_from_workspace_by_automation_id"
    ]
    assert texture_calls == [
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("burst-core", "inputs/textures/builtin/core_glow.png"),
        ),
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("burst-sparks", "inputs/textures/builtin/spark_star.png"),
        ),
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("secondary-sparkles", "inputs/textures/builtin/smoke_puff_01.png"),
        ),
    ]


def test_create_firework_burst_effect_cleans_up_root_on_failure() -> None:
    client = FakeRecipeClient(fail_on="save_project_to_workspace")

    with pytest.raises(RuntimeError, match="save failed"):
        create_firework_burst_effect(
            client=client,
            **firework_recipe_kwargs(),
        )

    assert client.removed_node_ids == ["firework-root"]


def test_create_slash_effect_runs_expected_commands() -> None:
    client = FakeRecipeClient()

    result = create_slash_effect(client=client, **slash_recipe_kwargs())

    assert result["automationNodeId"] == "slash-root"
    assert result["nodes"] == {
        "slash_root": "slash-root",
        "slash_arc": "slash-arc",
        "impact_sparks": "impact-sparks",
        "afterimage_particles": "afterimage-particles",
    }
    assert_only_container_hidden(
        client,
        "slash-root",
        {"slash-arc", "impact-sparks", "afterimage-particles"},
    )
    assert result["element"] == "wind"
    assert result["project_path"] == "outputs/slash.efkefc"
    assert result["effect_path"] == "outputs/slash.efk"
    assert client.calls[:5] == [
        ("get_node_tree", ()),
        ("add_node_to_parent_by_automation_id", ("root", "SlashRoot")),
        ("set_node_is_rendered_by_automation_id", ("slash-root", False)),
        ("add_node_to_parent_by_automation_id", ("slash-root", "SlashArc")),
        ("add_node_to_parent_by_automation_id", ("slash-root", "ImpactSparks")),
    ]
    assert client.calls[5] == (
        "add_node_to_parent_by_automation_id",
        ("slash-root", "AfterimageParticles"),
    )
    assert ("set_node_max_generation_by_automation_id", ("slash-arc", 1)) in (
        client.calls
    )
    assert ("set_node_fixed_rotation_by_automation_id", ("slash-arc", 0.0, 0.0, -25.0)) in client.calls
    assert ("set_node_max_generation_by_automation_id", ("impact-sparks", 28)) in (
        client.calls
    )
    assert (
        "set_node_max_generation_by_automation_id",
        ("afterimage-particles", 15),
    ) in client.calls
    assert client.calls[-2:] == [
        ("save_project_to_workspace", ("outputs/slash.efkefc",)),
        ("export_runtime_effect_to_workspace", ("outputs/slash.efk",)),
    ]


def test_create_slash_effect_assigns_texture_to_all_nodes() -> None:
    client = FakeRecipeClient()

    create_slash_effect(
        client=client,
        **slash_recipe_kwargs(texture_path="inputs/textures/smoke_color.png"),
    )

    texture_calls = [
        call
        for call in client.calls
        if call[0] == "set_node_color_texture_from_workspace_by_automation_id"
    ]
    assert texture_calls == [
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("slash-arc", "inputs/textures/smoke_color.png"),
        ),
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("impact-sparks", "inputs/textures/smoke_color.png"),
        ),
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("afterimage-particles", "inputs/textures/smoke_color.png"),
        ),
    ]


def test_create_slash_effect_uses_builtin_textures_when_not_requested() -> None:
    client = FakeRecipeClient()

    create_slash_effect(
        client=client,
        **slash_recipe_kwargs(texture_path=None),
    )

    texture_calls = [
        call
        for call in client.calls
        if call[0] == "set_node_color_texture_from_workspace_by_automation_id"
    ]
    assert texture_calls == [
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("slash-arc", "inputs/textures/builtin/slash_arc.png"),
        ),
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("impact-sparks", "inputs/textures/builtin/spark_star.png"),
        ),
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("afterimage-particles", "inputs/textures/builtin/trail_streak.png"),
        ),
    ]


def test_create_slash_effect_uses_role_texture_overrides() -> None:
    client = FakeRecipeClient()

    create_slash_effect(
        client=client,
        **slash_recipe_kwargs(
            texture_path="inputs/textures/legacy.png",
            texture_set="builtin",
            textures={
                "slash": "inputs/textures/custom_slash.png",
                "trail": "inputs/textures/custom_trail.png",
            },
        ),
    )

    texture_calls = [
        call
        for call in client.calls
        if call[0] == "set_node_color_texture_from_workspace_by_automation_id"
    ]
    assert texture_calls == [
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("slash-arc", "inputs/textures/custom_slash.png"),
        ),
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("impact-sparks", "inputs/textures/builtin/spark_star.png"),
        ),
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("afterimage-particles", "inputs/textures/custom_trail.png"),
        ),
    ]


def test_create_slash_effect_rejects_unsupported_element() -> None:
    with pytest.raises(RuntimeError, match="unsupported slash element"):
        create_slash_effect(**slash_recipe_kwargs(element="metal"))


def test_create_slash_effect_rejects_unsupported_visual_profile() -> None:
    with pytest.raises(ValueError, match="unsupported visual profile"):
        create_slash_effect(**slash_recipe_kwargs(visual_profile="not_a_profile"))


def test_create_slash_effect_cleans_up_root_on_failure() -> None:
    client = FakeRecipeClient(fail_on="save_project_to_workspace")

    with pytest.raises(RuntimeError, match="save failed"):
        create_slash_effect(client=client, **slash_recipe_kwargs())

    assert client.removed_node_ids == ["slash-root"]


def test_create_heal_sparkle_effect_runs_expected_commands() -> None:
    client = FakeRecipeClient()

    result = create_heal_sparkle_effect(client=client, **heal_recipe_kwargs())

    assert result["automationNodeId"] == "heal-root"
    assert result["nodes"] == {
        "heal_root": "heal-root",
        "soft_glow_core": "soft-glow-core",
        "upward_sparkles": "upward-sparkles",
        "healing_ring": "healing-ring",
    }
    assert_only_container_hidden(
        client,
        "heal-root",
        {"soft-glow-core", "upward-sparkles", "healing-ring"},
    )
    assert result["project_path"] == "outputs/heal.efkefc"
    assert result["effect_path"] == "outputs/heal.efk"
    assert client.calls[:5] == [
        ("get_node_tree", ()),
        ("add_node_to_parent_by_automation_id", ("root", "HealRoot")),
        ("set_node_is_rendered_by_automation_id", ("heal-root", False)),
        ("add_node_to_parent_by_automation_id", ("heal-root", "SoftGlowCore")),
        ("add_node_to_parent_by_automation_id", ("heal-root", "UpwardSparkles")),
    ]
    assert client.calls[5] == (
        "add_node_to_parent_by_automation_id",
        ("heal-root", "HealingRing"),
    )
    assert ("set_node_max_generation_by_automation_id", ("soft-glow-core", 1)) in (
        client.calls
    )
    assert (
        "set_node_max_generation_by_automation_id",
        ("upward-sparkles", 27),
    ) in client.calls
    assert ("set_node_life_by_automation_id", ("healing-ring", 49, 39, 49)) in (
        client.calls
    )
    ring_scale_call = next(
        call
        for call in client.calls
        if call[0] == "set_node_fixed_scale_by_automation_id"
        and call[1][0] == "healing-ring"
    )
    assert ring_scale_call[1] == (
        "healing-ring",
        pytest.approx(4.1715),
        pytest.approx(4.1715),
        1.62,
    )
    assert client.calls[-2:] == [
        ("save_project_to_workspace", ("outputs/heal.efkefc",)),
        ("export_runtime_effect_to_workspace", ("outputs/heal.efk",)),
    ]


def test_create_heal_sparkle_effect_assigns_texture_to_all_nodes() -> None:
    client = FakeRecipeClient()

    create_heal_sparkle_effect(
        client=client,
        **heal_recipe_kwargs(texture_path="inputs/textures/smoke_color.png"),
    )

    texture_calls = [
        call
        for call in client.calls
        if call[0] == "set_node_color_texture_from_workspace_by_automation_id"
    ]
    assert texture_calls == [
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("soft-glow-core", "inputs/textures/smoke_color.png"),
        ),
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("upward-sparkles", "inputs/textures/smoke_color.png"),
        ),
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("healing-ring", "inputs/textures/smoke_color.png"),
        ),
    ]


def test_create_heal_sparkle_effect_uses_builtin_textures_when_not_requested() -> None:
    client = FakeRecipeClient()

    create_heal_sparkle_effect(
        client=client,
        **heal_recipe_kwargs(texture_path=None),
    )

    texture_calls = [
        call
        for call in client.calls
        if call[0] == "set_node_color_texture_from_workspace_by_automation_id"
    ]
    assert texture_calls == [
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("soft-glow-core", "inputs/textures/builtin/core_glow.png"),
        ),
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("upward-sparkles", "inputs/textures/builtin/spark_star.png"),
        ),
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("healing-ring", "inputs/textures/builtin/ring_soft.png"),
        ),
    ]


def test_create_heal_sparkle_effect_uses_faded_primary_when_secondary_is_null() -> None:
    client = FakeRecipeClient()

    create_heal_sparkle_effect(
        client=client,
        **heal_recipe_kwargs(
            primary_color={"r": 200, "g": 210, "b": 220, "a": 255},
            secondary_color=None,
        ),
    )

    assert (
        "set_node_color_all_fixed_rgba_by_automation_id",
        ("upward-sparkles", 200, 210, 220, 128),
    ) in client.calls
    assert (
        "set_node_color_all_fixed_rgba_by_automation_id",
        ("healing-ring", 200, 210, 220, 70),
    ) in client.calls


def test_create_heal_sparkle_effect_cleans_up_root_on_failure() -> None:
    client = FakeRecipeClient(fail_on="save_project_to_workspace")

    with pytest.raises(RuntimeError, match="save failed"):
        create_heal_sparkle_effect(client=client, **heal_recipe_kwargs())

    assert client.removed_node_ids == ["heal-root"]


def test_create_elemental_burst_effect_runs_expected_commands() -> None:
    client = FakeRecipeClient()

    result = create_elemental_burst_effect(client=client, **elemental_recipe_kwargs())

    assert result["automationNodeId"] == "elemental-burst-root"
    assert result["nodes"] == {
        "elemental_burst_root": "elemental-burst-root",
        "core_glow": "core-glow",
        "element_sparks": "element-sparks",
        "residual_particles": "residual-particles",
    }
    assert_only_container_hidden(
        client,
        "elemental-burst-root",
        {"core-glow", "element-sparks", "residual-particles"},
    )
    assert result["element"] == "fire"
    assert result["project_path"] == "outputs/elemental.efkefc"
    assert result["effect_path"] == "outputs/elemental.efk"
    assert client.calls[:5] == [
        ("get_node_tree", ()),
        (
            "add_node_to_parent_by_automation_id",
            ("root", "ElementalBurstRoot"),
        ),
        (
            "set_node_is_rendered_by_automation_id",
            ("elemental-burst-root", False),
        ),
        (
            "add_node_to_parent_by_automation_id",
            ("elemental-burst-root", "CoreGlow"),
        ),
        (
            "add_node_to_parent_by_automation_id",
            ("elemental-burst-root", "ElementSparks"),
        ),
    ]
    assert client.calls[5] == (
        "add_node_to_parent_by_automation_id",
        ("elemental-burst-root", "ResidualParticles"),
    )
    assert ("set_node_max_generation_by_automation_id", ("core-glow", 1)) in (
        client.calls
    )
    assert ("set_node_max_generation_by_automation_id", ("element-sparks", 60)) in (
        client.calls
    )
    assert ("set_node_life_by_automation_id", ("element-sparks", 38, 28, 38)) in (
        client.calls
    )
    assert (
        "set_node_max_generation_by_automation_id",
        ("residual-particles", 34),
    ) in client.calls
    assert client.calls[-2:] == [
        ("save_project_to_workspace", ("outputs/elemental.efkefc",)),
        ("export_runtime_effect_to_workspace", ("outputs/elemental.efk",)),
    ]


def test_create_elemental_burst_effect_assigns_texture_to_all_nodes() -> None:
    client = FakeRecipeClient()

    create_elemental_burst_effect(
        client=client,
        **elemental_recipe_kwargs(texture_path="inputs/textures/smoke_color.png"),
    )

    texture_calls = [
        call
        for call in client.calls
        if call[0] == "set_node_color_texture_from_workspace_by_automation_id"
    ]
    assert texture_calls == [
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("core-glow", "inputs/textures/smoke_color.png"),
        ),
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("element-sparks", "inputs/textures/smoke_color.png"),
        ),
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("residual-particles", "inputs/textures/smoke_color.png"),
        ),
    ]


def test_create_elemental_burst_effect_uses_builtin_textures_when_not_requested() -> None:
    client = FakeRecipeClient()

    create_elemental_burst_effect(
        client=client,
        **elemental_recipe_kwargs(texture_path=None),
    )

    texture_calls = [
        call
        for call in client.calls
        if call[0] == "set_node_color_texture_from_workspace_by_automation_id"
    ]
    assert texture_calls == [
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("core-glow", "inputs/textures/builtin/core_glow.png"),
        ),
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("element-sparks", "inputs/textures/builtin/spark_star.png"),
        ),
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("residual-particles", "inputs/textures/builtin/smoke_puff_01.png"),
        ),
    ]


def test_create_elemental_burst_effect_rejects_unsupported_element() -> None:
    with pytest.raises(RuntimeError, match="unsupported elemental element"):
        create_elemental_burst_effect(**elemental_recipe_kwargs(element="metal"))


def test_create_elemental_burst_effect_uses_faded_primary_when_secondary_is_null() -> None:
    client = FakeRecipeClient()

    create_elemental_burst_effect(
        client=client,
        **elemental_recipe_kwargs(
            primary_color={"r": 220, "g": 80, "b": 40, "a": 255},
            secondary_color=None,
        ),
    )

    assert (
        "set_node_color_all_fixed_rgba_by_automation_id",
        ("residual-particles", 220, 80, 40, 79),
    ) in client.calls


def test_create_elemental_burst_effect_cleans_up_root_on_failure() -> None:
    client = FakeRecipeClient(fail_on="save_project_to_workspace")

    with pytest.raises(RuntimeError, match="save failed"):
        create_elemental_burst_effect(client=client, **elemental_recipe_kwargs())

    assert client.removed_node_ids == ["elemental-burst-root"]


def test_create_projectile_trail_effect_runs_expected_commands() -> None:
    client = FakeRecipeClient()

    result = create_projectile_trail_effect(
        client=client,
        **projectile_recipe_kwargs(),
    )

    assert result["automationNodeId"] == "projectile-root"
    assert result["nodes"] == {
        "projectile_root": "projectile-root",
        "projectile_core": "projectile-core",
        "trail_particles": "trail-particles",
        "impact_sparks": "impact-sparks",
    }
    assert_only_container_hidden(
        client,
        "projectile-root",
        {"projectile-core", "trail-particles", "impact-sparks"},
    )
    assert result["element"] == "fire"
    assert result["project_path"] == "outputs/projectile.efkefc"
    assert result["effect_path"] == "outputs/projectile.efk"
    assert client.calls[:5] == [
        ("get_node_tree", ()),
        (
            "add_node_to_parent_by_automation_id",
            ("root", "ProjectileRoot"),
        ),
        ("set_node_is_rendered_by_automation_id", ("projectile-root", False)),
        (
            "add_node_to_parent_by_automation_id",
            ("projectile-root", "ProjectileCore"),
        ),
        (
            "add_node_to_parent_by_automation_id",
            ("projectile-root", "TrailParticles"),
        ),
    ]
    assert client.calls[5] == (
        "add_node_to_parent_by_automation_id",
        ("projectile-root", "ImpactSparks"),
    )
    assert (
        "set_node_max_generation_by_automation_id",
        ("trail-particles", 45),
    ) in client.calls
    assert ("set_node_life_by_automation_id", ("trail-particles", 59, 44, 59)) in (
        client.calls
    )
    assert ("set_node_max_generation_by_automation_id", ("impact-sparks", 24)) in (
        client.calls
    )
    assert ("set_node_life_by_automation_id", ("impact-sparks", 28, 21, 28)) in (
        client.calls
    )
    assert client.calls[-2:] == [
        ("save_project_to_workspace", ("outputs/projectile.efkefc",)),
        ("export_runtime_effect_to_workspace", ("outputs/projectile.efk",)),
    ]


def test_create_projectile_trail_effect_assigns_texture_to_all_nodes() -> None:
    client = FakeRecipeClient()

    create_projectile_trail_effect(
        client=client,
        **projectile_recipe_kwargs(texture_path="inputs/textures/smoke_color.png"),
    )

    texture_calls = [
        call
        for call in client.calls
        if call[0] == "set_node_color_texture_from_workspace_by_automation_id"
    ]
    assert texture_calls == [
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("projectile-core", "inputs/textures/smoke_color.png"),
        ),
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("trail-particles", "inputs/textures/smoke_color.png"),
        ),
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("impact-sparks", "inputs/textures/smoke_color.png"),
        ),
    ]


def test_create_projectile_trail_effect_uses_builtin_textures_when_not_requested() -> None:
    client = FakeRecipeClient()

    create_projectile_trail_effect(
        client=client,
        **projectile_recipe_kwargs(texture_path=None),
    )

    texture_calls = [
        call
        for call in client.calls
        if call[0] == "set_node_color_texture_from_workspace_by_automation_id"
    ]
    assert texture_calls == [
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("projectile-core", "inputs/textures/builtin/core_glow.png"),
        ),
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("trail-particles", "inputs/textures/builtin/trail_streak.png"),
        ),
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            ("impact-sparks", "inputs/textures/builtin/ripple_ring.png"),
        ),
    ]


def test_create_projectile_trail_effect_rejects_unsupported_element() -> None:
    with pytest.raises(RuntimeError, match="unsupported projectile element"):
        create_projectile_trail_effect(**projectile_recipe_kwargs(element="metal"))


def test_create_projectile_trail_effect_uses_faded_primary_when_secondary_is_null() -> None:
    client = FakeRecipeClient()

    create_projectile_trail_effect(
        client=client,
        **projectile_recipe_kwargs(
            primary_color={"r": 80, "g": 160, "b": 240, "a": 255},
            secondary_color=None,
        ),
    )

    assert (
        "set_node_color_all_fixed_rgba_by_automation_id",
        ("trail-particles", 80, 160, 240, 92),
    ) in client.calls


def test_create_projectile_trail_effect_cleans_up_root_on_failure() -> None:
    client = FakeRecipeClient(fail_on="save_project_to_workspace")

    with pytest.raises(RuntimeError, match="save failed"):
        create_projectile_trail_effect(client=client, **projectile_recipe_kwargs())

    assert client.removed_node_ids == ["projectile-root"]

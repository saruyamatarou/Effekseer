from typing import Any

from effekseer_mcp import server


def test_server_basic_sprite_burst_tool_calls_recipe(
    monkeypatch,
) -> None:
    calls: list[dict[str, Any]] = []

    def fake_create_basic_sprite_burst_effect(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        return {
            "automationNodeId": "created",
            "project_path": kwargs["output_project_path"],
            "effect_path": kwargs["output_effect_path"],
            "commands": [],
        }

    monkeypatch.setattr(
        server,
        "create_basic_sprite_burst_effect",
        fake_create_basic_sprite_burst_effect,
    )

    result = server.effekseer_create_basic_sprite_burst_effect(
        name="Burst",
        output_project_path="outputs/burst.efkefc",
        output_effect_path="outputs/burst.efk",
        color={"r": 255, "g": 128, "b": 32, "a": 255},
        max_generation=8,
        life={"center": 30, "min": 20, "max": 40},
        location={"x": 1.0, "y": 2.0, "z": 3.0},
        rotation={"x": 10.0, "y": 20.0, "z": 30.0},
        scale={"x": 1.5, "y": 1.5, "z": 1.5},
        alpha_blend="Add",
        texture_path="inputs/textures/smoke_color.png",
    )

    assert result == {
        "automationNodeId": "created",
        "project_path": "outputs/burst.efkefc",
        "effect_path": "outputs/burst.efk",
        "commands": [],
    }
    assert calls == [
        {
            "name": "Burst",
            "output_project_path": "outputs/burst.efkefc",
            "output_effect_path": "outputs/burst.efk",
            "color": {"r": 255, "g": 128, "b": 32, "a": 255},
            "max_generation": 8,
            "life": {"center": 30, "min": 20, "max": 40},
            "location": {"x": 1.0, "y": 2.0, "z": 3.0},
            "rotation": {"x": 10.0, "y": 20.0, "z": 30.0},
            "scale": {"x": 1.5, "y": 1.5, "z": 1.5},
            "alpha_blend": "Add",
            "texture_path": "inputs/textures/smoke_color.png",
        }
    ]


def test_server_firework_burst_tool_calls_recipe(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_create_firework_burst_effect(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        return {
            "automationNodeId": "firework-root",
            "project_path": kwargs["output_project_path"],
            "effect_path": kwargs["output_effect_path"],
            "commands": [],
        }

    monkeypatch.setattr(
        server,
        "create_firework_burst_effect",
        fake_create_firework_burst_effect,
    )

    result = server.effekseer_create_firework_burst_effect(
        name="FireworkRoot",
        output_project_path="outputs/firework.efkefc",
        output_effect_path="outputs/firework.efk",
        primary_color={"r": 255, "g": 180, "b": 64, "a": 255},
        secondary_color={"r": 96, "g": 160, "b": 255, "a": 220},
        spark_count=48,
        secondary_spark_count=24,
        burst_life=45,
        secondary_life=35,
        burst_radius=80.0,
        gravity=-0.15,
        scale=1.0,
        texture_path="inputs/textures/smoke_color.png",
    )

    assert result == {
        "automationNodeId": "firework-root",
        "project_path": "outputs/firework.efkefc",
        "effect_path": "outputs/firework.efk",
        "commands": [],
    }
    assert calls == [
        {
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
            "texture_set": None,
            "textures": None,
            "visual_profile": None,
            "sample_tuning": "auto",
        }
    ]


def test_server_slash_tool_calls_recipe(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_create_slash_effect(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        return {
            "automationNodeId": "slash-root",
            "project_path": kwargs["output_project_path"],
            "effect_path": kwargs["output_effect_path"],
            "commands": [],
        }

    monkeypatch.setattr(
        server,
        "create_slash_effect",
        fake_create_slash_effect,
    )

    result = server.effekseer_create_slash_effect(
        name="SlashRoot",
        output_project_path="outputs/slash.efkefc",
        output_effect_path="outputs/slash.efk",
        primary_color={"r": 180, "g": 240, "b": 255, "a": 255},
        secondary_color={"r": 80, "g": 180, "b": 255, "a": 160},
        intensity=1.5,
        scale=1.2,
        duration=30,
        element="wind",
        texture_path="inputs/textures/smoke_color.png",
    )

    assert result == {
        "automationNodeId": "slash-root",
        "project_path": "outputs/slash.efkefc",
        "effect_path": "outputs/slash.efk",
        "commands": [],
    }
    assert calls == [
        {
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
            "texture_set": None,
            "textures": None,
            "visual_profile": None,
            "sample_tuning": "auto",
        }
    ]


def test_server_heal_sparkle_tool_calls_recipe(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_create_heal_sparkle_effect(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        return {
            "automationNodeId": "heal-root",
            "project_path": kwargs["output_project_path"],
            "effect_path": kwargs["output_effect_path"],
            "commands": [],
        }

    monkeypatch.setattr(
        server,
        "create_heal_sparkle_effect",
        fake_create_heal_sparkle_effect,
    )

    result = server.effekseer_create_heal_sparkle_effect(
        name="HealRoot",
        output_project_path="outputs/heal.efkefc",
        output_effect_path="outputs/heal.efk",
        primary_color={"r": 255, "g": 230, "b": 128, "a": 255},
        secondary_color={"r": 160, "g": 255, "b": 220, "a": 180},
        intensity=1.5,
        scale=1.2,
        duration=45,
        texture_path="inputs/textures/smoke_color.png",
    )

    assert result == {
        "automationNodeId": "heal-root",
        "project_path": "outputs/heal.efkefc",
        "effect_path": "outputs/heal.efk",
        "commands": [],
    }
    assert calls == [
        {
            "name": "HealRoot",
            "output_project_path": "outputs/heal.efkefc",
            "output_effect_path": "outputs/heal.efk",
            "primary_color": {"r": 255, "g": 230, "b": 128, "a": 255},
            "secondary_color": {"r": 160, "g": 255, "b": 220, "a": 180},
            "intensity": 1.5,
            "scale": 1.2,
            "duration": 45,
            "texture_path": "inputs/textures/smoke_color.png",
            "texture_set": None,
            "textures": None,
            "visual_profile": None,
            "sample_tuning": "auto",
        }
    ]


def test_server_elemental_burst_tool_calls_recipe(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_create_elemental_burst_effect(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        return {
            "automationNodeId": "elemental-burst-root",
            "project_path": kwargs["output_project_path"],
            "effect_path": kwargs["output_effect_path"],
            "commands": [],
        }

    monkeypatch.setattr(
        server,
        "create_elemental_burst_effect",
        fake_create_elemental_burst_effect,
    )

    result = server.effekseer_create_elemental_burst_effect(
        name="ElementalBurstRoot",
        output_project_path="outputs/elemental.efkefc",
        output_effect_path="outputs/elemental.efk",
        primary_color={"r": 255, "g": 120, "b": 48, "a": 255},
        secondary_color={"r": 128, "g": 64, "b": 255, "a": 180},
        intensity=1.5,
        scale=1.2,
        duration=40,
        element="fire",
        texture_path="inputs/textures/smoke_color.png",
    )

    assert result == {
        "automationNodeId": "elemental-burst-root",
        "project_path": "outputs/elemental.efkefc",
        "effect_path": "outputs/elemental.efk",
        "commands": [],
    }
    assert calls == [
        {
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
            "texture_set": None,
            "textures": None,
            "visual_profile": None,
            "sample_tuning": "auto",
        }
    ]


def test_server_projectile_trail_tool_calls_recipe(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_create_projectile_trail_effect(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        return {
            "automationNodeId": "projectile-root",
            "project_path": kwargs["output_project_path"],
            "effect_path": kwargs["output_effect_path"],
            "commands": [],
        }

    monkeypatch.setattr(
        server,
        "create_projectile_trail_effect",
        fake_create_projectile_trail_effect,
    )

    result = server.effekseer_create_projectile_trail_effect(
        name="ProjectileRoot",
        output_project_path="outputs/projectile.efkefc",
        output_effect_path="outputs/projectile.efk",
        primary_color={"r": 255, "g": 96, "b": 40, "a": 255},
        secondary_color={"r": 255, "g": 190, "b": 80, "a": 180},
        intensity=1.5,
        scale=1.2,
        duration=45,
        element="fire",
        texture_path="inputs/textures/smoke_color.png",
    )

    assert result == {
        "automationNodeId": "projectile-root",
        "project_path": "outputs/projectile.efkefc",
        "effect_path": "outputs/projectile.efk",
        "commands": [],
    }
    assert calls == [
        {
            "name": "ProjectileRoot",
            "output_project_path": "outputs/projectile.efkefc",
            "output_effect_path": "outputs/projectile.efk",
            "primary_color": {"r": 255, "g": 96, "b": 40, "a": 255},
            "secondary_color": {"r": 255, "g": 190, "b": 80, "a": 180},
            "intensity": 1.5,
            "scale": 1.2,
            "duration": 45,
            "element": "fire",
            "texture_path": "inputs/textures/smoke_color.png",
            "texture_set": None,
            "textures": None,
            "visual_profile": None,
            "sample_tuning": "auto",
        }
    ]


def test_server_effect_recipe_registry_tools_call_recipe_helpers(monkeypatch) -> None:
    list_calls = 0
    describe_calls: list[str] = []

    def fake_list_effect_recipes() -> list[dict[str, Any]]:
        nonlocal list_calls
        list_calls += 1
        return [{"id": "basic_sprite_burst"}]

    def fake_describe_effect_recipe(kind: str) -> dict[str, Any]:
        describe_calls.append(kind)
        return {"id": "firework_burst"}

    monkeypatch.setattr(server, "list_effect_recipes", fake_list_effect_recipes)
    monkeypatch.setattr(server, "describe_effect_recipe", fake_describe_effect_recipe)

    assert server.effekseer_list_effect_recipes() == [{"id": "basic_sprite_burst"}]
    assert server.effekseer_describe_effect_recipe("firework") == {
        "id": "firework_burst"
    }
    assert list_calls == 1
    assert describe_calls == ["firework"]


def test_server_create_effect_from_spec_tool_calls_recipe_helper(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_create_effect_from_spec(spec: dict[str, Any]) -> dict[str, Any]:
        calls.append(spec)
        return {
            "recipe": "firework_burst",
            "automationNodeId": "created",
            "project_path": spec["output_project_path"],
            "effect_path": spec["output_effect_path"],
        }

    monkeypatch.setattr(server, "create_effect_from_spec", fake_create_effect_from_spec)

    spec = {
        "kind": "firework",
        "name": "SpecFirework",
        "output_project_path": "outputs/spec_firework.efkefc",
        "output_effect_path": "outputs/spec_firework.efk",
        "primary_color": {"r": 255, "g": 180, "b": 64, "a": 255},
        "secondary_color": None,
        "intensity": 1.0,
        "scale": 1.0,
        "duration": None,
        "texture_path": None,
    }

    result = server.effekseer_create_effect_from_spec(spec)

    assert result == {
        "recipe": "firework_burst",
        "automationNodeId": "created",
        "project_path": "outputs/spec_firework.efkefc",
        "effect_path": "outputs/spec_firework.efk",
    }
    assert calls == [spec]


def test_server_sample_library_tools_call_helpers(monkeypatch) -> None:
    calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def fake_import_sample_effects(**kwargs: Any) -> dict[str, Any]:
        calls.append(("import", (), kwargs))
        return {"template_count": 1}

    def fake_list_sample_templates() -> list[dict[str, Any]]:
        calls.append(("list", (), {}))
        return [{"sample_id": "fireball"}]

    def fake_describe_sample_template(sample_id: str) -> dict[str, Any]:
        calls.append(("describe", (sample_id,), {}))
        return {"sample_id": sample_id}

    def fake_create_effect_from_sample_template(**kwargs: Any) -> dict[str, Any]:
        calls.append(("create", (), kwargs))
        return {
            "sample_id": kwargs["sample_id"],
            "project_path": kwargs["output_project_path"],
            "effect_path": kwargs["output_effect_path"],
        }

    monkeypatch.setattr(server, "import_sample_effects", fake_import_sample_effects)
    monkeypatch.setattr(server, "list_sample_templates", fake_list_sample_templates)
    monkeypatch.setattr(server, "describe_sample_template", fake_describe_sample_template)
    monkeypatch.setattr(
        server,
        "create_effect_from_sample_template",
        fake_create_effect_from_sample_template,
    )

    assert server.effekseer_import_sample_effects(repo_root="repo") == {
        "template_count": 1
    }
    assert server.effekseer_list_sample_templates() == [{"sample_id": "fireball"}]
    assert server.effekseer_describe_sample_template("fireball") == {
        "sample_id": "fireball"
    }
    assert server.effekseer_create_effect_from_sample_template(
        sample_id="fireball",
        output_project_path="outputs/fireball/fireball.efkproj",
        output_effect_path="outputs/fireball/fireball.efk",
    ) == {
        "sample_id": "fireball",
        "project_path": "outputs/fireball/fireball.efkproj",
        "effect_path": "outputs/fireball/fireball.efk",
    }
    assert calls == [
        ("import", (), {"repo_root": "repo"}),
        ("list", (), {}),
        ("describe", ("fireball",), {}),
        (
            "create",
            (),
            {
                "sample_id": "fireball",
                "output_project_path": "outputs/fireball/fireball.efkproj",
                "output_effect_path": "outputs/fireball/fireball.efk",
            },
        ),
    ]


def test_server_sample_analyzer_tools_call_helpers(monkeypatch) -> None:
    analyze_calls: list[str | None] = []
    summary_calls = 0

    def fake_analyze_sample_effects(sample_id: str | None = None) -> dict[str, Any]:
        analyze_calls.append(sample_id)
        return {"analysis_path": "outputs/sample_analysis/sample_analysis.json"}

    def fake_get_sample_analysis_summary() -> dict[str, Any]:
        nonlocal summary_calls
        summary_calls += 1
        return {"sample_count": 3}

    monkeypatch.setattr(server, "analyze_sample_effects", fake_analyze_sample_effects)
    monkeypatch.setattr(
        server,
        "get_sample_analysis_summary",
        fake_get_sample_analysis_summary,
    )

    assert server.effekseer_analyze_sample_effects("fireball") == {
        "analysis_path": "outputs/sample_analysis/sample_analysis.json"
    }
    assert server.effekseer_get_sample_analysis_summary() == {"sample_count": 3}
    assert analyze_calls == ["fireball"]
    assert summary_calls == 1

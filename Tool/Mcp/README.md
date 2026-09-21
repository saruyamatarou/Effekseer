# effekseer-mcp

Effekseer本体へ統合済みです。[INTEGRATION.md](INTEGRATION.md)を参照してください。以下は元の単体開発用ドキュメントです。

Effekseer を fork せず、ローカルの Effekseer 実行ファイル、エフェクト用 workspace、Effekseer Automation Bridge を安全に扱うための asset pipeline MCP サーバーです。

現在は read-only asset catalog と、localhost Automation Bridge への allowlist command 呼び出しを実装しています。任意 shell command 実行、任意 C# コード実行、任意 command 送信は行いません。

## Tools

基本 tool:

- `ping`
- `get_effekseer_config`
- `list_workspace_files`
- `list_assets`
- `inspect_asset`
- `list_asset_kinds`

High-level recipe tool:

- `effekseer_create_basic_sprite_burst_effect`
- `effekseer_create_firework_burst_effect`
- `effekseer_create_slash_effect`
- `effekseer_create_heal_sparkle_effect`
- `effekseer_create_elemental_burst_effect`
- `effekseer_create_projectile_trail_effect`
- `effekseer_list_effect_recipes`
- `effekseer_describe_effect_recipe`
- `effekseer_create_effect_from_spec`

Automation Bridge tool:

- `effekseer_bridge_ping`
- `effekseer_get_status`
- `effekseer_get_bridge_capabilities`
- `effekseer_get_workspace_status`
- `effekseer_save_project_to_workspace`
- `effekseer_open_project_from_workspace`
- `effekseer_export_runtime_effect_to_workspace`
- `effekseer_get_node_tree`
- `effekseer_add_node_to_selected`
- `effekseer_select_node_by_automation_id`
- `effekseer_add_node_to_parent_by_automation_id`
- `effekseer_rename_node_by_automation_id`
- `effekseer_remove_node_by_automation_id`
- `effekseer_duplicate_node_by_automation_id`
- `effekseer_insert_parent_node_by_automation_id`
- `effekseer_undo`
- `effekseer_redo`

Parameter inspection tool:

- `effekseer_get_node_basic_info_by_automation_id`
- `effekseer_get_node_parameter_groups_by_automation_id`
- `effekseer_get_node_base_parameters_by_automation_id`
- `effekseer_get_node_generation_parameters_by_automation_id`
- `effekseer_get_node_transform_parameters_by_automation_id`

Parameter write tool:

- `effekseer_set_node_is_rendered_by_automation_id`
- `effekseer_set_node_max_generation_by_automation_id`
- `effekseer_set_node_life_by_automation_id`
- `effekseer_set_node_fixed_location_by_automation_id`
- `effekseer_set_node_fixed_rotation_by_automation_id`
- `effekseer_set_node_fixed_scale_by_automation_id`
- `effekseer_set_node_generation_time_by_automation_id`
- `effekseer_set_node_location_type_by_automation_id`
- `effekseer_set_node_location_pva_by_automation_id`
- `effekseer_set_node_scale_type_by_automation_id`
- `effekseer_set_node_scale_pva_by_automation_id`
- `effekseer_set_node_fade_in_out_by_automation_id`
- `effekseer_set_node_color_all_fixed_rgba_by_automation_id`
- `effekseer_set_node_sprite_corner_colors_fixed_rgba_by_automation_id`
- `effekseer_set_node_alpha_blend_by_automation_id`
- `effekseer_set_node_z_write_by_automation_id`
- `effekseer_set_node_z_test_by_automation_id`
- `effekseer_set_node_renderer_type_by_automation_id`
- `effekseer_set_node_color_texture_from_workspace_by_automation_id`
- `effekseer_set_node_normal_texture_from_workspace_by_automation_id`
- `effekseer_clear_node_color_texture_by_automation_id`
- `effekseer_clear_node_normal_texture_by_automation_id`
- `effekseer_set_node_material_from_workspace_by_automation_id`
- `effekseer_clear_node_material_by_automation_id`
- `effekseer_set_node_model_from_workspace_by_automation_id`

Viewer control tool:

- `effekseer_play_viewer`
- `effekseer_stop_viewer`
- `effekseer_step_viewer`
- `effekseer_back_step_viewer`

## Built-in Texture Library

High-level recipes can use a generated procedural texture pack under `workspace/inputs/textures/builtin/`. These textures are transparent RGBA alpha masks in white/gray, so recipe `colorAll` controls the final color in Effekseer.

Generate or refresh the built-in pack:

```powershell
uv run python scripts/generate_builtin_textures.py
```

Generated files:

- `soft_circle.png`
- `core_glow.png`
- `spark_dot.png`
- `spark_star.png`
- `smoke_puff_01.png`
- `smoke_puff_02.png`
- `slash_arc.png`
- `ring_soft.png`
- `trail_streak.png`
- `ripple_ring.png`
- `texture_manifest.json`

`texture_manifest.json` records `id`, workspace-relative `path`, `role`, `tags`, `license`, `source`, `recommended_blend`, and notes. Built-in entries use `license: "generated_by_effekseer_mcp"` and `source: "procedural"`.

Recipe texture selection priority:

1. `textures` role overrides, such as `{"core": "inputs/textures/custom_core.png"}`
2. `texture_set`, currently `"builtin"`
3. legacy `texture_path`, applied to every node for backward compatibility
4. default built-in texture set when no texture option is provided

Supported roles are `core`, `spark`, `smoke`, `slash`, `ring`, `trail`, and `ripple`.

External texture assets must stay workspace-relative. If external or copied assets are added later, keep license/source metadata next to them or in a manifest; do not lose attribution.

## Visual Profiles

Visual Profile v0 is a recipe-level tuning layer above the built-in texture library. It does not add Bridge commands and still uses only allowlisted `EffekseerBridgeClient` methods. A profile can tune each recipe node role with:

- texture role
- recommended `alphaBlend`
- color alpha multiplier
- scale multiplier
- life multiplier
- generation multiplier
- radius multiplier
- gravity multiplier

Built-in profiles:

- `firework_default`
- `slash_wind_default`
- `heal_soft_default`
- `elemental_fire_default`
- `projectile_water_default`

Use `visual_profile` in EffectSpec or direct recipe calls:

```json
{
  "kind": "water_projectile",
  "name": "WaterShot",
  "output_project_path": "outputs/water_shot.efkefc",
  "output_effect_path": "outputs/water_shot.efk",
  "primary_color": {"r": 48, "g": 132, "b": 255, "a": 255},
  "secondary_color": {"r": 96, "g": 235, "b": 255, "a": 180},
  "intensity": 1.0,
  "scale": 1.0,
  "duration": 45,
  "texture_set": "builtin",
  "visual_profile": "projectile_water_default"
}
```

When `visual_profile` is omitted, the recipe selects a default profile from `kind` / recipe / element. Texture selection priority remains unchanged: explicit `textures` role overrides first, then `texture_set`, then legacy `texture_path`, then the default built-in texture set.

## Setup

```powershell
uv sync
Copy-Item .env.example .env
```

`.env` はローカル設定ファイルです。commit しないでください。

## Automation Bridge

Bridge tool を使うには、Effekseer 本体側に localhost JSON-line TCP Automation Bridge が必要です。

```powershell
& "C:\Program Files\Effekseer\Effekseer.exe" --automation-port 50123 --automation-workspace "D:\Documents\GitHub\effekseer-mcp\workspace"
```

Bridge 操作では `automationNodeId` を推奨識別子として使います。node の追加、削除、duplicate、parent 挿入、undo、redo などでツリー構造が変わった後は、必ず `effekseer_get_node_tree` を取り直して最新の `automationNodeId` を使ってください。

File / Project operation は Effekseer 本体側の automation workspace 配下に限定されています。MCP 側でも workspace 相対 path のみを許可し、`..` や絶対 path、対象外の拡張子は拒否します。`.efkefc` は編集用 project、`.efk` は runtime effect binary です。任意 file read、directory listing、gltf / glb export は実装していません。

## Parameter Inspection

Parameter inspection は read-only です。指定した `automationNodeId` の node について、基本情報、parameter group metadata、主要 parameter value を読みます。

Metadata:

- `effekseer_get_node_basic_info_by_automation_id`
- `effekseer_get_node_parameter_groups_by_automation_id`

Parameter value:

- `effekseer_get_node_base_parameters_by_automation_id`
- `effekseer_get_node_generation_parameters_by_automation_id`
- `effekseer_get_node_transform_parameters_by_automation_id`
- `effekseer_get_node_drawing_parameters_by_automation_id`
- `effekseer_get_node_renderer_parameters_by_automation_id`

取得対象は主要な base / generation / transform 値と、drawing / renderer common 情報です。Drawing / Renderer inspection も read-only です。texture / material / model の absolute path は返さず、summary や workspace-safe metadata として扱います。FCurve や NURBS などの参照ファイル path は展開しません。renderer write、texture assignment、texture/material import は次フェーズです。

## Parameter Write

Parameter write は手書き allowlist された基本パラメータだけに限定しています。

- `effekseer_set_node_is_rendered_by_automation_id(automation_node_id, is_rendered)`
- `effekseer_set_node_max_generation_by_automation_id(automation_node_id, max_generation)`
- `effekseer_set_node_life_by_automation_id(automation_node_id, center, min, max)`
- `effekseer_set_node_fixed_location_by_automation_id(automation_node_id, x, y, z)`
- `effekseer_set_node_fixed_rotation_by_automation_id(automation_node_id, x, y, z)`
- `effekseer_set_node_fixed_scale_by_automation_id(automation_node_id, x, y, z)`
- `effekseer_set_node_generation_time_by_automation_id(automation_node_id, center, min, max)`
- `effekseer_set_node_location_type_by_automation_id(automation_node_id, location_type)`
- `effekseer_set_node_location_pva_by_automation_id(automation_node_id, location, velocity, acceleration)`
- `effekseer_set_node_scale_type_by_automation_id(automation_node_id, scale_type)`
- `effekseer_set_node_scale_pva_by_automation_id(automation_node_id, scale, velocity, acceleration)`
- `effekseer_set_node_fade_in_out_by_automation_id(automation_node_id, fade_in_type, fade_in_frame, fade_out_type, fade_out_frame)`

`is_rendered` は boolean のみ、`max_generation` と life の `center` / `min` / `max` は integer のみ、fixed location / rotation / scale の `x` / `y` / `z` は有限の number のみ受け付けます。`bool` は integer 扱いしません。NaN / Infinity は拒否します。汎用 `set_parameter`、任意 reflection write、任意 command 送信は未対応です。

### Motion / Timing / Fade Write v1

Motion / Timing / Fade write v1 is the allowlisted setup layer for future Firework-style recipes. It updates only regular `Data.Node` values through explicit Bridge commands; root nodes are rejected by the Bridge. It does not expose generic `set_parameter`, arbitrary property names, reflection write, shell execution, C# execution, file reads, or directory listing.

- `generation_time` uses an explicit random payload: `center`, `min`, `max`.
- `location_type` accepts `Fixed` or `PVA`.
- `location` / `velocity` / `acceleration` PVA payloads are `{x:{center,min,max}, y:{center,min,max}, z:{center,min,max}}`.
- `scale_type` accepts `Fixed` or `PVA`.
- `scale` / `velocity` / `acceleration` PVA payloads use the same explicit vector random shape.
- `fade_in_type` accepts `None` or `Use`; `fade_out_type` accepts `None`, `WithinLifetime`, or `AfterRemoved`.
- All numeric inputs must be finite numbers. `bool`, `NaN`, and `Infinity` are rejected by the MCP client before Bridge transmission.
- Bridge responses include `before` / `after` plus `generationParameters`, `transformParameters`, or `rendererParameters` readback summaries. Absolute paths are not returned by these commands.

The smoke test checks write/readback, undo/redo for fade, and best-effort restore for this set.

### Drawing / Renderer Write v1

Drawing / Renderer write v1 is limited to file-reference-free visual changes:

- `effekseer_set_node_color_all_fixed_rgba_by_automation_id(automation_node_id, r, g, b, a)`
- `effekseer_set_node_sprite_corner_colors_fixed_rgba_by_automation_id(automation_node_id, lower_left, lower_right, upper_left, upper_right)`
- `effekseer_set_node_alpha_blend_by_automation_id(automation_node_id, alpha_blend)`
- `effekseer_set_node_z_write_by_automation_id(automation_node_id, z_write)`
- `effekseer_set_node_z_test_by_automation_id(automation_node_id, z_test)`
- `effekseer_set_node_renderer_type_by_automation_id(automation_node_id, renderer_type)`

RGBA channels must be integers from `0` to `255`; `bool` is rejected. `z_write` and `z_test` must be boolean. Supported `alpha_blend` values are `Opacity`, `Blend`, `Add`, `Sub`, `Mul`. Supported `renderer_type` values are `Sprite`, `Ribbon`, `Ring`, `Model`, `Track`. Texture, material, and model assignment are not implemented in this phase.

### Texture Workspace Assignment v1

Texture workspace assignment v1 assigns existing workspace-relative texture files to renderer texture slots:

- `effekseer_set_node_color_texture_from_workspace_by_automation_id(automation_node_id, path)`
- `effekseer_set_node_normal_texture_from_workspace_by_automation_id(automation_node_id, path)`
- `effekseer_clear_node_color_texture_by_automation_id(automation_node_id)`
- `effekseer_clear_node_normal_texture_by_automation_id(automation_node_id)`

The MCP side accepts only workspace-relative paths with `.png`, `.jpg`, `.jpeg`, `.tga`, `.dds`, `.bmp`, or `.gif` extensions. Absolute paths and `..` are rejected before calling the Bridge. This feature does not add arbitrary file reads, directory listing, texture content inspection, or texture copy/import. Tool and smoke-test responses must remain workspace-relative and must not include absolute local paths.

### Material Workspace Assignment v1

Material workspace assignment v1 assigns an existing workspace-relative `.efkmat` file:

- `effekseer_set_node_material_from_workspace_by_automation_id(automation_node_id, path)`
- `effekseer_clear_node_material_by_automation_id(automation_node_id)`

Only `.efkmat` paths under the configured workspace are accepted. Absolute paths and `..` are rejected before calling the Bridge. `effekseer_clear_node_material_by_automation_id` clears the material file and restores the Bridge-side material type to its default value. The smoke test runs material assignment, persistence, and clear only when `workspace/inputs/materials/smoke.efkmat` already exists; otherwise it prints a warning and skips that part. Material copy/import, directory listing, arbitrary file read, and material content inspection are not implemented.

To enable the material assignment smoke test, copy a valid Effekseer material fixture into the workspace. Do not use an empty placeholder file.

```powershell
New-Item -ItemType Directory -Force -Path workspace\inputs\materials
Copy-Item -LiteralPath ..\Effekseer\ResourceData\samples\00_Basic\Material\Emissive.efkmat -Destination workspace\inputs\materials\smoke.efkmat
```

The local smoke fixture used for development was `D:\Documents\GitHub\Effekseer\ResourceData\samples\00_Basic\Material\Emissive.efkmat`. The copied file is intentionally kept under `workspace/inputs/materials/` and Bridge responses must still use the workspace-relative path `inputs/materials/smoke.efkmat`, not the absolute source path.

### Model Workspace Assignment v1

Model workspace assignment v1 assigns an existing workspace-relative `.efkmodel` file and switches the target node renderer type to `Model`:

- `effekseer_set_node_model_from_workspace_by_automation_id(automation_node_id, path)`

Only `.efkmodel` paths under the configured workspace are accepted. Absolute paths and `..` are rejected before calling the Bridge. The smoke test runs model assignment only when `workspace/inputs/models/smoke.efkmodel` already exists; otherwise it prints a warning and skips that part. Model copy/import, model editing, gltf/glb export, directory listing, and arbitrary file read are not implemented.

To enable the model assignment smoke test, copy a valid Effekseer model fixture into the workspace. Do not use an empty placeholder file.

```powershell
New-Item -ItemType Directory -Force -Path workspace\inputs\models
Copy-Item -LiteralPath ..\Effekseer\Dev\Cpp\Test\Resource\Model\block.efkmodel -Destination workspace\inputs\models\smoke.efkmodel
```

The local smoke fixture used for development was `D:\Documents\GitHub\Effekseer\Dev\Cpp\Test\Resource\Model\block.efkmodel`. The copied file is intentionally kept under `workspace/inputs/models/` and Bridge responses must still use the workspace-relative path `inputs/models/smoke.efkmodel`, not the absolute source path.

## Runtime Export

Runtime export は workspace 相対 `.efk` path のみを受け付けます。

- `effekseer_export_runtime_effect_to_workspace(path)`

編集用 project を保存・読込する場合は `.efkefc`、ゲームや runtime 側で使う binary effect を出力する場合は `.efk` を使います。

## High-level Recipes

`effekseer_create_basic_sprite_burst_effect` creates a practical minimal sprite burst effect without requiring the caller to orchestrate every low-level Bridge command.

Inputs:

- `name`
- `output_project_path`: workspace-relative `.efkefc`
- `output_effect_path`: workspace-relative `.efk`
- `color`: `{r,g,b,a}`
- `max_generation`
- `life`: `{center,min,max}`
- `location`: `{x,y,z}`
- `rotation`: `{x,y,z}`
- `scale`: `{x,y,z}`
- `alpha_blend`: defaults to `Add`
- `texture_path`: optional workspace-relative texture path

The recipe adds a node under root, names it, sets Sprite renderer parameters, writes maxGeneration/life/fixed location/fixed rotation/fixed scale/color/alphaBlend, optionally assigns a color texture, saves the project, and exports the runtime `.efk`. It uses only the existing allowlisted low-level Bridge client methods. Output paths and optional texture paths are validated by the same workspace-relative path validation used by the low-level tools. If the recipe fails after creating a node, it attempts to remove that node as best-effort cleanup.

`effekseer_create_firework_burst_effect` is a natural-language-facing recipe for requests like "create a firework-like effect." It creates a small node hierarchy:

```text
FireworkRoot
|- BurstCore
|- BurstSparks
`- SecondarySparkles
```

Inputs:

- `name`: top-level firework root node name; use `FireworkRoot` for the canonical structure
- `output_project_path`: workspace-relative `.efkefc`
- `output_effect_path`: workspace-relative `.efk`
- `primary_color`: `{r,g,b,a}`
- `secondary_color`: `{r,g,b,a}`
- `spark_count`: defaults to `48`
- `secondary_spark_count`: defaults to `24`
- `burst_life`: defaults to `45`
- `secondary_life`: defaults to `35`
- `burst_radius`: defaults to `80.0`
- `gravity`: defaults to `-0.15`
- `scale`: defaults to `1.0`
- `texture_path`: optional workspace-relative texture path assigned to all three sprite nodes

The Firework recipe uses only existing `EffekseerBridgeClient` methods. It adds no new Bridge command, performs no shell execution, reads no arbitrary files, and relies on the existing workspace-relative validation for project/effect output paths and optional texture assignment. If recipe execution fails after creating the top-level firework node, it attempts to remove that node as best-effort cleanup.

`effekseer_create_slash_effect` is a natural-language-facing recipe for requests like "slash", "wind blade", "fire slash", or "kama-itachi." It creates a small node hierarchy:

```text
SlashRoot
|- SlashArc
|- ImpactSparks
`- AfterimageParticles
```

Inputs:

- `name`: top-level slash root node name; use `SlashRoot` for the canonical structure
- `output_project_path`: workspace-relative `.efkefc`
- `output_effect_path`: workspace-relative `.efk`
- `primary_color`: `{r,g,b,a}`
- `secondary_color`: optional `{r,g,b,a}`; when omitted the afterimage uses a faded primary color
- `intensity`: defaults to `1.0`; controls spark counts and spread
- `scale`: defaults to `1.0`
- `duration`: defaults to `30`
- `element`: one of `neutral`, `wind`, `fire`, `water`, `dark`, `holy`
- `texture_path`: optional workspace-relative texture path assigned to all three sprite nodes

The Slash recipe uses only existing `EffekseerBridgeClient` methods and `recipe_primitives`. It adds no new Bridge command, performs no shell execution, reads no arbitrary files, and relies on the existing workspace-relative validation for project/effect output paths and optional texture assignment. If recipe execution fails after creating the top-level slash node, it attempts to remove that node as best-effort cleanup.

`effekseer_create_heal_sparkle_effect` is a natural-language-facing recipe for requests like "heal", "recovery magic", "holy light", or "golden healing effect." It creates a small node hierarchy:

```text
HealRoot
|- SoftGlowCore
|- UpwardSparkles
`- HealingRing
```

Inputs:

- `name`: top-level heal root node name; use `HealRoot` for the canonical structure
- `output_project_path`: workspace-relative `.efkefc`
- `output_effect_path`: workspace-relative `.efk`
- `primary_color`: `{r,g,b,a}`
- `secondary_color`: optional `{r,g,b,a}`; when omitted sparkle/ring nodes use a faded primary color
- `intensity`: defaults to `1.0`; controls sparkle count, height, and ring radius
- `scale`: defaults to `1.0`
- `duration`: defaults to `45`
- `texture_path`: optional workspace-relative texture path assigned to all three sprite nodes

The Heal Sparkle recipe uses only existing `EffekseerBridgeClient` methods and `recipe_primitives`. It adds no new Bridge command, performs no shell execution, reads no arbitrary files, and relies on the existing workspace-relative validation for project/effect output paths and optional texture assignment. If recipe execution fails after creating the top-level heal node, it attempts to remove that node as best-effort cleanup.

`effekseer_create_elemental_burst_effect` is a general-purpose elemental recipe for requests like "fire", "water magic", "wind spell", "dark explosion", or "holy burst." It creates a small node hierarchy:

```text
ElementalBurstRoot
|- CoreGlow
|- ElementSparks
`- ResidualParticles
```

Inputs:

- `name`: top-level elemental root node name; use `ElementalBurstRoot` for the canonical structure
- `output_project_path`: workspace-relative `.efkefc`
- `output_effect_path`: workspace-relative `.efk`
- `primary_color`: `{r,g,b,a}`
- `secondary_color`: optional `{r,g,b,a}`; when omitted residual particles use a faded primary color
- `intensity`: defaults to `1.0`; controls spark counts and burst radius
- `scale`: defaults to `1.0`
- `duration`: defaults to `40`
- `element`: one of `neutral`, `fire`, `water`, `wind`, `dark`, `holy`
- `texture_path`: optional workspace-relative texture path assigned to all three sprite nodes

The Elemental Burst recipe uses only existing `EffekseerBridgeClient` methods and `recipe_primitives`. It adds no new Bridge command, performs no shell execution, reads no arbitrary files, and relies on the existing workspace-relative validation for project/effect output paths and optional texture assignment. Element choices adjust only allowlisted recipe parameters such as scale, radius, life, gravity, and spark counts. If recipe execution fails after creating the top-level elemental node, it attempts to remove that node as best-effort cleanup.

`effekseer_create_projectile_trail_effect` is a natural-language-facing recipe for requests like "fireball", "water projectile", "magic bullet", "wind projectile", or "dark projectile." It creates a small node hierarchy:

```text
ProjectileRoot
|- ProjectileCore
|- TrailParticles
`- ImpactSparks
```

Inputs:

- `name`: top-level projectile root node name; use `ProjectileRoot` for the canonical structure
- `output_project_path`: workspace-relative `.efkefc`
- `output_effect_path`: workspace-relative `.efk`
- `primary_color`: `{r,g,b,a}`
- `secondary_color`: optional `{r,g,b,a}`; when omitted trail particles use a faded primary color
- `intensity`: defaults to `1.0`; controls trail/impact particle counts and spread
- `scale`: defaults to `1.0`
- `duration`: defaults to `45`
- `element`: one of `neutral`, `fire`, `water`, `wind`, `dark`, `holy`
- `texture_path`: optional workspace-relative texture path assigned to all three sprite nodes

The Projectile Trail recipe uses only existing `EffekseerBridgeClient` methods and `recipe_primitives`. It adds no new Bridge command, performs no shell execution, reads no arbitrary files, and relies on the existing workspace-relative validation for project/effect output paths and optional texture assignment. Element choices adjust only allowlisted recipe parameters such as core scale, trail life, gravity, velocity, and spark counts. If recipe execution fails after creating the top-level projectile node, it attempts to remove that node as best-effort cleanup.

### EffectSpec v0

EffectSpec v0 is a structured routing layer for callers that already interpreted natural language outside this MCP server. It does not add new Bridge commands; it maps a small allowlisted spec into existing high-level recipes.

Tools:

- `effekseer_list_effect_recipes`: list supported recipe ids and accepted EffectSpec kinds.
- `effekseer_describe_effect_recipe(kind)`: describe `basic_sprite_burst`, `firework_burst`, `slash`, `heal_sparkle`, `elemental_burst`, `projectile_trail`, or a supported kind alias such as `firework`.
- `effekseer_create_effect_from_spec(spec)`: validate and route an EffectSpec v0 payload.

Supported routing:

- `kind: "basic_sprite_burst"` -> `effekseer_create_basic_sprite_burst_effect`
- `kind: "firework"` or `"firework_burst"` -> `effekseer_create_firework_burst_effect`
- `kind: "slash"`, `"wind_slash"`, or `"fire_slash"` -> `effekseer_create_slash_effect`
- `kind: "heal"`, `"heal_sparkle"`, or `"holy_heal"` -> `effekseer_create_heal_sparkle_effect`
- `kind: "elemental_burst"`, `"fire"`, `"water"`, `"wind"`, `"dark"`, or `"holy"` -> `effekseer_create_elemental_burst_effect`
- `kind: "projectile"`, `"projectile_trail"`, `"fireball"`, `"water_projectile"`, `"wind_projectile"`, `"dark_projectile"`, or `"holy_projectile"` -> `effekseer_create_projectile_trail_effect`

EffectSpec v0 shape:

```json
{
  "kind": "firework",
  "name": "FireworkRoot",
  "output_project_path": "outputs/firework.efkefc",
  "output_effect_path": "outputs/firework.efk",
  "primary_color": {"r": 255, "g": 180, "b": 64, "a": 255},
  "secondary_color": {"r": 96, "g": 160, "b": 255, "a": 220},
  "intensity": 1.0,
  "scale": 1.0,
  "duration": 45,
  "texture_path": null,
  "sample_tuning": "auto"
}
```

`intensity` is converted into recipe-specific counts and radius values. For `basic_sprite_burst`, it controls `max_generation`; for `firework`, it controls spark counts and burst radius; for `slash`, it controls impact spark count and spread; for `heal_sparkle`, it controls upward sparkle count, height, and ring radius; for `elemental_burst`, it controls elemental spark counts and radius; for `projectile_trail`, it controls trail/impact particle counts and spread. `duration` maps to life values when provided. `sample_tuning` may be `"auto"`, `"off"`, `null`, or an object with conservative override multipliers; `"auto"` and `null` use Sample-guided tuning when available and otherwise use a safe fallback. `secondary_color` may be `null`; firework routing then reuses `primary_color`, slash routing uses a faded primary color for afterimages, heal routing uses a faded primary color for sparkles/ring, elemental routing uses a faded primary color for residual particles, and projectile routing uses a faded primary color for trail particles. Slash kinds infer an element when `element` is omitted: `slash` -> `neutral`, `wind_slash` -> `wind`, `fire_slash` -> `fire`. Elemental kinds infer an element when `element` is omitted: `fire` -> `fire`, `water` -> `water`, `wind` -> `wind`, `dark` -> `dark`, `holy` -> `holy`, and `elemental_burst` -> `fire`. Projectile kinds infer an element when `element` is omitted: `fireball` -> `fire`, `water_projectile` -> `water`, `wind_projectile` -> `wind`, `dark_projectile` -> `dark`, `holy_projectile` -> `holy`, and `projectile` / `projectile_trail` -> `fire`. Output paths and optional texture paths remain workspace-relative and are validated by the existing low-level Bridge client methods.

### Recipe Visual Smoke

`scripts/smoke_recipes.py` runs representative EffectSpec recipes against a live Effekseer Automation Bridge and writes reviewable `.efkefc` / `.efk` outputs under `workspace/outputs/recipe_smoke_<run_id>/`.

Start Effekseer with the Automation Bridge and workspace first:

```powershell
.\Dev\release\Effekseer.exe --automation-port 50123 --automation-workspace D:\Documents\GitHub\effekseer-mcp\workspace
```

Generate the recipe smoke outputs:

```powershell
uv run python scripts/smoke_recipes.py
```

Disable sample-guided tuning for comparison:

```powershell
uv run python scripts/smoke_recipes.py --no-sample-tuning
```

The script creates:

- `firework_burst.efkefc` / `firework_burst.efk`
- `wind_slash.efkefc` / `wind_slash.efk`
- `holy_heal.efkefc` / `holy_heal.efk`
- `elemental_fire.efkefc` / `elemental_fire.efk`
- `water_projectile.efkefc` / `water_projectile.efk`
- `manifest.json`
- `REVIEW.md`

Each generated project is saved/exported as a standalone effect. After a recipe succeeds, `smoke_recipes.py` removes that recipe's top-level smoke node from the live editor project before generating the next case. It also best-effort removes only the fixed visual-smoke node names (`SmokeFirework`, `SmokeWindSlash`, `SmokeHolyHeal`, `SmokeElementalFire`, `SmokeWaterProjectile`) at startup.

For interactive visual review:

```powershell
uv run python scripts/smoke_recipes.py --visual
```

With `--visual`, the script stops the viewer, opens each generated `.efkefc` via `open_project_from_workspace`, stops again to clear prior playback state, calls `play_viewer`, prints the review prompt, waits for Enter, and stops the viewer before moving to the next effect. The review checklist covers:

- Firework: 中心から粒子が広がるか
- Wind Slash: 斜めの斬撃と小さい粒子が見えるか
- Holy Heal: 柔らかい光、上昇する粒子、リングが見えるか
- Elemental Fire: 中心光と火属性っぽい粒子が見えるか
- Water Projectile: 弾の中心、軌跡、着弾粒子が見えるか

This workflow uses only existing `EffekseerBridgeClient` methods and EffectSpec routing. It does not add Bridge commands, does not read arbitrary files, and keeps all generated outputs workspace-relative. High-level recipe container nodes such as `FireworkRoot`, `SlashRoot`, `HealRoot`, `ElementalBurstRoot`, and `ProjectileRoot` are marked non-rendered so only their child effect nodes draw.

### SampleEffects Template Library

SampleEffects Template Library v0 imports repo-local `SampleEffects` into the MCP workspace as official-sample-derived template assets. It is useful when hand-authored high-level recipes are not visually rich enough yet.

Tools:

- `effekseer_import_sample_effects(repo_root=None)`: copy `SampleEffects` into `workspace/samples/sample_effects` and write `sample_manifest.json`.
- `effekseer_list_sample_templates()`: list imported template entries.
- `effekseer_describe_sample_template(sample_id)`: describe one template.
- `effekseer_create_effect_from_sample_template(sample_id, output_project_path, output_effect_path)`: copy the template and related assets into `workspace/outputs`, open the project, and export runtime `.efk`.

Import samples:

```powershell
uv run python -c "from effekseer_mcp.sample_library import import_sample_effects; import_sample_effects()"
```

Smoke/export representative samples:

```powershell
uv run python scripts/smoke_sample_templates.py
```

Interactive visual review:

```powershell
uv run python scripts/smoke_sample_templates.py --visual
```

The sample smoke uses representative templates such as `fireball`, `magicheal1`, `magicwater`, `magicthunder`, and `attack1` when available. With `--visual`, it stops the viewer, opens each generated `.efkproj`, stops again, plays the viewer, waits for Enter, and stops before moving on.

`.efkproj` is treated as a legacy/open-only project format. `open_project_from_workspace` accepts workspace-relative `.efkefc` and `.efkproj`; `save_project_to_workspace` remains `.efkefc` only. Runtime export remains `.efk`.

Security boundary:

- Source input is the fixed repo-local `SampleEffects` directory.
- MCP runtime paths are limited to `workspace/samples` and `workspace/outputs`.
- Returned paths are workspace-relative; absolute paths are not returned.
- The workflow does not add Bridge commands, arbitrary file reads, directory-listing tools, or shell execution.

Use high-level recipes when you want parametric AI-generated effects. Use sample templates when you want to start from known Effekseer sample assets and export/review them through the same workspace-safe bridge path.

### Sample Analyzer

Sample Analyzer v0 parses imported `workspace/samples/sample_effects/*.efkproj` XML and extracts practical ranges from official samples. It is read-only against imported sample projects and is meant to provide tuning data for custom recipes: life, generation count, timing, velocity, scale, renderer type, alphaBlend, texture/model/sound references, and fade frames.

Run analysis:

```powershell
uv run python scripts/analyze_sample_effects.py
```

Analyze one sample:

```powershell
uv run python scripts/analyze_sample_effects.py --sample-id fireball
```

Outputs:

- `workspace/outputs/sample_analysis/sample_analysis.json`
- `workspace/outputs/sample_analysis/sample_analysis.md`

MCP tools:

- `effekseer_analyze_sample_effects(sample_id=None)`
- `effekseer_get_sample_analysis_summary()`

The analyzer reads only `workspace/samples/sample_effects/sample_manifest.json` and `.efkproj` files under `workspace/samples/sample_effects`. Unknown XML elements are ignored. Broken XML files are recorded in `errors` and the batch continues. Output paths and project paths in the generated analysis remain workspace-relative.

### Sample-guided Recipe Tuning

Sample-guided Recipe Tuning v0 uses `workspace/outputs/sample_analysis/sample_analysis.json` as a conservative baseline for procedural recipes. It nudges high-level recipe values such as `burst_radius`, velocity factors, scale, life, and generation counts toward the category medians/ranges extracted from official SampleEffects, so generated particles are less likely to fly off-screen in a single frame.

Recommended flow:

```powershell
uv run python scripts/analyze_sample_effects.py
uv run python scripts/smoke_recipes.py --visual
```

Supported recipe tuning inputs:

- `sample_tuning: "auto"` or `null`: use sample analysis if present, otherwise use safe fallback limits.
- `sample_tuning: "off"`: keep the recipe's raw procedural values.
- `sample_tuning: {"mode":"auto","radius_multiplier":0.25,"velocity_multiplier":0.2}`: use explicit conservative multipliers while still reporting baseline metadata.

Category mapping is intentionally narrow: firework uses `magic` / `fire`, slash uses `hit` / `impact`, heal uses `heal` / `holy`, elemental recipes use their element category, and projectile recipes prefer `projectile` with an element fallback. Recipe smoke manifests and `REVIEW.md` include the selected tuning category, baseline source, and applied radius/velocity multipliers.

## Smoke Test

Effekseer を Bridge 付きで起動した状態で、Bridge 操作の end-to-end smoke test を実行できます。

```powershell
uv run python scripts/smoke_bridge.py
```

smoke test は run ごとにユニークな `SmokeTestRoot_<run_id>` を作り、その配下だけで node lifecycle を確認します。最後に作成した root を削除し、その run の smoke node が残っていないことを確認します。

smoke test の冒頭では `get_bridge_capabilities` を呼び、必要な Bridge command がすべて揃っているか確認します。`unknown command` や不足 command のエラーが出る場合は、Effekseer 本体側の Automation Bridge が古い可能性があるため、Effekseer.exe を再ビルドして再起動してください。

確認内容:

- `ping`
- `get_status`
- `get_bridge_capabilities`
- `get_workspace_status`
- `get_node_tree`
- add / rename / duplicate / insert parent / remove / undo / redo
- basic info / parameter groups / base values / generation values / transform values / drawing values / renderer values の read-only inspection
- inspection 前後で node tree 構造が変わらないこと
- `set_node_is_rendered_by_automation_id` の write / undo / redo / restore
- basic parameter write: maxGeneration / life / fixed location / fixed rotation / fixed scale
- basic parameter write の undo / redo / restore
- motion / timing / fade write v1: generationTime / location PVA / scale PVA / fade in-out
- motion / timing / fade write v1 の readback / undo / redo / restore
- drawing / renderer write v1: colorAll / sprite corner colors / alphaBlend / zWrite / zTest / rendererType / undo / redo / restore
- texture workspace assignment v1: colorTexture / normalTexture assignment / clear readback
- material workspace assignment / persistence / clear when `inputs/materials/smoke.efkmat` exists
- model workspace assignment v1 when `inputs/models/smoke.efkmodel` exists
- viewer control: play / step / stop / back step
- resource persistence project save/open: `outputs/smoke_resource_<run_id>.efkefc`
- resource persistence runtime export: `outputs/smoke_resource_<run_id>.efk`
- best-effort cleanup

smoke test は保存した `outputs/smoke_<run_id>.efkefc` を再度 open し、open 後に `get_node_tree` が成功することを確認します。その後、`outputs/smoke_<run_id>.efk` へ runtime export し、返却された path と byte count を確認します。保存・export した smoke file を削除する Bridge command はまだないため、不要になった smoke file は手動削除してください。後続フェーズで workspace cleanup command を追加する想定です。

## Workspace

workspace 配下には以下の標準ディレクトリを作成・利用します。

- `workspace/inputs`
- `workspace/outputs`
- `workspace/temp`

`list_assets` は、ファイル内容を読まずに拡張子とファイルサイズだけで分類します。返却される `relative_path` は必ず workspace 相対パスです。

## Security Policy

- workspace 外のファイル読み書きは禁止
- `../` による workspace 外アクセスは禁止
- workspace 外を指す絶対パスは禁止
- tool の返却値に絶対パスを含めない
- asset catalog ではファイル内容の読み込みをしない
- asset catalog ではハッシュ計算をしない
- 任意 shell command 実行は禁止
- 任意 C# コード実行は禁止
- parameter write は明示的な手書き allowlist command のみに限定
- 汎用 `set_parameter` や任意 reflection write は未実装
- Drawing / Renderer write と texture assignment は未実装
- texture/material import は未実装
- project save/open は workspace 相対 `.efkefc` のみに限定
- runtime export は workspace 相対 `.efk` のみに限定
- arbitrary file read / directory listing / gltf / glb export は未実装
- Bridge 接続先 host は `127.0.0.1` 固定
- Bridge command は allowlist された最小コマンドのみ

- Drawing / Renderer write v1 is limited to explicit allowlisted scalar/color changes
- Texture workspace assignment v1 is limited to workspace-relative existing texture paths
- absolute paths are rejected and must not be returned by texture assignment responses
- Material workspace assignment v1 is limited to workspace-relative existing `.efkmat` paths
- Model workspace assignment v1 is limited to workspace-relative existing `.efkmodel` paths
- copy/import / directory listing / arbitrary file read are not implemented

## Development

```powershell
uv run ruff check .
uv run pytest
```

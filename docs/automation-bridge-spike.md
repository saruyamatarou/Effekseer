# Automation Bridge spike

This spike adds a minimal, opt-in automation bridge for controlling a running Effekseer Editor from a local external process.

## Scope

- Disabled by default.
- Binds only to `127.0.0.1`.
- Enabled by `--automation-port <port>` or `EFFEKSEER_AUTOMATION_PORT=<port>`.
- Uses JSON-line TCP: one JSON object per line, one JSON object response per line.
- Allows only explicit commands: `ping`, `get_status`, `get_node_tree`, `add_node_to_selected`, `select_node_by_id`, `add_node_to_parent`, `rename_node`, `select_node_by_automation_id`, `add_node_to_parent_by_automation_id`, `rename_node_by_automation_id`, `remove_node_by_automation_id`, `duplicate_node_by_automation_id`, `insert_parent_node_by_automation_id`, `undo`, `redo`, `play_viewer`, `stop_viewer`, `step_viewer`, `back_step_viewer`, `get_node_basic_info_by_automation_id`, and `get_node_parameter_groups_by_automation_id`.
- Does not execute shell commands or arbitrary C# code.
- Does not use UI clicks or GUI automation.

## Relevant files

- `Dev/Editor/Effekseer/Program.cs`
  - Main entry point.
  - Parses `--automation-port`.
  - Reads `EFFEKSEER_AUTOMATION_PORT`.
- `Dev/Editor/Effekseer/App.cs`
  - Editor application subclass.
  - Starts and stops the bridge.
  - Calls `AutomationBridge.Update()` from `OnUpdate()`.
- `Dev/Editor/Effekseer/AutomationBridge.cs`
  - Localhost TCP listener and JSON-line command handling.
  - Network/client tasks enqueue commands.
  - Main/UI thread executes queued commands during `OnUpdate()`.
- `Dev/Editor/EffekseerCoreGUI/Application.cs`
  - Main loop: `GUI.Manager.Update(); OnUpdate();`.
- `Dev/Editor/EffekseerCore/Data/NodeBase.cs`
  - `AddChild()` creates a child node through the command manager.
- `Dev/Editor/EffekseerCoreGUI/GUI/Commands.cs`
  - Existing `AddNode()` behavior checks the selected node and node layer limit.
- `Dev/Editor/EffekseerCore/Core.cs`
  - `Core.SelectedNode` stores the editor selection and raises selection change events.

## Threading model

The TCP listener and per-client readers run on background tasks. They never mutate `Core.SelectedNode` or node data directly. Parsed and allowlisted commands are pushed into a concurrent queue. The editor main loop calls `AutomationBridge.Update()` from `App.OnUpdate()`, and that method executes the command on the main/UI thread and completes the waiting response task.

This keeps editing operations on the same thread as normal editor updates.

## Existing IPC/network comparison

The existing Network panel is an editor-side client for sending effect data to an external runtime/viewer. It stores a target address and port, auto-connects, updates the native network client, sends effect binary data, and supports profiling.

For automation, extending that path would mix two different responsibilities:

- existing Network: editor-to-runtime data transfer and profiling
- automation bridge: external-controller-to-editor edit commands

A separate bridge is smaller for this spike and avoids changing existing network behavior.

## Commands

Requests support an optional `params` object. Existing requests without `params` remain valid and are treated as if `params` were `{}`.

```json
{"command":"ping"}
```

```json
{"command":"select_node_by_id","params":{"editorNodeId":1}}
```

`editorNodeId` remains in responses because Effekseer already exposes it internally, but MCP clients should prefer `automationNodeId` for edit operations. `automationNodeId` is generated from the current node tree path:

- Root: `0`
- Root's first child: `0/0`
- Root's second child: `0/1`
- First child under `0/1`: `0/1/0`

Because this is a path ID, clients should refresh it with `get_node_tree` after structural edits that can change sibling indexes. This includes add, remove, duplicate, and insert-parent operations.

### ping

Request:

```json
{"command":"ping"}
```

Response:

```json
{"ok":true,"command":"ping","result":{"message":"pong"}}
```

### get_status

Request:

```json
{"command":"get_status"}
```

Response shape:

```json
{"ok":true,"command":"get_status","result":{"running":true,"has_selected_node":true,"selected_node":{"automationNodeId":"0/0","name":"Node","editor_node_id":0,"children_count":0}}}
```

`editor_node_id` can be `0` before the editor/exporter assigns stable IDs.

### add_node_to_selected

Request:

```json
{"command":"add_node_to_selected"}
```

If no node is selected:

```json
{"ok":false,"command":"add_node_to_selected","error":"selected node is not found"}
```

If a node is selected:

```json
{"ok":true,"command":"add_node_to_selected","result":{"selected_node":{"automationNodeId":"0/0","name":"Node","editor_node_id":0,"children_count":1},"added_node":{"automationNodeId":"0/0/0","name":"Node","editor_node_id":0,"children_count":0}}}
```

### get_node_tree

Request:

```json
{"command":"get_node_tree"}
```

Response shape:

```json
{"ok":true,"command":"get_node_tree","result":{"root":{"automationNodeId":"0","editorNodeId":0,"name":"Root","isSelected":false,"childCount":1,"children":[{"automationNodeId":"0/0","editorNodeId":0,"name":"Node","isSelected":true,"childCount":0,"children":[]}]}}}
```

The response contains only editor node metadata needed by automation clients. It does not include project paths, resource paths, or other local filesystem information.

### select_node_by_id

Request:

```json
{"command":"select_node_by_id","params":{"editorNodeId":1}}
```

If the node is found, the editor selection is updated on the main/UI thread:

```json
{"ok":true,"command":"select_node_by_id","result":{"selected_node":{"automationNodeId":"0/0","name":"Node","editor_node_id":1,"children_count":0}}}
```

If the node is not found:

```json
{"ok":false,"command":"select_node_by_id","error":"node is not found"}
```

### add_node_to_parent

Request:

```json
{"command":"add_node_to_parent","params":{"parentEditorNodeId":1,"name":"Child"}}
```

`params.name` is optional. If present, it must be non-empty and 128 characters or less.

Response shape:

```json
{"ok":true,"command":"add_node_to_parent","result":{"parent_node":{"automationNodeId":"0/0","name":"Node","editor_node_id":1,"children_count":1},"added_node":{"automationNodeId":"0/0/0","name":"Child","editor_node_id":0,"children_count":0}}}
```

If the parent is not found:

```json
{"ok":false,"command":"add_node_to_parent","error":"parent node is not found"}
```

### rename_node

Request:

```json
{"command":"rename_node","params":{"editorNodeId":1,"name":"Renamed"}}
```

`params.name` must be non-empty and 128 characters or less. Renaming the root node is currently rejected.

Response shape:

```json
{"ok":true,"command":"rename_node","result":{"renamed_node":{"automationNodeId":"0/0","name":"Renamed","editor_node_id":1,"children_count":0}}}
```

If the root node is targeted:

```json
{"ok":false,"command":"rename_node","error":"root node cannot be renamed"}
```

### select_node_by_automation_id

Request:

```json
{"command":"select_node_by_automation_id","params":{"automationNodeId":"0/0"}}
```

Response shape:

```json
{"ok":true,"command":"select_node_by_automation_id","result":{"selected_node":{"automationNodeId":"0/0","name":"Node","editor_node_id":0,"children_count":0}}}
```

Invalid paths, out-of-range indexes, and missing nodes return an error:

```json
{"ok":false,"command":"select_node_by_automation_id","error":"automationNodeId index is out of range"}
```

### add_node_to_parent_by_automation_id

Request:

```json
{"command":"add_node_to_parent_by_automation_id","params":{"parentAutomationNodeId":"0/0","name":"Child"}}
```

`params.name` is optional. If present, it must be non-empty and 128 characters or less.

Response shape:

```json
{"ok":true,"command":"add_node_to_parent_by_automation_id","result":{"parent_node":{"automationNodeId":"0/0","name":"Node","editor_node_id":0,"children_count":1},"added_node":{"automationNodeId":"0/0/0","name":"Child","editor_node_id":0,"children_count":0}}}
```

### rename_node_by_automation_id

Request:

```json
{"command":"rename_node_by_automation_id","params":{"automationNodeId":"0/0","name":"Renamed"}}
```

Response shape:

```json
{"ok":true,"command":"rename_node_by_automation_id","result":{"renamed_node":{"automationNodeId":"0/0","name":"Renamed","editor_node_id":0,"children_count":0}}}
```

### remove_node_by_automation_id

Request:

```json
{"command":"remove_node_by_automation_id","params":{"automationNodeId":"0/1"}}
```

The root node cannot be removed. The response includes the parent after removal and a payload captured for the node before removal:

```json
{"ok":true,"command":"remove_node_by_automation_id","result":{"parent_node":{"automationNodeId":"0","name":"Root","editor_node_id":0,"children_count":1},"removed_node":{"automationNodeId":"0/1","name":"Node","editor_node_id":0,"children_count":0}}}
```

After removal, the removed node's `automationNodeId` is invalid, and sibling path indexes may have changed. Call `get_node_tree` before issuing more path-based edits.

### duplicate_node_by_automation_id

Request:

```json
{"command":"duplicate_node_by_automation_id","params":{"automationNodeId":"0/1","name":"Copy"}}
```

The root node cannot be duplicated. Duplication uses Effekseer's existing internal `Core.Copy(node)` and `Core.Paste(newNode, data)` XML copy/paste mechanism, not UI clipboard automation. The duplicate is appended to the same parent. `params.name` is optional; if present, it must be non-empty and 128 characters or less.

Response shape:

```json
{"ok":true,"command":"duplicate_node_by_automation_id","result":{"parent_node":{"automationNodeId":"0","name":"Root","editor_node_id":0,"children_count":3},"duplicated_node":{"automationNodeId":"0/2","name":"Copy","editor_node_id":0,"children_count":0}}}
```

Because the duplicate is appended and the tree shape changes, call `get_node_tree` before issuing more path-based edits.

### insert_parent_node_by_automation_id

Request:

```json
{"command":"insert_parent_node_by_automation_id","params":{"automationNodeId":"0/1","name":"Wrapper"}}
```

The root node cannot be wrapped. This uses the existing `node.InsertParent()` operation. The inserted parent takes the original path and the moved node becomes its first child.

Response shape:

```json
{"ok":true,"command":"insert_parent_node_by_automation_id","result":{"inserted_node":{"automationNodeId":"0/1","name":"Wrapper","editor_node_id":0,"children_count":1},"moved_node":{"automationNodeId":"0/1/0","name":"Node","editor_node_id":0,"children_count":0}}}
```

After this operation, descendant `automationNodeId` values can change. Call `get_node_tree` before issuing more path-based edits.

### undo

Request:

```json
{"command":"undo"}
```

Response shape:

```json
{"ok":true,"command":"undo","result":{"status":{"running":true,"has_selected_node":true,"selected_node":{"automationNodeId":"0/0","name":"Node","editor_node_id":0,"children_count":0}}}}
```

If there is nothing to undo:

```json
{"ok":false,"command":"undo","error":"nothing to undo"}
```

### redo

Request:

```json
{"command":"redo"}
```

Response shape:

```json
{"ok":true,"command":"redo","result":{"status":{"running":true,"has_selected_node":true,"selected_node":{"automationNodeId":"0/0","name":"Node","editor_node_id":0,"children_count":0}}}}
```

If there is nothing to redo:

```json
{"ok":false,"command":"redo","error":"nothing to redo"}
```

## Viewer commands

Viewer commands control playback in the Effekseer Editor viewer. They do not edit effect data and do not use GUI clicks or UI automation. The bridge reuses the existing editor command methods: `Effekseer.GUI.Commands.Play`, `Stop`, `Step`, and `BackStep`.

### play_viewer

Request:

```json
{"command":"play_viewer"}
```

Response shape:

```json
{"ok":true,"command":"play_viewer","result":{"running":true,"viewer":{"is_playing":true,"is_paused":false},"status":{"running":true,"has_selected_node":true,"selected_node":{"automationNodeId":"0/0","name":"Node","editor_node_id":0,"children_count":0}}}}
```

### stop_viewer

Request:

```json
{"command":"stop_viewer"}
```

Response shape:

```json
{"ok":true,"command":"stop_viewer","result":{"running":true,"viewer":{"is_playing":false,"is_paused":false},"status":{"running":true,"has_selected_node":true,"selected_node":{"automationNodeId":"0/0","name":"Node","editor_node_id":0,"children_count":0}}}}
```

### step_viewer

Request:

```json
{"command":"step_viewer"}
```

Response shape:

```json
{"ok":true,"command":"step_viewer","result":{"running":true,"viewer":{"is_playing":true,"is_paused":true},"status":{"running":true,"has_selected_node":true,"selected_node":{"automationNodeId":"0/0","name":"Node","editor_node_id":0,"children_count":0}}}}
```

### back_step_viewer

Request:

```json
{"command":"back_step_viewer"}
```

Response shape:

```json
{"ok":true,"command":"back_step_viewer","result":{"running":true,"viewer":{"is_playing":true,"is_paused":true},"status":{"running":true,"has_selected_node":true,"selected_node":{"automationNodeId":"0/0","name":"Node","editor_node_id":0,"children_count":0}}}}
```

## Parameter inspection commands

Parameter inspection commands are read-only. They are intended to help MCP/AI clients understand which node is targeted and which coarse parameter groups exist before a later parameter-write phase. They do not accept arbitrary property names, do not dump all reflected properties, and do not return file paths or local resource paths.

Investigation notes:

- `Data.NodeBase` owns the common node-level fields: `Name`, `IsRendered`, `Parent`, `Children`, and `EditorNodeId`.
- `Data.NodeRoot` derives from `NodeBase` and owns the effect path internally, but the bridge does not expose that path.
- Regular `Data.Node` adds editable value objects: `CommonValues`, `LocationValues`, `RotationValues`, `ScalingValues`, `LocationAbsValues`, `GenerationLocationValues`, `DepthValues`, `RendererCommonValues`, `DrawingValues`, `SoundValues`, `AdvancedRendererCommonValuesValues`, `KillRulesValues`, `CollisionsValues`, and `GpuParticles`.
- GUI dock panels use `BindableComponent.ParameterList.SetValue(...)` with those objects, for example common/basic settings, spawning method, position, rotation, scale, render settings, sound, kill rules, collisions, and GPU particles.
- Safe for this phase: node identity, tree/layer counts, `IsRendered`, class/type names, and allowlisted coarse group names.
- Parameter value inspection reads only hand-written allowlisted properties. `CommonValues.Generation`, `CommonValues.Life`, `CommonValues.MaxGeneration`, `LocationValues`, `RotationValues`, and `ScalingValues` expose basic numeric value objects that can be safely summarized without reflection.
- `Value.FloatWithRandom` and `Value.IntWithRandom` are returned as `center`, `min`, `max`, `amplitude`, and `drawnAs`. `Value.Vector3D` is returned as `x/y/z`. `Value.Vector3DWithRandom` returns one random summary per axis.
- Complex curve data is currently summarized only. NURBS curve file paths and other local resource paths are intentionally omitted.
- Deferred for a later phase: writing parameters, texture replacement, file open/save, arbitrary reflection dumps, arbitrary property-name reads, and full FCurve/NURBS data extraction.

### get_node_basic_info_by_automation_id

Request:

```json
{"command":"get_node_basic_info_by_automation_id","params":{"automationNodeId":"0/1"}}
```

Response shape:

```json
{"ok":true,"command":"get_node_basic_info_by_automation_id","result":{"automationNodeId":"0/1","name":"Node","editorNodeId":0,"childCount":0,"parentAutomationNodeId":"0","isSelected":false,"isRendered":true,"nodeType":"node","className":"Node","layerNumber":2,"deepestLayerNumberInChildren":1}}
```

### get_node_parameter_groups_by_automation_id

Request:

```json
{"command":"get_node_parameter_groups_by_automation_id","params":{"automationNodeId":"0/1"}}
```

Response shape for a regular node:

```json
{"ok":true,"command":"get_node_parameter_groups_by_automation_id","result":{"automationNodeId":"0/1","name":"Node","groups":["node_base","common","generation","location","rotation","scale","local_force_field","depth","renderer_common","drawing","sound","advanced_render","kill_rules","collisions","gpu_particles"]}}
```

Response shape for the root node:

```json
{"ok":true,"command":"get_node_parameter_groups_by_automation_id","result":{"automationNodeId":"0","name":"Root","groups":["node_base"]}}
```

Parameter write commands such as `set_parameter` are intentionally not part of this phase.

## Parameter value inspection commands

Parameter value inspection commands are read-only. They run on the main/UI thread through `AutomationBridge.Update()` and expose only fixed allowlisted value summaries. They do not accept arbitrary parameter names and do not mutate editor state.

### get_node_base_parameters_by_automation_id

Request:

```json
{"command":"get_node_base_parameters_by_automation_id","params":{"automationNodeId":"0/1"}}
```

Response shape:

```json
{"ok":true,"command":"get_node_base_parameters_by_automation_id","result":{"automationNodeId":"0/1","name":"Node","isRendered":true,"childCount":0,"nodeType":"node","className":"Node"}}
```

This command can be used for both the root node and regular nodes.

### get_node_generation_parameters_by_automation_id

Request:

```json
{"command":"get_node_generation_parameters_by_automation_id","params":{"automationNodeId":"0/1"}}
```

Response shape:

```json
{"ok":true,"command":"get_node_generation_parameters_by_automation_id","result":{"automationNodeId":"0/1","name":"Node","maxGeneration":{"value":1,"infinite":false},"life":{"center":100,"min":100,"max":100,"amplitude":0,"drawnAs":"CenterAndAmplitude"},"generation":{"timing":{"value":"Continuous","valueId":0},"generationTime":{"center":1.0,"min":1.0,"max":1.0,"amplitude":0.0,"drawnAs":"CenterAndAmplitude"},"generationTimeOffset":{"center":0.0,"min":0.0,"max":0.0,"amplitude":0.0,"drawnAs":"CenterAndAmplitude"},"toStartGeneration":{"value":"None","valueId":0},"toStopGeneration":{"value":"None","valueId":0},"trigger":{"value":"None","valueId":0},"triggerCount":{"center":1,"min":1,"max":1,"amplitude":0,"drawnAs":"CenterAndAmplitude"}},"parentEffect":{"location":{"value":"Already","valueId":0},"rotation":{"value":"Already","valueId":0},"scale":{"value":"Already","valueId":0}},"removal":{"whenLifeIsExtinct":true,"whenParentIsRemoved":false,"whenAllChildrenAreRemoved":false,"triggerToRemove":{"value":"None","valueId":0}}}}
```

The root node does not have `Data.Node.CommonValues`; the bridge returns an error if this command targets root.

### get_node_transform_parameters_by_automation_id

Request:

```json
{"command":"get_node_transform_parameters_by_automation_id","params":{"automationNodeId":"0/1"}}
```

Response shape:

```json
{"ok":true,"command":"get_node_transform_parameters_by_automation_id","result":{"automationNodeId":"0/1","name":"Node","location":{"type":{"value":"Fixed","valueId":0},"fixed":{"location":{"x":0.0,"y":0.0,"z":0.0}},"pva":{"location":{"x":{"center":0.0,"min":0.0,"max":0.0,"amplitude":0.0,"drawnAs":"CenterAndAmplitude"},"y":{"center":0.0,"min":0.0,"max":0.0,"amplitude":0.0,"drawnAs":"CenterAndAmplitude"},"z":{"center":0.0,"min":0.0,"max":0.0,"amplitude":0.0,"drawnAs":"CenterAndAmplitude"},"drawnAs":"CenterAndAmplitude"},"velocity":{},"acceleration":{}},"easing":{},"locationFCurve":{"kind":"fcurve","summary":"FCurve values are not expanded in this read-only spike"},"nurbsCurve":{"summary":"NURBS curve file path is intentionally omitted","scale":{"value":1.0},"moveSpeed":{"value":1.0},"loopType":{"value":"Repeat","valueId":0}},"viewOffset":{"distance":{"center":3.0,"min":3.0,"max":3.0,"amplitude":0.0,"drawnAs":"CenterAndAmplitude"}}},"rotation":{"type":{"value":"Fixed","valueId":0},"fixed":{"rotation":{"x":0.0,"y":0.0,"z":0.0}}},"scale":{"type":{"value":"Fixed","valueId":0},"fixed":{"scale":{"x":1.0,"y":1.0,"z":1.0}}}}}
```

The actual response includes the same allowlisted value summaries for PVA/easing/axis/single-scale groups. `FCurve` values are intentionally summarized for now. The root node does not have transform parameter objects; the bridge returns an error if this command targets root.

Parameter write remains a future phase. A later write API should use stable allowlisted parameter IDs, validation rules, and undo-aware editor commands instead of accepting arbitrary property paths.

## Usage examples

Start Effekseer:

```powershell
.\Effekseer.exe --automation-port 50123
```

Or:

```powershell
$env:EFFEKSEER_AUTOMATION_PORT = "50123"
.\Effekseer.exe
```

Send a command from PowerShell:

```powershell
$client = [System.Net.Sockets.TcpClient]::new("127.0.0.1", 50123)
$stream = $client.GetStream()
$writer = [System.IO.StreamWriter]::new($stream, [System.Text.UTF8Encoding]::new($false))
$reader = [System.IO.StreamReader]::new($stream, [System.Text.UTF8Encoding]::new($false))
$writer.AutoFlush = $true
$writer.WriteLine('{"command":"ping"}')
$reader.ReadLine()
$client.Close()
```

## Risks and follow-ups

- This spike has no authentication. It relies on opt-in enablement and loopback-only binding.
- `add_node_to_selected` currently mirrors the existing `Commands.AddNode()` layer-limit behavior but returns the newly created node by calling `Core.SelectedNode.AddChild()` directly.
- Response waiting has a 30 second timeout if the editor main loop is blocked.
- Future MCP-facing work should define a versioned command schema, request IDs, and richer error codes.

## Security policy

- The bridge is disabled by default and starts only when an automation port is explicitly provided.
- The listener binds to `127.0.0.1` only.
- Requests are JSON-line command objects, not scripts.
- Only allowlisted commands are accepted.
- The bridge does not execute shell commands or arbitrary C# code.
- The network/client tasks parse JSON and enqueue command data only. They do not read or mutate `Core`, `Core.SelectedNode`, or node objects directly.
- Editor state reads and mutations run from `AutomationBridge.Update()` on the main/UI thread.
- Viewer playback commands run from `AutomationBridge.Update()` on the main/UI thread and call existing editor command methods; they do not click or automate GUI controls.
- Parameter inspection commands are read-only and expose only allowlisted summary fields/group names.
- Parameter value inspection commands are read-only and expose only hand-written allowlisted numeric/enum/boolean summaries. They do not perform reflection dumps or arbitrary property-name reads.
- Responses intentionally avoid absolute paths and local resource paths.

## Known limitations

- `EditorNodeId` can be `0` before the editor/exporter assigns IDs. MCP clients should prefer `automationNodeId` for edit operations.
- `automationNodeId` is a path into the current tree. It is stable while the tree shape before that node is unchanged, but sibling insertions, removals, duplicates, and insert-parent operations can change path indexes. Refresh with `get_node_tree` after structural edits.
- `rename_node` rejects the root node for now.
- Node names accepted through the bridge are limited to 128 characters.
- The bridge has no authentication beyond opt-in loopback binding.
- Parameter value inspection currently covers base, generation/common, location, rotation, and scale summaries only. It does not mutate values and does not expand full FCurve/NURBS data.

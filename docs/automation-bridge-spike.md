# Automation Bridge spike

This spike adds a minimal, opt-in automation bridge for controlling a running Effekseer Editor from a local external process.

## Scope

- Disabled by default.
- Binds only to `127.0.0.1`.
- Enabled by `--automation-port <port>` or `EFFEKSEER_AUTOMATION_PORT=<port>`.
- Uses JSON-line TCP: one JSON object per line, one JSON object response per line.
- Allows only explicit commands: `ping`, `get_status`, `get_node_tree`, and `add_node_to_selected`.
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
{"ok":true,"command":"get_status","result":{"running":true,"has_selected_node":true,"selected_node":{"name":"Node","editor_node_id":0,"children_count":0}}}
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
{"ok":true,"command":"add_node_to_selected","result":{"selected_node":{"name":"Node","editor_node_id":0,"children_count":1},"added_node":{"name":"Node","editor_node_id":0,"children_count":0}}}
```

### get_node_tree

Request:

```json
{"command":"get_node_tree"}
```

Response shape:

```json
{"ok":true,"command":"get_node_tree","result":{"root":{"editorNodeId":0,"name":"Root","isSelected":false,"childCount":1,"children":[{"editorNodeId":0,"name":"Node","isSelected":true,"childCount":0,"children":[]}]}}}
```

The response contains only editor node metadata needed by automation clients. It does not include project paths, resource paths, or other local filesystem information.

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
- Future MCP-facing work should define a versioned command schema, request IDs, richer error codes, and more explicit node identifiers.

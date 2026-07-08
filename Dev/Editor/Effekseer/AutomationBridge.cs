using System;
using System.Collections.Concurrent;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;

namespace Effekseer
{
	public sealed class AutomationBridge : IDisposable
	{
		class PendingCommand
		{
			public string Command;
			public JObject Params;
			public TaskCompletionSource<JObject> Completion = new TaskCompletionSource<JObject>(TaskCreationOptions.RunContinuationsAsynchronously);
		}

		const int MaxNodeNameLength = 128;
		readonly int port;
		readonly ConcurrentQueue<PendingCommand> pendingCommands = new ConcurrentQueue<PendingCommand>();
		readonly CancellationTokenSource cancellation = new CancellationTokenSource();
		TcpListener listener;
		Task acceptTask;

		public AutomationBridge(int port)
		{
			this.port = port;
		}

		public void Start()
		{
			if (listener != null)
			{
				return;
			}

			listener = new TcpListener(IPAddress.Loopback, port);
			listener.Start();
			acceptTask = Task.Run(AcceptLoop);
			Utils.Logger.Write($"Automation bridge listening on 127.0.0.1:{port}");
		}

		public void Update()
		{
			while (pendingCommands.TryDequeue(out var command))
			{
				try
				{
					command.Completion.TrySetResult(ExecuteOnMainThread(command.Command, command.Params));
				}
				catch (Exception e)
				{
					command.Completion.TrySetResult(CreateError(command.Command, e.Message));
				}
			}
		}

		public void Dispose()
		{
			cancellation.Cancel();

			if (listener != null)
			{
				listener.Stop();
				listener = null;
			}

			while (pendingCommands.TryDequeue(out var command))
			{
				command.Completion.TrySetResult(CreateError(command.Command, "automation bridge is stopping"));
			}

			try
			{
				acceptTask?.Wait(1000);
			}
			catch
			{
			}

			cancellation.Dispose();
		}

		async Task AcceptLoop()
		{
			while (!cancellation.IsCancellationRequested)
			{
				try
				{
					var client = await listener.AcceptTcpClientAsync();
					_ = Task.Run(() => ProcessClient(client));
				}
				catch (ObjectDisposedException)
				{
					return;
				}
				catch (SocketException)
				{
					if (cancellation.IsCancellationRequested)
					{
						return;
					}
				}
				catch (Exception e)
				{
					Utils.Logger.Write($"Automation bridge accept error : {e}");
				}
			}
		}

		async Task ProcessClient(TcpClient client)
		{
			using (client)
			using (var stream = client.GetStream())
			using (var reader = new StreamReader(stream, new UTF8Encoding(false), false, 4096, true))
			using (var writer = new StreamWriter(stream, new UTF8Encoding(false), 4096, true))
			{
				writer.NewLine = "\n";
				writer.AutoFlush = true;

				while (!cancellation.IsCancellationRequested)
				{
					var line = await reader.ReadLineAsync();
					if (line == null)
					{
						break;
					}

					var response = await ProcessLine(line);
					await writer.WriteLineAsync(response.ToString(Newtonsoft.Json.Formatting.None));
				}
			}
		}

		async Task<JObject> ProcessLine(string line)
		{
			string command = null;
			JObject parameters = null;

			try
			{
				var request = JObject.Parse(line);
				command = request.Value<string>("command");
				parameters = request["params"] as JObject ?? new JObject();
			}
			catch (Exception e)
			{
				return CreateError(null, $"invalid json: {e.Message}");
			}

			if (!IsAllowedCommand(command))
			{
				return CreateError(command, "unknown command");
			}

			var pending = new PendingCommand { Command = command, Params = parameters };
			pendingCommands.Enqueue(pending);

			var completed = await Task.WhenAny(pending.Completion.Task, Task.Delay(TimeSpan.FromSeconds(30), cancellation.Token));
			if (completed != pending.Completion.Task)
			{
				return CreateError(command, "timed out waiting for main thread");
			}

			return await pending.Completion.Task;
		}

		static bool IsAllowedCommand(string command)
		{
			return command == "ping" ||
				command == "get_status" ||
				command == "get_node_tree" ||
				command == "add_node_to_selected" ||
				command == "select_node_by_id" ||
				command == "add_node_to_parent" ||
				command == "rename_node" ||
				command == "select_node_by_automation_id" ||
				command == "add_node_to_parent_by_automation_id" ||
				command == "rename_node_by_automation_id" ||
				command == "remove_node_by_automation_id" ||
				command == "duplicate_node_by_automation_id" ||
				command == "insert_parent_node_by_automation_id" ||
				command == "undo" ||
				command == "redo";
		}

		static JObject ExecuteOnMainThread(string command, JObject parameters)
		{
			if (command == "ping")
			{
				return CreateOk(command, new JObject
				{
					["message"] = "pong"
				});
			}

			if (command == "get_status")
			{
				return CreateOk(command, CreateStatusPayload());
			}

			if (command == "get_node_tree")
			{
				return CreateOk(command, CreateNodeTreePayload());
			}

			if (command == "select_node_by_id")
			{
				if (!TryGetIntParameter(parameters, "editorNodeId", out var editorNodeId, out var error))
				{
					return CreateError(command, error);
				}

				var node = FindNodeByEditorNodeId(editorNodeId);
				if (node == null)
				{
					return CreateError(command, "node is not found");
				}

				Core.SelectedNode = node;
				return CreateOk(command, new JObject
				{
					["selected_node"] = CreateNodePayload(node)
				});
			}

			if (command == "select_node_by_automation_id")
			{
				if (!TryGetStringParameter(parameters, "automationNodeId", out var automationNodeId, out var error))
				{
					return CreateError(command, error);
				}

				var node = FindNodeByAutomationNodeId(automationNodeId, out error);
				if (node == null)
				{
					return CreateError(command, error);
				}

				Core.SelectedNode = node;
				return CreateOk(command, new JObject
				{
					["selected_node"] = CreateNodePayload(node, automationNodeId)
				});
			}

			if (command == "add_node_to_parent")
			{
				if (!TryGetIntParameter(parameters, "parentEditorNodeId", out var parentEditorNodeId, out var error))
				{
					return CreateError(command, error);
				}

				var parent = FindNodeByEditorNodeId(parentEditorNodeId);
				if (parent == null)
				{
					return CreateError(command, "parent node is not found");
				}

				if (parent.GetLayerNumber() >= Constant.NodeLayerLimit)
				{
					return CreateError(command, "node layer limit exceeded");
				}

				var name = parameters.Value<string>("name");
				if (name != null && !IsValidNodeName(name, out error))
				{
					return CreateError(command, error);
				}

				var added = parent.AddChild();
				if (name != null)
				{
					added.Name.Value = name;
				}

				return CreateOk(command, new JObject
				{
					["parent_node"] = CreateNodePayload(parent),
					["added_node"] = CreateNodePayload(added)
				});
			}

			if (command == "add_node_to_parent_by_automation_id")
			{
				if (!TryGetStringParameter(parameters, "parentAutomationNodeId", out var parentAutomationNodeId, out var error))
				{
					return CreateError(command, error);
				}

				var parent = FindNodeByAutomationNodeId(parentAutomationNodeId, out error);
				if (parent == null)
				{
					return CreateError(command, error);
				}

				if (parent.GetLayerNumber() >= Constant.NodeLayerLimit)
				{
					return CreateError(command, "node layer limit exceeded");
				}

				var name = parameters.Value<string>("name");
				if (name != null && !IsValidNodeName(name, out error))
				{
					return CreateError(command, error);
				}

				var added = parent.AddChild();
				if (name != null)
				{
					added.Name.Value = name;
				}

				var addedAutomationNodeId = CreateChildAutomationNodeId(parentAutomationNodeId, parent.Children.Count - 1);
				return CreateOk(command, new JObject
				{
					["parent_node"] = CreateNodePayload(parent, parentAutomationNodeId),
					["added_node"] = CreateNodePayload(added, addedAutomationNodeId)
				});
			}

			if (command == "rename_node")
			{
				if (!TryGetIntParameter(parameters, "editorNodeId", out var editorNodeId, out var error))
				{
					return CreateError(command, error);
				}

				var name = parameters.Value<string>("name");
				if (!IsValidNodeName(name, out error))
				{
					return CreateError(command, error);
				}

				var node = FindNodeByEditorNodeId(editorNodeId);
				if (node == null)
				{
					return CreateError(command, "node is not found");
				}

				if (node.Parent == null)
				{
					return CreateError(command, "root node cannot be renamed");
				}

				node.Name.Value = name;
				return CreateOk(command, new JObject
				{
					["renamed_node"] = CreateNodePayload(node)
				});
			}

			if (command == "rename_node_by_automation_id")
			{
				if (!TryGetStringParameter(parameters, "automationNodeId", out var automationNodeId, out var error))
				{
					return CreateError(command, error);
				}

				var name = parameters.Value<string>("name");
				if (!IsValidNodeName(name, out error))
				{
					return CreateError(command, error);
				}

				var node = FindNodeByAutomationNodeId(automationNodeId, out error);
				if (node == null)
				{
					return CreateError(command, error);
				}

				if (node.Parent == null)
				{
					return CreateError(command, "root node cannot be renamed");
				}

				node.Name.Value = name;
				return CreateOk(command, new JObject
				{
					["renamed_node"] = CreateNodePayload(node, automationNodeId)
				});
			}

			if (command == "remove_node_by_automation_id")
			{
				if (!TryGetStringParameter(parameters, "automationNodeId", out var automationNodeId, out var error))
				{
					return CreateError(command, error);
				}

				var node = FindNodeByAutomationNodeId(automationNodeId, out error);
				if (node == null)
				{
					return CreateError(command, error);
				}

				if (node.Parent == null)
				{
					return CreateError(command, "root node cannot be removed");
				}

				if (!(node is Data.Node removableNode))
				{
					return CreateError(command, "node cannot be removed");
				}

				var parent = node.Parent;
				var parentAutomationNodeId = FindAutomationNodeId(parent);
				var removedNodePayload = CreateNodePayload(node, automationNodeId);
				parent.RemoveChild(removableNode);

				return CreateOk(command, new JObject
				{
					["parent_node"] = CreateNodePayload(parent, parentAutomationNodeId),
					["removed_node"] = removedNodePayload
				});
			}

			if (command == "duplicate_node_by_automation_id")
			{
				if (!TryGetStringParameter(parameters, "automationNodeId", out var automationNodeId, out var error))
				{
					return CreateError(command, error);
				}

				var node = FindNodeByAutomationNodeId(automationNodeId, out error);
				if (node == null)
				{
					return CreateError(command, error);
				}

				if (node.Parent == null)
				{
					return CreateError(command, "root node cannot be duplicated");
				}

				var parent = node.Parent;
				if (parent.GetLayerNumber() + node.GetDeepestLayerNumberInChildren() > Constant.NodeLayerLimit)
				{
					return CreateError(command, "node layer limit exceeded");
				}

				var name = parameters.Value<string>("name");
				if (name != null && !IsValidNodeName(name, out error))
				{
					return CreateError(command, error);
				}

				var data = Core.Copy(node);
				if (!Core.IsValidXml(data))
				{
					return CreateError(command, "failed to copy node");
				}

				Data.Node duplicated = null;
				Command.CommandManager.StartCollection();
				try
				{
					duplicated = parent.AddChild();
					Core.Paste(duplicated, data);
					if (name != null)
					{
						duplicated.Name.Value = name;
					}
				}
				finally
				{
					Command.CommandManager.EndCollection();
				}

				if (Core.Root.GetDeepestLayerNumberInChildren() > Constant.NodeLayerLimit)
				{
					Command.CommandManager.Undo(true);
					return CreateError(command, "node layer limit exceeded");
				}

				var parentAutomationNodeId = FindAutomationNodeId(parent);
				var duplicatedAutomationNodeId = CreateChildAutomationNodeId(parentAutomationNodeId, parent.Children.Count - 1);
				return CreateOk(command, new JObject
				{
					["parent_node"] = CreateNodePayload(parent, parentAutomationNodeId),
					["duplicated_node"] = CreateNodePayload(duplicated, duplicatedAutomationNodeId)
				});
			}

			if (command == "insert_parent_node_by_automation_id")
			{
				if (!TryGetStringParameter(parameters, "automationNodeId", out var automationNodeId, out var error))
				{
					return CreateError(command, error);
				}

				var node = FindNodeByAutomationNodeId(automationNodeId, out error);
				if (node == null)
				{
					return CreateError(command, error);
				}

				if (node.Parent == null)
				{
					return CreateError(command, "root node cannot be wrapped");
				}

				if (Core.Root.GetDeepestLayerNumberInChildren() >= Constant.NodeLayerLimit)
				{
					return CreateError(command, "node layer limit exceeded");
				}

				var name = parameters.Value<string>("name");
				if (name != null && !IsValidNodeName(name, out error))
				{
					return CreateError(command, error);
				}

				var inserted = node.InsertParent();
				if (inserted == null)
				{
					return CreateError(command, "failed to insert parent node");
				}

				if (name != null)
				{
					inserted.Name.Value = name;
				}

				return CreateOk(command, new JObject
				{
					["inserted_node"] = CreateNodePayload(inserted, automationNodeId),
					["moved_node"] = CreateNodePayload(node, CreateChildAutomationNodeId(automationNodeId, 0))
				});
			}

			if (command == "undo")
			{
				var succeeded = Command.CommandManager.Undo();
				if (!succeeded)
				{
					return CreateError(command, "nothing to undo");
				}

				return CreateOk(command, new JObject
				{
					["status"] = CreateStatusPayload()
				});
			}

			if (command == "redo")
			{
				var succeeded = Command.CommandManager.Redo();
				if (!succeeded)
				{
					return CreateError(command, "nothing to redo");
				}

				return CreateOk(command, new JObject
				{
					["status"] = CreateStatusPayload()
				});
			}

			if (command == "add_node_to_selected")
			{
				var selected = Core.SelectedNode;
				if (selected == null)
				{
					return CreateError(command, "selected node is not found");
				}

				if (selected.GetLayerNumber() >= Constant.NodeLayerLimit)
				{
					return CreateError(command, "node layer limit exceeded");
				}

				var added = selected.AddChild();
				return CreateOk(command, new JObject
				{
					["selected_node"] = CreateNodePayload(selected),
					["added_node"] = CreateNodePayload(added)
				});
			}

			return CreateError(command, "unknown command");
		}

		static JObject CreateStatusPayload()
		{
			var selected = Core.SelectedNode;
			return new JObject
			{
				["running"] = true,
				["has_selected_node"] = selected != null,
				["selected_node"] = selected != null ? CreateNodePayload(selected) : null
			};
		}

		static bool TryGetIntParameter(JObject parameters, string name, out int value, out string error)
		{
			value = 0;
			error = null;

			if (parameters == null || parameters[name] == null)
			{
				error = $"params.{name} is required";
				return false;
			}

			if (parameters[name].Type != JTokenType.Integer)
			{
				error = $"params.{name} must be an integer";
				return false;
			}

			value = parameters.Value<int>(name);
			return true;
		}

		static bool TryGetStringParameter(JObject parameters, string name, out string value, out string error)
		{
			value = null;
			error = null;

			if (parameters == null || parameters[name] == null)
			{
				error = $"params.{name} is required";
				return false;
			}

			if (parameters[name].Type != JTokenType.String)
			{
				error = $"params.{name} must be a string";
				return false;
			}

			value = parameters.Value<string>(name);
			return true;
		}

		static bool IsValidNodeName(string name, out string error)
		{
			error = null;

			if (string.IsNullOrEmpty(name))
			{
				error = "params.name must not be empty";
				return false;
			}

			if (name.Length > MaxNodeNameLength)
			{
				error = $"params.name must be {MaxNodeNameLength} characters or less";
				return false;
			}

			return true;
		}

		static Data.NodeBase FindNodeByEditorNodeId(int editorNodeId)
		{
			if (Core.Root == null)
			{
				throw new InvalidOperationException("root node is not found");
			}

			return FindNodeByEditorNodeId(Core.Root, editorNodeId);
		}

		static Data.NodeBase FindNodeByEditorNodeId(Data.NodeBase root, int editorNodeId)
		{
			if (root.EditorNodeId == editorNodeId)
			{
				return root;
			}

			for (int i = 0; i < root.Children.Count; i++)
			{
				var found = FindNodeByEditorNodeId(root.Children[i], editorNodeId);
				if (found != null)
				{
					return found;
				}
			}

			return null;
		}

		static Data.NodeBase FindNodeByAutomationNodeId(string automationNodeId, out string error)
		{
			if (Core.Root == null)
			{
				error = "root node is not found";
				return null;
			}

			return FindNodeByAutomationNodeId(Core.Root, automationNodeId, out error);
		}

		static Data.NodeBase FindNodeByAutomationNodeId(Data.NodeBase root, string automationNodeId, out string error)
		{
			error = null;

			if (string.IsNullOrEmpty(automationNodeId))
			{
				error = "params.automationNodeId must not be empty";
				return null;
			}

			var parts = automationNodeId.Split('/');
			if (parts.Length == 0 || parts[0] != "0")
			{
				error = "automationNodeId must start with 0";
				return null;
			}

			var node = root;
			for (int i = 1; i < parts.Length; i++)
			{
				if (!int.TryParse(parts[i], out var childIndex) || childIndex < 0 || parts[i] != childIndex.ToString())
				{
					error = "automationNodeId contains an invalid index";
					return null;
				}

				if (childIndex >= node.Children.Count)
				{
					error = "automationNodeId index is out of range";
					return null;
				}

				node = node.Children[childIndex];
			}

			return node;
		}

		static string FindAutomationNodeId(Data.NodeBase target)
		{
			if (Core.Root == null || target == null)
			{
				return null;
			}

			if (Core.Root == target)
			{
				return "0";
			}

			return FindAutomationNodeId(Core.Root, target, "0");
		}

		static string FindAutomationNodeId(Data.NodeBase parent, Data.NodeBase target, string parentAutomationNodeId)
		{
			for (int i = 0; i < parent.Children.Count; i++)
			{
				var child = parent.Children[i];
				var childAutomationNodeId = CreateChildAutomationNodeId(parentAutomationNodeId, i);
				if (child == target)
				{
					return childAutomationNodeId;
				}

				var found = FindAutomationNodeId(child, target, childAutomationNodeId);
				if (found != null)
				{
					return found;
				}
			}

			return null;
		}

		static string CreateChildAutomationNodeId(string parentAutomationNodeId, int childIndex)
		{
			return $"{parentAutomationNodeId}/{childIndex}";
		}

		static JObject CreateNodeTreePayload()
		{
			return new JObject
			{
				["root"] = Core.Root != null ? CreateNodeTreeNodePayload(Core.Root, "0") : null
			};
		}

		static JObject CreateNodeTreeNodePayload(Data.NodeBase node, string automationNodeId)
		{
			var children = new JArray();
			for (int i = 0; i < node.Children.Count; i++)
			{
				children.Add(CreateNodeTreeNodePayload(node.Children[i], CreateChildAutomationNodeId(automationNodeId, i)));
			}

			return new JObject
			{
				["automationNodeId"] = automationNodeId,
				["editorNodeId"] = node.EditorNodeId,
				["name"] = node.Name.Value,
				["isSelected"] = node == Core.SelectedNode,
				["childCount"] = node.Children.Count,
				["children"] = children
			};
		}

		static JObject CreateNodePayload(Data.NodeBase node)
		{
			return CreateNodePayload(node, FindAutomationNodeId(node));
		}

		static JObject CreateNodePayload(Data.NodeBase node, string automationNodeId)
		{
			return new JObject
			{
				["automationNodeId"] = automationNodeId,
				["name"] = node.Name.Value,
				["editor_node_id"] = node.EditorNodeId,
				["children_count"] = node.Children.Count
			};
		}

		static JObject CreateOk(string command, JObject payload)
		{
			return new JObject
			{
				["ok"] = true,
				["command"] = command,
				["result"] = payload
			};
		}

		static JObject CreateError(string command, string message)
		{
			return new JObject
			{
				["ok"] = false,
				["command"] = command,
				["error"] = message
			};
		}
	}
}

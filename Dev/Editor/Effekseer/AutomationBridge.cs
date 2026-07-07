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
			public TaskCompletionSource<JObject> Completion = new TaskCompletionSource<JObject>(TaskCreationOptions.RunContinuationsAsynchronously);
		}

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
					command.Completion.TrySetResult(ExecuteOnMainThread(command.Command));
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

			try
			{
				var request = JObject.Parse(line);
				command = request.Value<string>("command");
			}
			catch (Exception e)
			{
				return CreateError(null, $"invalid json: {e.Message}");
			}

			if (!IsAllowedCommand(command))
			{
				return CreateError(command, "unknown command");
			}

			var pending = new PendingCommand { Command = command };
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
				command == "add_node_to_selected";
		}

		static JObject ExecuteOnMainThread(string command)
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

		static JObject CreateNodeTreePayload()
		{
			return new JObject
			{
				["root"] = Core.Root != null ? CreateNodeTreeNodePayload(Core.Root) : null
			};
		}

		static JObject CreateNodeTreeNodePayload(Data.NodeBase node)
		{
			var children = new JArray();
			for (int i = 0; i < node.Children.Count; i++)
			{
				children.Add(CreateNodeTreeNodePayload(node.Children[i]));
			}

			return new JObject
			{
				["editorNodeId"] = node.EditorNodeId,
				["name"] = node.Name.Value,
				["isSelected"] = node == Core.SelectedNode,
				["childCount"] = node.Children.Count,
				["children"] = children
			};
		}

		static JObject CreateNodePayload(Data.NodeBase node)
		{
			return new JObject
			{
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

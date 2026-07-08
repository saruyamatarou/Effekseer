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
		const int MaxAutomationIntegerValue = 1000000;
		const float MaxAutomationFloatAbs = 1000000.0f;
		static readonly string[] AllowedCommands = new[]
		{
			"get_bridge_capabilities",
			"get_workspace_status",
			"ping",
			"get_status",
			"get_node_tree",
			"save_project_to_workspace",
			"open_project_from_workspace",
			"export_runtime_effect_to_workspace",
			"add_node_to_selected",
			"select_node_by_id",
			"add_node_to_parent",
			"rename_node",
			"select_node_by_automation_id",
			"add_node_to_parent_by_automation_id",
			"rename_node_by_automation_id",
			"remove_node_by_automation_id",
			"duplicate_node_by_automation_id",
			"insert_parent_node_by_automation_id",
			"undo",
			"redo",
			"play_viewer",
			"stop_viewer",
			"step_viewer",
			"back_step_viewer",
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
			"set_node_color_all_fixed_rgba_by_automation_id",
			"set_node_sprite_corner_colors_fixed_rgba_by_automation_id",
			"set_node_alpha_blend_by_automation_id",
			"set_node_z_write_by_automation_id",
			"set_node_z_test_by_automation_id",
			"set_node_renderer_type_by_automation_id",
		};
		readonly int port;
		readonly string automationWorkspaceRoot;
		readonly ConcurrentQueue<PendingCommand> pendingCommands = new ConcurrentQueue<PendingCommand>();
		readonly CancellationTokenSource cancellation = new CancellationTokenSource();
		TcpListener listener;
		Task acceptTask;

		public AutomationBridge(int port)
			: this(port, null)
		{
		}

		public AutomationBridge(int port, string automationWorkspaceRoot)
		{
			this.port = port;
			this.automationWorkspaceRoot = NormalizeAutomationWorkspaceRoot(automationWorkspaceRoot);
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
			if (!string.IsNullOrEmpty(automationWorkspaceRoot))
			{
				Utils.Logger.Write("Automation bridge workspace is enabled.");
			}
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
			return Array.IndexOf(AllowedCommands, command) >= 0;
		}

		JObject ExecuteOnMainThread(string command, JObject parameters)
		{
			if (command == "get_bridge_capabilities")
			{
				return CreateOk(command, CreateBridgeCapabilitiesPayload());
			}

			if (command == "get_workspace_status")
			{
				return CreateOk(command, CreateWorkspaceStatusPayload());
			}

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

			if (command == "save_project_to_workspace")
			{
				if (!TryGetStringParameter(parameters, "path", out var path, out var error))
				{
					return CreateError(command, error);
				}

				if (!TryValidateWorkspaceProjectPath(path, mustExist: false, out var fullPath, out var workspaceRelativePath, out error))
				{
					return CreateError(command, error);
				}

				var parentDirectory = Path.GetDirectoryName(fullPath);
				if (!string.IsNullOrEmpty(parentDirectory))
				{
					Directory.CreateDirectory(parentDirectory);
				}

				Core.SaveTo(fullPath);
				return CreateOk(command, new JObject
				{
					["path"] = workspaceRelativePath,
					["status"] = CreateStatusPayload()
				});
			}

			if (command == "open_project_from_workspace")
			{
				if (!TryGetStringParameter(parameters, "path", out var path, out var error))
				{
					return CreateError(command, error);
				}

				if (!TryValidateWorkspaceProjectPath(path, mustExist: true, out var fullPath, out var workspaceRelativePath, out error))
				{
					return CreateError(command, error);
				}

				Core.LoadFrom(fullPath);
				return CreateOk(command, new JObject
				{
					["path"] = workspaceRelativePath,
					["status"] = CreateStatusPayload()
				});
			}

			if (command == "export_runtime_effect_to_workspace")
			{
				if (!TryGetStringParameter(parameters, "path", out var path, out var error))
				{
					return CreateError(command, error);
				}

				if (!TryValidateWorkspaceRuntimeEffectPath(path, out var fullPath, out var workspaceRelativePath, out error))
				{
					return CreateError(command, error);
				}

				var parentDirectory = Path.GetDirectoryName(fullPath);
				if (!string.IsNullOrEmpty(parentDirectory))
				{
					Directory.CreateDirectory(parentDirectory);
				}

				var exporter = new Binary.Exporter();
				var binary = exporter.Export(Core.Root, Core.Option.Magnification);
				File.WriteAllBytes(fullPath, binary);
				return CreateOk(command, new JObject
				{
					["path"] = workspaceRelativePath,
					["bytes"] = binary.Length
				});
			}

			if (command == "play_viewer")
			{
				return ExecuteViewerCommand(command, Effekseer.GUI.Commands.Play);
			}

			if (command == "stop_viewer")
			{
				return ExecuteViewerCommand(command, Effekseer.GUI.Commands.Stop);
			}

			if (command == "step_viewer")
			{
				return ExecuteViewerCommand(command, Effekseer.GUI.Commands.Step);
			}

			if (command == "back_step_viewer")
			{
				return ExecuteViewerCommand(command, Effekseer.GUI.Commands.BackStep);
			}

			if (command == "get_node_basic_info_by_automation_id")
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

				return CreateOk(command, CreateNodeBasicInfoPayload(node, automationNodeId));
			}

			if (command == "get_node_parameter_groups_by_automation_id")
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

				return CreateOk(command, CreateNodeParameterGroupsPayload(node, automationNodeId));
			}

			if (command == "get_node_base_parameters_by_automation_id")
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

				return CreateOk(command, CreateNodeBaseParametersPayload(node, automationNodeId));
			}

			if (command == "get_node_generation_parameters_by_automation_id")
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

				if (!(node is Data.Node regularNode))
				{
					return CreateError(command, "node does not have generation parameters");
				}

				return CreateOk(command, CreateNodeGenerationParametersPayload(regularNode, automationNodeId));
			}

			if (command == "get_node_transform_parameters_by_automation_id")
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

				if (!(node is Data.Node regularNode))
				{
					return CreateError(command, "node does not have transform parameters");
				}

				return CreateOk(command, CreateNodeTransformParametersPayload(regularNode, automationNodeId));
			}

			if (command == "get_node_drawing_parameters_by_automation_id")
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

				if (!(node is Data.Node regularNode))
				{
					return CreateError(command, "node does not have drawing parameters");
				}

				return CreateOk(command, CreateNodeDrawingParametersPayload(regularNode, automationNodeId));
			}

			if (command == "get_node_renderer_parameters_by_automation_id")
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

				if (!(node is Data.Node regularNode))
				{
					return CreateError(command, "node does not have renderer parameters");
				}

				return CreateOk(command, CreateNodeRendererParametersPayload(regularNode, automationNodeId));
			}

			if (command == "set_node_is_rendered_by_automation_id")
			{
				if (!TryGetStringParameter(parameters, "automationNodeId", out var automationNodeId, out var error))
				{
					return CreateError(command, error);
				}

				if (!TryGetBooleanParameter(parameters, "isRendered", out var isRendered, out error))
				{
					return CreateError(command, error);
				}

				var node = FindNodeByAutomationNodeId(automationNodeId, out error);
				if (node == null)
				{
					return CreateError(command, error);
				}

				var before = node.IsRendered.Value;
				node.IsRendered.SetValue(isRendered);
				var after = node.IsRendered.Value;

				return CreateOk(command, new JObject
				{
					["automationNodeId"] = automationNodeId,
					["name"] = node.Name.Value,
					["before"] = before,
					["after"] = after,
					["baseParameters"] = CreateNodeBaseParametersPayload(node, automationNodeId)
				});
			}

			if (command == "set_node_max_generation_by_automation_id")
			{
				if (!TryGetWritableDataNode(command, parameters, out var automationNodeId, out var regularNode, out var error))
				{
					return CreateError(command, error);
				}

				if (!TryGetBoundedIntParameter(parameters, "maxGeneration", 1, MaxAutomationIntegerValue, out var maxGeneration, out error))
				{
					return CreateError(command, error);
				}

				var before = CreateIntWithInfinitePayload(regularNode.CommonValues.MaxGeneration);
				Command.CommandManager.StartCollection();
				try
				{
					regularNode.CommonValues.MaxGeneration.Infinite.SetValue(false);
					regularNode.CommonValues.MaxGeneration.Value.SetValue(maxGeneration);
				}
				finally
				{
					Command.CommandManager.EndCollection();
				}

				var after = CreateIntWithInfinitePayload(regularNode.CommonValues.MaxGeneration);
				return CreateOk(command, new JObject
				{
					["automationNodeId"] = automationNodeId,
					["name"] = regularNode.Name.Value,
					["before"] = before,
					["after"] = after,
					["generationParameters"] = CreateNodeGenerationParametersPayload(regularNode, automationNodeId)
				});
			}

			if (command == "set_node_life_by_automation_id")
			{
				if (!TryGetWritableDataNode(command, parameters, out var automationNodeId, out var regularNode, out var error))
				{
					return CreateError(command, error);
				}

				if (!TryGetBoundedIntParameter(parameters, "center", 1, MaxAutomationIntegerValue, out var center, out error) ||
					!TryGetBoundedIntParameter(parameters, "min", 1, MaxAutomationIntegerValue, out var min, out error) ||
					!TryGetBoundedIntParameter(parameters, "max", 1, MaxAutomationIntegerValue, out var max, out error))
				{
					return CreateError(command, error);
				}

				if (min > center || center > max)
				{
					return CreateError(command, "params.min <= params.center <= params.max is required");
				}

				var before = CreateIntWithRandomPayload(regularNode.CommonValues.Life);
				SetIntWithRandom(regularNode.CommonValues.Life, center, min, max);
				var after = CreateIntWithRandomPayload(regularNode.CommonValues.Life);
				return CreateOk(command, new JObject
				{
					["automationNodeId"] = automationNodeId,
					["name"] = regularNode.Name.Value,
					["before"] = before,
					["after"] = after,
					["generationParameters"] = CreateNodeGenerationParametersPayload(regularNode, automationNodeId)
				});
			}

			if (command == "set_node_fixed_location_by_automation_id")
			{
				if (!TryGetWritableDataNode(command, parameters, out var automationNodeId, out var regularNode, out var error) ||
					!TryGetVector3Parameters(parameters, out var x, out var y, out var z, out error))
				{
					return CreateError(command, error);
				}

				var target = regularNode.LocationValues.Fixed.Location;
				var before = CreateVector3DPayload(target);
				SetVector3D(target, x, y, z);
				var after = CreateVector3DPayload(target);
				return CreateOk(command, new JObject
				{
					["automationNodeId"] = automationNodeId,
					["name"] = regularNode.Name.Value,
					["before"] = before,
					["after"] = after,
					["transformParameters"] = CreateNodeTransformParametersPayload(regularNode, automationNodeId)
				});
			}

			if (command == "set_node_fixed_rotation_by_automation_id")
			{
				if (!TryGetWritableDataNode(command, parameters, out var automationNodeId, out var regularNode, out var error) ||
					!TryGetVector3Parameters(parameters, out var x, out var y, out var z, out error))
				{
					return CreateError(command, error);
				}

				var target = regularNode.RotationValues.Fixed.Rotation;
				var before = CreateVector3DPayload(target);
				SetVector3D(target, x, y, z);
				var after = CreateVector3DPayload(target);
				return CreateOk(command, new JObject
				{
					["automationNodeId"] = automationNodeId,
					["name"] = regularNode.Name.Value,
					["before"] = before,
					["after"] = after,
					["transformParameters"] = CreateNodeTransformParametersPayload(regularNode, automationNodeId)
				});
			}

			if (command == "set_node_fixed_scale_by_automation_id")
			{
				if (!TryGetWritableDataNode(command, parameters, out var automationNodeId, out var regularNode, out var error) ||
					!TryGetVector3Parameters(parameters, out var x, out var y, out var z, out error))
				{
					return CreateError(command, error);
				}

				var target = regularNode.ScalingValues.Fixed.Scale;
				var before = CreateVector3DPayload(target);
				SetVector3D(target, x, y, z);
				var after = CreateVector3DPayload(target);
				return CreateOk(command, new JObject
				{
					["automationNodeId"] = automationNodeId,
					["name"] = regularNode.Name.Value,
					["before"] = before,
					["after"] = after,
					["transformParameters"] = CreateNodeTransformParametersPayload(regularNode, automationNodeId)
				});
			}

			if (command == "set_node_color_all_fixed_rgba_by_automation_id")
			{
				if (!TryGetWritableDataNode(command, parameters, out var automationNodeId, out var regularNode, out var error) ||
					!TryGetRgbaParameters(parameters, out var r, out var g, out var b, out var a, out error))
				{
					return CreateError(command, error);
				}

				var target = regularNode.DrawingValues.ColorAll;
				var before = CreateStandardColorPayload(target);
				Command.CommandManager.StartCollection();
				try
				{
					target.Type.SetValue(Data.StandardColorType.Fixed);
					target.Fixed.SetValue(r, g, b, a);
				}
				finally
				{
					Command.CommandManager.EndCollection();
				}

				var after = CreateStandardColorPayload(target);
				return CreateOk(command, new JObject
				{
					["automationNodeId"] = automationNodeId,
					["name"] = regularNode.Name.Value,
					["before"] = before,
					["after"] = after,
					["drawingParameters"] = CreateNodeDrawingParametersPayload(regularNode, automationNodeId)
				});
			}

			if (command == "set_node_sprite_corner_colors_fixed_rgba_by_automation_id")
			{
				if (!TryGetWritableDataNode(command, parameters, out var automationNodeId, out var regularNode, out var error))
				{
					return CreateError(command, error);
				}

				if (regularNode.DrawingValues.Type.Value != Data.RendererValues.ParamaterType.Sprite)
				{
					return CreateError(command, "rendererType must be sprite to set sprite corner colors");
				}

				if (!TryGetRgbaObjectParameter(parameters, "lowerLeft", out var lowerLeft, out error) ||
					!TryGetRgbaObjectParameter(parameters, "lowerRight", out var lowerRight, out error) ||
					!TryGetRgbaObjectParameter(parameters, "upperLeft", out var upperLeft, out error) ||
					!TryGetRgbaObjectParameter(parameters, "upperRight", out var upperRight, out error))
				{
					return CreateError(command, error);
				}

				var sprite = regularNode.DrawingValues.Sprite;
				var before = CreateSpriteDrawingPayload(sprite);
				Command.CommandManager.StartCollection();
				try
				{
					sprite.Color.SetValue(Data.RendererValues.SpriteParamater.ColorType.Fixed);
					SetColor(sprite.Color_Fixed_LL, lowerLeft);
					SetColor(sprite.Color_Fixed_LR, lowerRight);
					SetColor(sprite.Color_Fixed_UL, upperLeft);
					SetColor(sprite.Color_Fixed_UR, upperRight);
				}
				finally
				{
					Command.CommandManager.EndCollection();
				}

				var after = CreateSpriteDrawingPayload(sprite);
				return CreateOk(command, new JObject
				{
					["automationNodeId"] = automationNodeId,
					["name"] = regularNode.Name.Value,
					["before"] = before,
					["after"] = after,
					["drawingParameters"] = CreateNodeDrawingParametersPayload(regularNode, automationNodeId)
				});
			}

			if (command == "set_node_alpha_blend_by_automation_id")
			{
				if (!TryGetWritableDataNode(command, parameters, out var automationNodeId, out var regularNode, out var error) ||
					!TryGetStringParameter(parameters, "alphaBlend", out var alphaBlendText, out error) ||
					!TryParseAlphaBlend(alphaBlendText, out var alphaBlend, out error))
				{
					return CreateError(command, error);
				}

				var target = regularNode.RendererCommonValues.AlphaBlend;
				var before = CreateEnumPayload(target);
				target.SetValue(alphaBlend);
				var after = CreateEnumPayload(target);
				return CreateOk(command, new JObject
				{
					["automationNodeId"] = automationNodeId,
					["name"] = regularNode.Name.Value,
					["before"] = before,
					["after"] = after,
					["rendererParameters"] = CreateNodeRendererParametersPayload(regularNode, automationNodeId)
				});
			}

			if (command == "set_node_z_write_by_automation_id")
			{
				if (!TryGetWritableDataNode(command, parameters, out var automationNodeId, out var regularNode, out var error) ||
					!TryGetBooleanParameter(parameters, "zWrite", out var zWrite, out error))
				{
					return CreateError(command, error);
				}

				var target = regularNode.RendererCommonValues.ZWrite;
				var before = target.Value;
				target.SetValue(zWrite);
				var after = target.Value;
				return CreateOk(command, new JObject
				{
					["automationNodeId"] = automationNodeId,
					["name"] = regularNode.Name.Value,
					["before"] = before,
					["after"] = after,
					["rendererParameters"] = CreateNodeRendererParametersPayload(regularNode, automationNodeId)
				});
			}

			if (command == "set_node_z_test_by_automation_id")
			{
				if (!TryGetWritableDataNode(command, parameters, out var automationNodeId, out var regularNode, out var error) ||
					!TryGetBooleanParameter(parameters, "zTest", out var zTest, out error))
				{
					return CreateError(command, error);
				}

				var target = regularNode.RendererCommonValues.ZTest;
				var before = target.Value;
				target.SetValue(zTest);
				var after = target.Value;
				return CreateOk(command, new JObject
				{
					["automationNodeId"] = automationNodeId,
					["name"] = regularNode.Name.Value,
					["before"] = before,
					["after"] = after,
					["rendererParameters"] = CreateNodeRendererParametersPayload(regularNode, automationNodeId)
				});
			}

			if (command == "set_node_renderer_type_by_automation_id")
			{
				if (!TryGetWritableDataNode(command, parameters, out var automationNodeId, out var regularNode, out var error) ||
					!TryGetStringParameter(parameters, "rendererType", out var rendererTypeText, out error) ||
					!TryParseRendererType(rendererTypeText, out var rendererType, out error))
				{
					return CreateError(command, error);
				}

				var target = regularNode.DrawingValues.Type;
				var before = CreateEnumPayload(target);
				target.SetValue(rendererType);
				var after = CreateEnumPayload(target);
				return CreateOk(command, new JObject
				{
					["automationNodeId"] = automationNodeId,
					["name"] = regularNode.Name.Value,
					["before"] = before,
					["after"] = after,
					["drawingParameters"] = CreateNodeDrawingParametersPayload(regularNode, automationNodeId)
				});
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

		static string NormalizeAutomationWorkspaceRoot(string workspaceRoot)
		{
			if (string.IsNullOrWhiteSpace(workspaceRoot))
			{
				return null;
			}

			var fullPath = Path.GetFullPath(workspaceRoot);
			return TrimEndingDirectorySeparator(fullPath);
		}

		bool TryValidateWorkspacePath(string path, out string fullPath, out string workspaceRelativePath, out string error)
		{
			fullPath = null;
			workspaceRelativePath = null;
			error = null;

			if (string.IsNullOrEmpty(automationWorkspaceRoot))
			{
				error = "automation workspace is not configured";
				return false;
			}

			if (!Directory.Exists(automationWorkspaceRoot))
			{
				error = "automation workspace is not found";
				return false;
			}

			if (string.IsNullOrWhiteSpace(path))
			{
				error = "path must not be empty";
				return false;
			}

			if (HasParentDirectoryTraversal(path))
			{
				error = "path must not contain parent directory traversal";
				return false;
			}

			fullPath = Path.IsPathRooted(path)
				? Path.GetFullPath(path)
				: Path.GetFullPath(Path.Combine(automationWorkspaceRoot, path));
			fullPath = TrimEndingDirectorySeparator(fullPath);

			if (!IsPathUnderWorkspace(fullPath, automationWorkspaceRoot))
			{
				error = "path must be inside automation workspace";
				fullPath = null;
				return false;
			}

			workspaceRelativePath = Path.GetRelativePath(automationWorkspaceRoot, fullPath).Replace(Path.DirectorySeparatorChar, '/');
			if (workspaceRelativePath == ".")
			{
				workspaceRelativePath = string.Empty;
			}

			return true;
		}

		bool TryValidateWorkspaceProjectPath(string path, bool mustExist, out string fullPath, out string workspaceRelativePath, out string error)
		{
			if (!TryValidateWorkspacePath(path, out fullPath, out workspaceRelativePath, out error))
			{
				return false;
			}

			if (!string.Equals(Path.GetExtension(fullPath), ".efkefc", StringComparison.OrdinalIgnoreCase))
			{
				error = "path extension must be .efkefc";
				fullPath = null;
				workspaceRelativePath = null;
				return false;
			}

			if (mustExist && !File.Exists(fullPath))
			{
				error = "project file is not found";
				fullPath = null;
				workspaceRelativePath = null;
				return false;
			}

			return true;
		}

		bool TryValidateWorkspaceRuntimeEffectPath(string path, out string fullPath, out string workspaceRelativePath, out string error)
		{
			if (!TryValidateWorkspacePath(path, out fullPath, out workspaceRelativePath, out error))
			{
				return false;
			}

			if (!string.Equals(Path.GetExtension(fullPath), ".efk", StringComparison.OrdinalIgnoreCase))
			{
				error = "path extension must be .efk";
				fullPath = null;
				workspaceRelativePath = null;
				return false;
			}

			return true;
		}

		static bool HasParentDirectoryTraversal(string path)
		{
			var parts = path.Split(new[] { Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar }, StringSplitOptions.RemoveEmptyEntries);
			for (int i = 0; i < parts.Length; i++)
			{
				if (parts[i] == "..")
				{
					return true;
				}
			}

			return false;
		}

		static bool IsPathUnderWorkspace(string fullPath, string workspaceRoot)
		{
			if (string.Equals(fullPath, workspaceRoot, StringComparison.OrdinalIgnoreCase))
			{
				return true;
			}

			var rootWithSeparator = workspaceRoot + Path.DirectorySeparatorChar;
			return fullPath.StartsWith(rootWithSeparator, StringComparison.OrdinalIgnoreCase);
		}

		static string TrimEndingDirectorySeparator(string path)
		{
			if (string.IsNullOrEmpty(path))
			{
				return path;
			}

			var root = Path.GetPathRoot(path);
			if (!string.IsNullOrEmpty(root) && string.Equals(path, root, StringComparison.OrdinalIgnoreCase))
			{
				return root;
			}

			var trimmed = path.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
			if (!string.IsNullOrEmpty(root) && string.IsNullOrEmpty(trimmed))
			{
				return root;
			}

			return trimmed;
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

		JObject CreateWorkspaceStatusPayload()
		{
			return new JObject
			{
				["enabled"] = !string.IsNullOrEmpty(automationWorkspaceRoot),
				["exists"] = !string.IsNullOrEmpty(automationWorkspaceRoot) && Directory.Exists(automationWorkspaceRoot)
			};
		}

		static JObject CreateBridgeCapabilitiesPayload()
		{
			var commands = new JArray();
			for (int i = 0; i < AllowedCommands.Length; i++)
			{
				commands.Add(AllowedCommands[i]);
			}

			return new JObject
			{
				["bridgeName"] = "Effekseer Automation Bridge",
				["protocolVersion"] = 1,
				["commands"] = commands
			};
		}

		static JObject ExecuteViewerCommand(string command, Func<bool> viewerCommand)
		{
			if (!viewerCommand())
			{
				return CreateError(command, "viewer command failed");
			}

			return CreateOk(command, CreateViewerStatusPayload());
		}

		static JObject CreateViewerStatusPayload()
		{
			var viewer = Effekseer.GUI.Manager.Viewer;
			return new JObject
			{
				["running"] = true,
				["viewer"] = viewer != null ? new JObject
				{
					["is_playing"] = viewer.IsPlaying,
					["is_paused"] = viewer.IsPaused
				} : null,
				["status"] = CreateStatusPayload()
			};
		}

		static JObject CreateNodeBasicInfoPayload(Data.NodeBase node, string automationNodeId)
		{
			var parentAutomationNodeId = node.Parent != null ? FindAutomationNodeId(node.Parent) : null;
			return new JObject
			{
				["automationNodeId"] = automationNodeId,
				["name"] = node.Name.Value,
				["editorNodeId"] = node.EditorNodeId,
				["childCount"] = node.Children.Count,
				["parentAutomationNodeId"] = parentAutomationNodeId,
				["isSelected"] = node == Core.SelectedNode,
				["isRendered"] = node.IsRendered.Value,
				["nodeType"] = node is Data.NodeRoot ? "root" : "node",
				["className"] = node.GetType().Name,
				["layerNumber"] = node.GetLayerNumber(),
				["deepestLayerNumberInChildren"] = node.GetDeepestLayerNumberInChildren()
			};
		}

		static JObject CreateNodeParameterGroupsPayload(Data.NodeBase node, string automationNodeId)
		{
			var groups = new JArray();
			groups.Add("node_base");

			if (node is Data.Node)
			{
				groups.Add("common");
				groups.Add("generation");
				groups.Add("location");
				groups.Add("rotation");
				groups.Add("scale");
				groups.Add("local_force_field");
				groups.Add("depth");
				groups.Add("renderer_common");
				groups.Add("drawing");
				groups.Add("sound");
				groups.Add("advanced_render");
				groups.Add("kill_rules");
				groups.Add("collisions");
				groups.Add("gpu_particles");
			}

			return new JObject
			{
				["automationNodeId"] = automationNodeId,
				["name"] = node.Name.Value,
				["groups"] = groups
			};
		}

		static JObject CreateNodeBaseParametersPayload(Data.NodeBase node, string automationNodeId)
		{
			return new JObject
			{
				["automationNodeId"] = automationNodeId,
				["name"] = node.Name.Value,
				["isRendered"] = node.IsRendered.Value,
				["childCount"] = node.Children.Count,
				["nodeType"] = node is Data.NodeRoot ? "root" : "node",
				["className"] = node.GetType().Name
			};
		}

		static JObject CreateNodeGenerationParametersPayload(Data.Node node, string automationNodeId)
		{
			var common = node.CommonValues;
			var generation = common.Generation;
			return new JObject
			{
				["automationNodeId"] = automationNodeId,
				["name"] = node.Name.Value,
				["maxGeneration"] = CreateIntWithInfinitePayload(common.MaxGeneration),
				["life"] = CreateIntWithRandomPayload(common.Life),
				["generation"] = new JObject
				{
					["timing"] = CreateEnumPayload(generation.Timing),
					["generationTime"] = CreateFloatWithRandomPayload(generation.GenerationTime),
					["generationTimeOffset"] = CreateFloatWithRandomPayload(generation.GenerationTimeOffset),
					["toStartGeneration"] = CreateEnumPayload(generation.ToStartGeneration),
					["toStopGeneration"] = CreateEnumPayload(generation.ToStopGeneration),
					["trigger"] = CreateEnumPayload(generation.Trigger),
					["triggerCount"] = CreateIntWithRandomPayload(generation.TriggerCount)
				},
				["parentEffect"] = new JObject
				{
					["location"] = CreateEnumPayload(common.LocationEffectType),
					["rotation"] = CreateEnumPayload(common.RotationEffectType),
					["scale"] = CreateEnumPayload(common.ScaleEffectType)
				},
				["removal"] = new JObject
				{
					["whenLifeIsExtinct"] = common.Removal.WhenLifeIsExtinct.Value,
					["whenParentIsRemoved"] = common.Removal.WhenParentIsRemoved.Value,
					["whenAllChildrenAreRemoved"] = common.Removal.WhenAllChildrenAreRemoved.Value,
					["triggerToRemove"] = CreateEnumPayload(common.Removal.TriggerToRemove)
				}
			};
		}

		static JObject CreateNodeTransformParametersPayload(Data.Node node, string automationNodeId)
		{
			return new JObject
			{
				["automationNodeId"] = automationNodeId,
				["name"] = node.Name.Value,
				["location"] = CreateLocationParametersPayload(node.LocationValues),
				["rotation"] = CreateRotationParametersPayload(node.RotationValues),
				["scale"] = CreateScaleParametersPayload(node.ScalingValues)
			};
		}

		static JObject CreateNodeDrawingParametersPayload(Data.Node node, string automationNodeId)
		{
			var values = node.DrawingValues;
			return new JObject
			{
				["automationNodeId"] = automationNodeId,
				["name"] = node.Name.Value,
				["rendererType"] = CreateEnumPayload(values.Type),
				["textureUVType"] = CreateTextureUVTypePayload(values.TextureUVType),
				["trailSmoothing"] = CreateEnumPayload(values.TrailSmoothing),
				["trailTimeSource"] = CreateEnumPayload(values.TrailTimeSource),
				["colorAll"] = CreateStandardColorPayload(values.ColorAll),
				["trackColors"] = new JObject
				{
					["left"] = CreateStandardColorPayload(values.TrailColorLeft),
					["leftMiddle"] = CreateStandardColorPayload(values.TrailColorLeftMiddle),
					["center"] = CreateStandardColorPayload(values.TrailColorCenter),
					["centerMiddle"] = CreateStandardColorPayload(values.TrailColorCenterMiddle),
					["right"] = CreateStandardColorPayload(values.TrailColorRight),
					["rightMiddle"] = CreateStandardColorPayload(values.TrailColorRightMiddle)
				},
				["sprite"] = CreateSpriteDrawingPayload(values.Sprite),
				["ribbon"] = CreateRibbonDrawingPayload(values.Ribbon),
				["ring"] = CreateRingDrawingPayload(values.Ring),
				["track"] = CreateTrackDrawingPayload(values.Track),
				["model"] = CreateModelDrawingPayload(values.Model),
				["notes"] = new JArray
				{
					"Only allowlisted drawing fields are expanded.",
					"Complex color easing, random color, gradients, and model/procedural data are summarized."
				}
			};
		}

		static JObject CreateNodeRendererParametersPayload(Data.Node node, string automationNodeId)
		{
			var values = node.RendererCommonValues;
			return new JObject
			{
				["automationNodeId"] = automationNodeId,
				["name"] = node.Name.Value,
				["material"] = new JObject
				{
					["type"] = CreateEnumPayload(values.Material),
					["materialFile"] = CreatePathReferencePayload(values.MaterialFile.Path),
					["emissiveScaling"] = CreateFloatPayload(values.EmissiveScaling),
					["distortionIntensity"] = CreateFloatPayload(values.DistortionIntensity)
				},
				["textures"] = new JObject
				{
					["colorTexture"] = new JObject
					{
						["reference"] = CreatePathReferencePayload(values.ColorTexture),
						["filter"] = CreateEnumPayload(values.Filter),
						["wrap"] = CreateEnumPayload(values.Wrap)
					},
					["normalTexture"] = new JObject
					{
						["reference"] = CreatePathReferencePayload(values.NormalTexture),
						["filter"] = CreateEnumPayload(values.Filter2),
						["wrap"] = CreateEnumPayload(values.Wrap2)
					}
				},
				["blend"] = new JObject
				{
					["alphaBlend"] = CreateEnumPayload(values.AlphaBlend),
					["zWrite"] = values.ZWrite.Value,
					["zTest"] = values.ZTest.Value
				},
				["fade"] = new JObject
				{
					["fadeInType"] = CreateEnumPayload(values.FadeInType),
					["fadeIn"] = CreateFadePayload(values.FadeIn),
					["fadeOutType"] = CreateEnumPayload(values.FadeOutType),
					["fadeOut"] = CreateFadePayload(values.FadeOut)
				},
				["uv"] = CreateUVPayload(values),
				["colorInheritType"] = CreateEnumPayload(values.ColorInheritType),
				["customData"] = new JObject
				{
					["customData1"] = CreateCustomDataPayload(values.CustomData1),
					["customData2"] = CreateCustomDataPayload(values.CustomData2)
				},
				["notes"] = new JArray
				{
					"Texture and material absolute paths are never returned.",
					"Path references are reported as empty or set_omitted in this read-only spike."
				}
			};
		}

		static JObject CreateTextureUVTypePayload(Data.TextureUVTypeParameter value)
		{
			return new JObject
			{
				["type"] = CreateEnumPayload(value.Type),
				["tileLength"] = CreateFloatPayload(value.TileLength),
				["tileEdgeHead"] = CreateIntPayload(value.TileEdgeHead),
				["tileEdgeTail"] = CreateIntPayload(value.TileEdgeTail),
				["tileLoopingArea"] = CreateVector2DPayload(value.TileLoopingArea)
			};
		}

		static JObject CreateStandardColorPayload(Data.StandardColor value)
		{
			return new JObject
			{
				["type"] = CreateEnumPayload(value.Type),
				["fixed"] = CreateColorPayload(value.Fixed),
				["random"] = CreateComplexSummaryPayload("color_random", "Random color values are summarized in this read-only spike"),
				["easing"] = CreateComplexSummaryPayload("color_easing", "Color easing values are summarized in this read-only spike"),
				["fcurve"] = CreateComplexSummaryPayload("color_fcurve", "Color FCurve values are not expanded in this read-only spike"),
				["gradient"] = CreateComplexSummaryPayload("gradient", "Gradient stops are not expanded in this read-only spike")
			};
		}

		static JObject CreateSpriteDrawingPayload(Data.RendererValues.SpriteParamater value)
		{
			return new JObject
			{
				["renderingOrder"] = CreateEnumPayload(value.RenderingOrder),
				["billboard"] = CreateEnumPayload(value.Billboard),
				["colorType"] = CreateEnumPayload(value.Color),
				["fixedColors"] = new JObject
				{
					["lowerLeft"] = CreateColorPayload(value.Color_Fixed_LL),
					["lowerRight"] = CreateColorPayload(value.Color_Fixed_LR),
					["upperLeft"] = CreateColorPayload(value.Color_Fixed_UL),
					["upperRight"] = CreateColorPayload(value.Color_Fixed_UR)
				},
				["positionType"] = CreateEnumPayload(value.Position),
				["fixedPositions"] = new JObject
				{
					["lowerLeft"] = CreateVector2DPayload(value.Position_Fixed_LL),
					["lowerRight"] = CreateVector2DPayload(value.Position_Fixed_LR),
					["upperLeft"] = CreateVector2DPayload(value.Position_Fixed_UL),
					["upperRight"] = CreateVector2DPayload(value.Position_Fixed_UR)
				},
				["colorTexture"] = CreatePathReferencePayload(value.ColorTexture)
			};
		}

		static JObject CreateRibbonDrawingPayload(Data.RendererValues.RibbonParamater value)
		{
			return new JObject
			{
				["viewpointDependent"] = value.ViewpointDependent.Value,
				["colorAllType"] = CreateEnumPayload(value.ColorAll),
				["colorAllFixed"] = CreateColorPayload(value.ColorAll_Fixed),
				["colorType"] = CreateEnumPayload(value.Color),
				["fixedColors"] = new JObject
				{
					["left"] = CreateColorPayload(value.Color_Fixed_L),
					["right"] = CreateColorPayload(value.Color_Fixed_R)
				},
				["positionType"] = CreateEnumPayload(value.Position),
				["fixedPositions"] = new JObject
				{
					["left"] = CreateFloatPayload(value.Position_Fixed_L),
					["right"] = CreateFloatPayload(value.Position_Fixed_R)
				},
				["splineDivision"] = CreateIntPayload(value.SplineDivision),
				["colorTexture"] = CreatePathReferencePayload(value.ColorTexture)
			};
		}

		static JObject CreateRingDrawingPayload(Data.RendererValues.RingParamater value)
		{
			return new JObject
			{
				["ringShape"] = new JObject
				{
					["type"] = CreateEnumPayload(value.RingShape.Type),
					["crescent"] = new JObject
					{
						["startingFade"] = CreateFloatPayload(value.RingShape.Crescent.StartingFade),
						["endingFade"] = CreateFloatPayload(value.RingShape.Crescent.EndingFade),
						["startingAngleType"] = CreateEnumPayload(value.RingShape.Crescent.StartingAngle),
						["startingAngleFixed"] = CreateFloatPayload(value.RingShape.Crescent.StartingAngle_Fixed),
						["endingAngleType"] = CreateEnumPayload(value.RingShape.Crescent.EndingAngle),
						["endingAngleFixed"] = CreateFloatPayload(value.RingShape.Crescent.EndingAngle_Fixed)
					}
				},
				["renderingOrder"] = CreateEnumPayload(value.RenderingOrder),
				["billboard"] = CreateEnumPayload(value.Billboard),
				["vertexCount"] = CreateIntPayload(value.VertexCount),
				["outerType"] = CreateEnumPayload(value.Outer),
				["outerFixed"] = CreateVector2DPayload(value.Outer_Fixed.Location),
				["innerType"] = CreateEnumPayload(value.Inner),
				["innerFixed"] = CreateVector2DPayload(value.Inner_Fixed.Location),
				["centerRatioType"] = CreateEnumPayload(value.CenterRatio),
				["centerRatioFixed"] = CreateFloatPayload(value.CenterRatio_Fixed),
				["outerColorType"] = CreateEnumPayload(value.OuterColor),
				["outerColorFixed"] = CreateColorPayload(value.OuterColor_Fixed),
				["centerColorType"] = CreateEnumPayload(value.CenterColor),
				["centerColorFixed"] = CreateColorPayload(value.CenterColor_Fixed),
				["innerColorType"] = CreateEnumPayload(value.InnerColor),
				["innerColorFixed"] = CreateColorPayload(value.InnerColor_Fixed),
				["colorTexture"] = CreatePathReferencePayload(value.ColorTexture)
			};
		}

		static JObject CreateTrackDrawingPayload(Data.RendererValues.TrackParameter value)
		{
			return new JObject
			{
				["trackSizeForType"] = CreateEnumPayload(value.TrackSizeFor),
				["trackSizeForFixed"] = CreateFloatPayload(value.TrackSizeFor_Fixed),
				["trackSizeMiddleType"] = CreateEnumPayload(value.TrackSizeMiddle),
				["trackSizeMiddleFixed"] = CreateFloatPayload(value.TrackSizeMiddle_Fixed),
				["trackSizeBackType"] = CreateEnumPayload(value.TrackSizeBack),
				["trackSizeBackFixed"] = CreateFloatPayload(value.TrackSizeBack_Fixed),
				["splineDivision"] = CreateIntPayload(value.SplineDivision),
				["note"] = "Track color values are exposed through trackColors at the drawing payload root."
			};
		}

		static JObject CreateModelDrawingPayload(Data.RendererValues.ModelParamater value)
		{
			return new JObject
			{
				["modelReference"] = CreateEnumPayload(value.ModelReference),
				["model"] = CreatePathReferencePayload(value.Model),
				["externalModelIndex"] = CreateIntPayload(value.ExternalModelIndex),
				["billboard"] = CreateEnumPayload(value.Billboard),
				["culling"] = CreateEnumPayload(value.Culling),
				["proceduralModel"] = CreateComplexSummaryPayload("procedural_model", "Procedural model data is summarized in this read-only spike")
			};
		}

		static JObject CreateFadePayload(Data.RendererCommonValues.FadeInParamater value)
		{
			return new JObject
			{
				["frame"] = CreateFloatPayload(value.Frame),
				["startSpeed"] = CreateEnumPayload(value.StartSpeed),
				["endSpeed"] = CreateEnumPayload(value.EndSpeed)
			};
		}

		static JObject CreateFadePayload(Data.RendererCommonValues.FadeOutParamater value)
		{
			return new JObject
			{
				["frame"] = CreateFloatPayload(value.Frame),
				["startSpeed"] = CreateEnumPayload(value.StartSpeed),
				["endSpeed"] = CreateEnumPayload(value.EndSpeed)
			};
		}

		static JObject CreateUVPayload(Data.RendererCommonValues values)
		{
			return new JObject
			{
				["type"] = CreateEnumPayload(values.UV),
				["textureReferenceTarget"] = CreateEnumPayload(values.UVTextureReferenceTarget),
				["flipHorizontalProbability"] = CreateIntPayload(values.UVFlipHorizontalProbability),
				["fixed"] = new JObject
				{
					["start"] = CreateVector2DPayload(values.UVFixed.Start),
					["size"] = CreateVector2DPayload(values.UVFixed.Size)
				},
				["animation"] = new JObject
				{
					["start"] = CreateVector2DPayload(values.UVAnimation.AnimationParams.Start),
					["size"] = CreateVector2DPayload(values.UVAnimation.AnimationParams.Size),
					["frameLength"] = CreateIntWithInfinitePayload(values.UVAnimation.AnimationParams.FrameLength),
					["frameCountX"] = CreateIntPayload(values.UVAnimation.AnimationParams.FrameCountX),
					["frameCountY"] = CreateIntPayload(values.UVAnimation.AnimationParams.FrameCountY),
					["loopType"] = CreateEnumPayload(values.UVAnimation.AnimationParams.LoopType),
					["startSheet"] = CreateIntWithRandomPayload(values.UVAnimation.AnimationParams.StartSheet),
					["flipbookInterpolationType"] = CreateEnumPayload(values.UVAnimation.FlipbookInterpolationType)
				},
				["scroll"] = new JObject
				{
					["start"] = CreateVector2DWithRandomPayload(values.UVScroll.Start),
					["size"] = CreateVector2DWithRandomPayload(values.UVScroll.Size),
					["speed"] = CreateVector2DWithRandomPayload(values.UVScroll.Speed)
				},
				["fcurve"] = CreateComplexSummaryPayload("uv_fcurve", "UV FCurve values are not expanded in this read-only spike")
			};
		}

		static JObject CreateCustomDataPayload(Data.CustomDataParameter value)
		{
			return new JObject
			{
				["type"] = CreateEnumPayload(value.CustomData),
				["fixed"] = CreateVector2DPayload(value.Fixed),
				["fixed4"] = CreateVector4DPayload(value.Fixed4),
				["random"] = CreateComplexSummaryPayload("custom_data_random", "Custom data random/easing/FCurve values are summarized in this read-only spike")
			};
		}

		static JObject CreateLocationParametersPayload(Data.LocationValues values)
		{
			return new JObject
			{
				["type"] = CreateEnumPayload(values.Type),
				["fixed"] = new JObject
				{
					["location"] = CreateVector3DPayload(values.Fixed.Location)
				},
				["pva"] = new JObject
				{
					["location"] = CreateVector3DWithRandomPayload(values.PVA.Location),
					["velocity"] = CreateVector3DWithRandomPayload(values.PVA.Velocity),
					["acceleration"] = CreateVector3DWithRandomPayload(values.PVA.Acceleration)
				},
				["easing"] = CreateVector3DEasingPayload(values.Easing),
				["locationFCurve"] = CreateComplexSummaryPayload("fcurve", "FCurve values are not expanded in this read-only spike"),
				["nurbsCurve"] = new JObject
				{
					["summary"] = "NURBS curve file path is intentionally omitted",
					["scale"] = CreateFloatPayload(values.NurbsCurve.Scale),
					["moveSpeed"] = CreateFloatPayload(values.NurbsCurve.MoveSpeed),
					["loopType"] = CreateEnumPayload(values.NurbsCurve.LoopType)
				},
				["viewOffset"] = new JObject
				{
					["distance"] = CreateFloatWithRandomPayload(values.ViewOffset.Distance)
				}
			};
		}

		static JObject CreateRotationParametersPayload(Data.RotationValues values)
		{
			return new JObject
			{
				["type"] = CreateEnumPayload(values.Type),
				["fixed"] = new JObject
				{
					["rotation"] = CreateVector3DPayload(values.Fixed.Rotation)
				},
				["pva"] = new JObject
				{
					["rotation"] = CreateVector3DWithRandomPayload(values.PVA.Rotation),
					["velocity"] = CreateVector3DWithRandomPayload(values.PVA.Velocity),
					["acceleration"] = CreateVector3DWithRandomPayload(values.PVA.Acceleration)
				},
				["easing"] = CreateVector3DEasingPayload(values.Easing),
				["axisPVA"] = new JObject
				{
					["axis"] = CreateVector3DWithRandomPayload(values.AxisPVA.Axis),
					["rotation"] = CreateFloatWithRandomPayload(values.AxisPVA.Rotation),
					["velocity"] = CreateFloatWithRandomPayload(values.AxisPVA.Velocity),
					["acceleration"] = CreateFloatWithRandomPayload(values.AxisPVA.Acceleration)
				},
				["axisEasing"] = new JObject
				{
					["axis"] = CreateVector3DWithRandomPayload(values.AxisEasing.Axis),
					["easing"] = CreateFloatEasingPayload(values.AxisEasing.Easing)
				},
				["rotationFCurve"] = CreateComplexSummaryPayload("fcurve", "FCurve values are not expanded in this read-only spike"),
				["velocity"] = new JObject
				{
					["axis"] = CreateEnumPayload(values.Velocity.Axis)
				}
			};
		}

		static JObject CreateScaleParametersPayload(Data.ScaleValues values)
		{
			return new JObject
			{
				["type"] = CreateEnumPayload(values.Type),
				["fixed"] = new JObject
				{
					["scale"] = CreateVector3DPayload(values.Fixed.Scale)
				},
				["pva"] = new JObject
				{
					["scale"] = CreateVector3DWithRandomPayload(values.PVA.Scale),
					["velocity"] = CreateVector3DWithRandomPayload(values.PVA.Velocity),
					["acceleration"] = CreateVector3DWithRandomPayload(values.PVA.Acceleration)
				},
				["easing"] = CreateVector3DEasingPayload(values.Easing),
				["singlePVA"] = new JObject
				{
					["scale"] = CreateFloatWithRandomPayload(values.SinglePVA.Scale),
					["velocity"] = CreateFloatWithRandomPayload(values.SinglePVA.Velocity),
					["acceleration"] = CreateFloatWithRandomPayload(values.SinglePVA.Acceleration)
				},
				["singleEasing"] = CreateFloatEasingPayload(values.SingleEasing),
				["fcurve"] = CreateComplexSummaryPayload("fcurve", "FCurve values are not expanded in this read-only spike"),
				["singleFCurve"] = CreateComplexSummaryPayload("fcurve", "FCurve values are not expanded in this read-only spike")
			};
		}

		static JObject CreateFloatPayload(Data.Value.Float value)
		{
			return new JObject
			{
				["value"] = value.Value
			};
		}

		static JObject CreateIntPayload(Data.Value.Int value)
		{
			return new JObject
			{
				["value"] = value.Value
			};
		}

		static JObject CreateFloatWithRandomPayload(Data.Value.FloatWithRandom value)
		{
			return new JObject
			{
				["center"] = value.Center,
				["min"] = value.Min,
				["max"] = value.Max,
				["amplitude"] = value.Amplitude,
				["drawnAs"] = value.DrawnAs.ToString()
			};
		}

		static JObject CreateIntWithRandomPayload(Data.Value.IntWithRandom value)
		{
			return new JObject
			{
				["center"] = value.Center,
				["min"] = value.Min,
				["max"] = value.Max,
				["amplitude"] = value.Amplitude,
				["drawnAs"] = value.DrawnAs.ToString()
			};
		}

		static JObject CreateIntWithInfinitePayload(Data.Value.IntWithInifinite value)
		{
			return new JObject
			{
				["value"] = value.Value.Value,
				["infinite"] = value.Infinite.Value
			};
		}

		static JObject CreateVector2DPayload(Data.Value.Vector2D value)
		{
			return new JObject
			{
				["x"] = value.X.Value,
				["y"] = value.Y.Value
			};
		}

		static JObject CreateVector2DWithRandomPayload(Data.Value.Vector2DWithRandom value)
		{
			return new JObject
			{
				["x"] = CreateFloatWithRandomPayload(value.X),
				["y"] = CreateFloatWithRandomPayload(value.Y),
				["drawnAs"] = value.DrawnAs.ToString()
			};
		}

		static JObject CreateVector3DPayload(Data.Value.Vector3D value)
		{
			return new JObject
			{
				["x"] = value.X.Value,
				["y"] = value.Y.Value,
				["z"] = value.Z.Value
			};
		}

		static JObject CreateVector3DWithRandomPayload(Data.Value.Vector3DWithRandom value)
		{
			return new JObject
			{
				["x"] = CreateFloatWithRandomPayload(value.X),
				["y"] = CreateFloatWithRandomPayload(value.Y),
				["z"] = CreateFloatWithRandomPayload(value.Z),
				["drawnAs"] = value.DrawnAs.ToString()
			};
		}

		static JObject CreateVector4DPayload(Data.Value.Vector4D value)
		{
			return new JObject
			{
				["x"] = value.X.Value,
				["y"] = value.Y.Value,
				["z"] = value.Z.Value,
				["w"] = value.W.Value
			};
		}

		static JObject CreateColorPayload(Data.Value.Color value)
		{
			return new JObject
			{
				["r"] = value.R.Value,
				["g"] = value.G.Value,
				["b"] = value.B.Value,
				["a"] = value.A.Value,
				["colorSpace"] = value.ColorSpace.ToString()
			};
		}

		static JObject CreatePathReferencePayload(Data.Value.Path value)
		{
			var hasValue = !string.IsNullOrEmpty(value.AbsolutePath);
			return new JObject
			{
				["hasValue"] = hasValue,
				["pathStatus"] = hasValue ? "set_omitted" : "empty",
				["summary"] = hasValue ? "Path is set but omitted to avoid exposing absolute or workspace-outside paths" : "No path is set"
			};
		}

		static JObject CreateEnumPayload<T>(Data.Value.Enum<T> value)
			where T : struct, IComparable, IFormattable, IConvertible
		{
			return new JObject
			{
				["value"] = value.Value.ToString(),
				["valueId"] = value.GetValueAsInt()
			};
		}

		static JObject CreateFloatEasingPayload(Data.FloatEasingParamater value)
		{
			return new JObject
			{
				["type"] = CreateEnumPayload(value.Type),
				["start"] = CreateFloatWithRandomPayload(value.Start),
				["end"] = CreateFloatWithRandomPayload(value.End),
				["startSpeed"] = CreateEnumPayload(value.StartSpeed),
				["endSpeed"] = CreateEnumPayload(value.EndSpeed),
				["isMiddleEnabled"] = value.IsMiddleEnabled.Value,
				["middle"] = CreateFloatWithRandomPayload(value.Middle),
				["isRandomGroupEnabled"] = value.IsRandomGroupEnabled.Value,
				["randomGroupA"] = value.RandomGroupA.Value,
				["isIndividualTypeEnabled"] = value.IsIndividualTypeEnabled.Value,
				["typeA"] = CreateEnumPayload(value.Type_A)
			};
		}

		static JObject CreateVector3DEasingPayload(Data.Vector3DEasingParamater value)
		{
			return new JObject
			{
				["type"] = CreateEnumPayload(value.Type),
				["start"] = CreateVector3DWithRandomPayload(value.Start),
				["end"] = CreateVector3DWithRandomPayload(value.End),
				["startSpeed"] = CreateEnumPayload(value.StartSpeed),
				["endSpeed"] = CreateEnumPayload(value.EndSpeed),
				["isMiddleEnabled"] = value.IsMiddleEnabled.Value,
				["middle"] = CreateVector3DWithRandomPayload(value.Middle),
				["isRandomGroupEnabled"] = value.IsRandomGroupEnabled.Value,
				["randomGroup"] = new JObject
				{
					["x"] = value.RandomGroupX.Value,
					["y"] = value.RandomGroupY.Value,
					["z"] = value.RandomGroupZ.Value
				},
				["isIndividualTypeEnabled"] = value.IsIndividualTypeEnabled.Value,
				["individualType"] = new JObject
				{
					["x"] = CreateEnumPayload(value.TypeX),
					["y"] = CreateEnumPayload(value.TypeY),
					["z"] = CreateEnumPayload(value.TypeZ)
				}
			};
		}

		static JObject CreateComplexSummaryPayload(string kind, string summary)
		{
			return new JObject
			{
				["kind"] = kind,
				["summary"] = summary
			};
		}

		static bool TryGetWritableDataNode(string command, JObject parameters, out string automationNodeId, out Data.Node node, out string error)
		{
			automationNodeId = null;
			node = null;

			if (!TryGetStringParameter(parameters, "automationNodeId", out automationNodeId, out error))
			{
				return false;
			}

			var found = FindNodeByAutomationNodeId(automationNodeId, out error);
			if (found == null)
			{
				return false;
			}

			if (!(found is Data.Node regularNode))
			{
				error = $"{command} requires a regular node";
				return false;
			}

			node = regularNode;
			return true;
		}

		static bool TryGetVector3Parameters(JObject parameters, out float x, out float y, out float z, out string error)
		{
			x = 0;
			y = 0;
			z = 0;

			return TryGetFiniteFloatParameter(parameters, "x", -MaxAutomationFloatAbs, MaxAutomationFloatAbs, out x, out error) &&
				TryGetFiniteFloatParameter(parameters, "y", -MaxAutomationFloatAbs, MaxAutomationFloatAbs, out y, out error) &&
				TryGetFiniteFloatParameter(parameters, "z", -MaxAutomationFloatAbs, MaxAutomationFloatAbs, out z, out error);
		}

		struct Rgba
		{
			public int R;
			public int G;
			public int B;
			public int A;
		}

		static bool TryGetRgbaParameters(JObject parameters, out int r, out int g, out int b, out int a, out string error)
		{
			r = 0;
			g = 0;
			b = 0;
			a = 0;

			return TryGetBoundedIntParameter(parameters, "r", 0, 255, out r, out error) &&
				TryGetBoundedIntParameter(parameters, "g", 0, 255, out g, out error) &&
				TryGetBoundedIntParameter(parameters, "b", 0, 255, out b, out error) &&
				TryGetBoundedIntParameter(parameters, "a", 0, 255, out a, out error);
		}

		static bool TryGetRgbaObjectParameter(JObject parameters, string name, out Rgba color, out string error)
		{
			color = new Rgba();
			error = null;

			if (parameters == null || parameters[name] == null)
			{
				error = $"params.{name} is required";
				return false;
			}

			if (parameters[name].Type != JTokenType.Object)
			{
				error = $"params.{name} must be an object";
				return false;
			}

			var obj = (JObject)parameters[name];
			return TryGetBoundedIntParameter(obj, "r", 0, 255, out color.R, out error) &&
				TryGetBoundedIntParameter(obj, "g", 0, 255, out color.G, out error) &&
				TryGetBoundedIntParameter(obj, "b", 0, 255, out color.B, out error) &&
				TryGetBoundedIntParameter(obj, "a", 0, 255, out color.A, out error);
		}

		static bool TryParseAlphaBlend(string value, out Data.AlphaBlendType alphaBlend, out string error)
		{
			alphaBlend = Data.AlphaBlendType.Blend;
			error = null;

			switch ((value ?? string.Empty).Trim().ToLowerInvariant())
			{
				case "opacity":
					alphaBlend = Data.AlphaBlendType.Opacity;
					return true;
				case "blend":
					alphaBlend = Data.AlphaBlendType.Blend;
					return true;
				case "add":
					alphaBlend = Data.AlphaBlendType.Add;
					return true;
				case "sub":
				case "subtract":
					alphaBlend = Data.AlphaBlendType.Sub;
					return true;
				case "mul":
				case "multiply":
					alphaBlend = Data.AlphaBlendType.Mul;
					return true;
				default:
					error = "params.alphaBlend must be one of opacity, blend, add, sub, mul";
					return false;
			}
		}

		static bool TryParseRendererType(string value, out Data.RendererValues.ParamaterType rendererType, out string error)
		{
			rendererType = Data.RendererValues.ParamaterType.Sprite;
			error = null;

			switch ((value ?? string.Empty).Trim().ToLowerInvariant())
			{
				case "none":
					rendererType = Data.RendererValues.ParamaterType.None;
					return true;
				case "sprite":
					rendererType = Data.RendererValues.ParamaterType.Sprite;
					return true;
				case "ribbon":
					rendererType = Data.RendererValues.ParamaterType.Ribbon;
					return true;
				case "ring":
					rendererType = Data.RendererValues.ParamaterType.Ring;
					return true;
				case "track":
					rendererType = Data.RendererValues.ParamaterType.Track;
					return true;
				case "model":
					rendererType = Data.RendererValues.ParamaterType.Model;
					return true;
				default:
					error = "params.rendererType must be one of none, sprite, ribbon, ring, track, model";
					return false;
			}
		}

		static void SetVector3D(Data.Value.Vector3D value, float x, float y, float z)
		{
			Command.CommandManager.StartCollection();
			try
			{
				value.X.SetValue(x);
				value.Y.SetValue(y);
				value.Z.SetValue(z);
			}
			finally
			{
				Command.CommandManager.EndCollection();
			}
		}

		static void SetColor(Data.Value.Color value, Rgba color)
		{
			value.SetValue(color.R, color.G, color.B, color.A);
		}

		static void SetIntWithRandom(Data.Value.IntWithRandom value, int center, int min, int max)
		{
			Command.CommandManager.StartCollection();
			try
			{
				value.SetMin(min);
				value.SetMax(max);
				value.SetCenter(center);
			}
			finally
			{
				Command.CommandManager.EndCollection();
			}
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

		static bool TryGetBoundedIntParameter(JObject parameters, string name, int min, int max, out int value, out string error)
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

			long parsed;
			try
			{
				parsed = parameters.Value<long>(name);
			}
			catch
			{
				error = $"params.{name} is out of range";
				return false;
			}

			if (parsed < min || parsed > max)
			{
				error = $"params.{name} must be between {min} and {max}";
				return false;
			}

			value = (int)parsed;
			return true;
		}

		static bool TryGetFiniteFloatParameter(JObject parameters, string name, float min, float max, out float value, out string error)
		{
			value = 0;
			error = null;

			if (parameters == null || parameters[name] == null)
			{
				error = $"params.{name} is required";
				return false;
			}

			var tokenType = parameters[name].Type;
			if (tokenType != JTokenType.Integer && tokenType != JTokenType.Float)
			{
				error = $"params.{name} must be a finite number";
				return false;
			}

			double parsed;
			try
			{
				parsed = parameters.Value<double>(name);
			}
			catch
			{
				error = $"params.{name} must be a finite number";
				return false;
			}

			if (double.IsNaN(parsed) || double.IsInfinity(parsed) || parsed < min || parsed > max)
			{
				error = $"params.{name} must be a finite number between {min} and {max}";
				return false;
			}

			value = (float)parsed;
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

		static bool TryGetBooleanParameter(JObject parameters, string name, out bool value, out string error)
		{
			value = false;
			error = null;

			if (parameters == null || parameters[name] == null)
			{
				error = $"params.{name} is required";
				return false;
			}

			if (parameters[name].Type != JTokenType.Boolean)
			{
				error = $"params.{name} must be a boolean";
				return false;
			}

			value = parameters.Value<bool>(name);
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

using System;
using System.Diagnostics;
using System.IO;

namespace Effekseer
{
	// The editor owns this process; clients connect over loopback HTTP.
	sealed class McpServerProcess : IDisposable
	{
		System.Diagnostics.Process process;
		static readonly object logLock = new object();

		public void Start(int bridgePort, string workspace)
		{
			var executable = Path.Combine(AppContext.BaseDirectory, "mcp",
				OperatingSystem.IsWindows() ? "effekseer-mcp.exe" : "effekseer-mcp");
			if (!File.Exists(executable))
				throw new FileNotFoundException("MCP runtime is missing. Run Tool/Mcp/scripts/build_bundle.py.", executable);

			var start = new ProcessStartInfo(executable)
			{
				UseShellExecute = false,
				CreateNoWindow = true,
				WorkingDirectory = Path.GetDirectoryName(executable),
				RedirectStandardInput = true,
				RedirectStandardOutput = true,
				RedirectStandardError = true,
			};
			start.Environment["MCP_TRANSPORT"] = "http";
			start.Environment["EFFEKSEER_MCP_MANAGED"] = "1";
			start.Environment["EFFEKSEER_BRIDGE_PORT"] = bridgePort.ToString();
			start.Environment["EFFEKSEER_WORKSPACE"] = workspace;
			start.Environment["EFFEKSEER_EXE"] = Environment.ProcessPath;
			process = new System.Diagnostics.Process { StartInfo = start };
			process.OutputDataReceived += (_, e) => Log(e.Data);
			process.ErrorDataReceived += (_, e) => Log(e.Data);
			process.EnableRaisingEvents = true;
			process.Exited += (_, __) => Log("MCP process stopped. See preceding log messages for startup errors.");
			process.Start();
			process.BeginOutputReadLine();
			process.BeginErrorReadLine();
		}

		internal static void Log(string message)
		{
			if (string.IsNullOrEmpty(message)) return;
			Utils.Logger.Write("MCP: " + message);
			try
			{
				var directory = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Effekseer", "Mcp");
				lock (logLock)
				{
					Directory.CreateDirectory(directory);
					var path = Path.Combine(directory, "server.log");
					if (File.Exists(path) && new FileInfo(path).Length > 2 * 1024 * 1024)
						File.Move(path, path + ".old", overwrite: true);
					File.AppendAllText(path, DateTime.Now.ToString("s") + " " + message + Environment.NewLine);
				}
			}
			catch (IOException) { }
			catch (UnauthorizedAccessException) { }
		}

		public void Dispose()
		{
			if (process == null) return;
			try
			{
				if (!process.HasExited)
				{
					process.StandardInput.Close();
					if (!process.WaitForExit(2000)) process.Kill(entireProcessTree: true);
				}
			}
			catch (InvalidOperationException) { }
			finally { process.Dispose(); process = null; }
		}
	}
}

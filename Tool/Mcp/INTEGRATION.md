# Effekseer built-in MCP (Windows)

`effekseer-mcp` is maintained here as part of the Effekseer repository. The original
repository's tracked source, tests, scripts, sample assets and lock file were
imported; local environments, generated workspaces and editor settings were omitted.

## Use

Start `Dev/release/Effekseer.exe` normally. The editor starts its Automation Bridge
on `127.0.0.1:50123` and the bundled MCP runtime on
`http://127.0.0.1:50124/mcp` (Streamable HTTP). Register that URL once in your MCP
client. Starting the application does not configure clients automatically.

Python and uv are not required on the user's machine. Keep the adjacent `mcp`
directory with the application when copying/distributing it. The runtime exits
when the editor closes, including when the editor process crashes.

The default workspace is `%LOCALAPPDATA%/Effekseer/Mcp/workspace`. Existing files
from the old repository's workspace are not moved. To continue using them, set
`EFFEKSEER_AUTOMATION_WORKSPACE` or pass `--automation-workspace <path>`.

- `--no-mcp` or `EFFEKSEER_MCP_ENABLED=0`: disable automatic MCP and default Bridge.
- `--automation-port <port>` or `EFFEKSEER_AUTOMATION_PORT`: override Bridge port.
- `EFFEKSEER_MCP_PORT`: override HTTP port (default 50124).
- An explicit Bridge port still enables the Bridge with `--no-mcp`.
- Command-line export (`-cui`) starts neither service.
- Only the first editor using these ports serves MCP. Additional editors still
  open normally. Use distinct ports and workspaces for independent MCP sessions.
- Startup failures are recorded in `%LOCALAPPDATA%/Effekseer/Mcp/server.log`.

## Build

Install uv on the build machine, then from the repository root run:

```powershell
python Tool/Mcp/scripts/build_bundle.py
dotnet publish Dev/Editor/Effekseer/Effekseer.csproj -c Release --self-contained -r win-x64
Copy-Item Dev/release/win-x64/publish/* Dev/release/ -Recurse -Force
```

The existing Windows `build.py` packaging flow also builds the runtime. Dependencies
are locked by `Tool/Mcp/uv.lock`. PyInstaller bundles the interpreter, libraries and
SampleEffects. The standalone bundler supports `--output <application-directory>`.
Rebuild the bundle after changing Python source. A plain `dotnet build` rebuilds
only the editor. The automated packaging integration is Windows-only.

```powershell
uv run --project Tool/Mcp --locked pytest Tool/Mcp/tests -q
```

The original MCP README below this directory documents tools and development use;
its standalone startup instructions are unnecessary for the bundled application.

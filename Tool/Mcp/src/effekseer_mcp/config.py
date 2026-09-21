import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from effekseer_mcp.paths import get_project_root, resolve_workspace


@dataclass(frozen=True)
class EffekseerConfig:
    effekseer_exe: str
    effekseer_exe_path: Path | None
    effekseer_exe_exists: bool
    workspace: Path

    def as_dict(self) -> dict[str, str | bool]:
        return {
            "effekseer_exe": self.effekseer_exe,
            "effekseer_exe_exists": self.effekseer_exe_exists,
            "workspace": str(self.workspace),
        }


def load_config() -> EffekseerConfig:
    """Load Effekseer MCP configuration without requiring Effekseer.exe."""
    project_root = get_project_root()
    load_dotenv(project_root / ".env")

    exe = os.getenv("EFFEKSEER_EXE", "")
    workspace_raw = os.getenv("EFFEKSEER_WORKSPACE", "workspace")
    workspace = resolve_workspace(workspace_raw, project_root=project_root)
    exe_path = _resolve_optional_path(exe, project_root)

    return EffekseerConfig(
        effekseer_exe=exe,
        effekseer_exe_path=exe_path,
        effekseer_exe_exists=bool(exe_path and exe_path.exists() and exe_path.is_file()),
        workspace=workspace,
    )


def _resolve_optional_path(raw_path: str, project_root: Path) -> Path | None:
    if not raw_path:
        return None

    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = project_root / path

    return path.resolve(strict=False)

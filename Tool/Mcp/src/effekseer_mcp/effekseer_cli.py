from pathlib import Path

from effekseer_mcp.config import EffekseerConfig, load_config


class EffekseerCli:
    """Thin boundary for future safe Effekseer subprocess execution."""

    def __init__(self, config: EffekseerConfig | None = None) -> None:
        self.config = config or load_config()

    @property
    def executable(self) -> Path | None:
        return self.config.effekseer_exe_path

    def executable_exists(self) -> bool:
        return self.config.effekseer_exe_exists

    def ensure_executable(self) -> Path:
        """Return the executable path or raise before any command execution."""
        if self.executable is None:
            raise FileNotFoundError("EFFEKSEER_EXE is not configured")

        if not self.executable_exists():
            raise FileNotFoundError(f"Effekseer executable not found: {self.executable}")

        return self.executable

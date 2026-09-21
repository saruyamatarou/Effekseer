from pathlib import Path

import pytest

from effekseer_mcp.config import load_config


def test_config_loads_without_effekseer_exe(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("EFFEKSEER_EXE", "")
    monkeypatch.setenv("EFFEKSEER_WORKSPACE", str(tmp_path / "workspace"))

    config = load_config()

    assert config.effekseer_exe == ""
    assert config.effekseer_exe_path is None
    assert config.effekseer_exe_exists is False
    assert config.workspace == (tmp_path / "workspace").resolve()

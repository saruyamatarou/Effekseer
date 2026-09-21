from effekseer_mcp import server
from effekseer_mcp.paths import resolve_workspace
import pytest


def test_workspace_environment_is_shared_by_sample_helpers(monkeypatch, tmp_path):
    monkeypatch.setenv("EFFEKSEER_WORKSPACE", str(tmp_path / "editor"))
    assert resolve_workspace() == tmp_path / "editor"
    assert resolve_workspace(tmp_path / "explicit") == tmp_path / "explicit"


def test_http_uses_loopback_and_configured_port(monkeypatch):
    monkeypatch.setenv("MCP_TRANSPORT", "http")
    monkeypatch.setenv("EFFEKSEER_MCP_PORT", "51234")
    monkeypatch.setattr(server.mcp.settings, "port", 8000)
    monkeypatch.setattr(server.mcp.settings, "host", "127.0.0.1")
    calls = []
    monkeypatch.setattr(server.mcp, "run", lambda **kw: calls.append(kw))
    server.main()
    assert server.mcp.settings.host == "127.0.0.1"
    assert server.mcp.settings.port == 51234
    assert calls == [{"transport": "streamable-http"}]


@pytest.mark.parametrize("port", ["0", "65536", "invalid"])
def test_invalid_http_port_is_rejected(monkeypatch, port):
    monkeypatch.setenv("MCP_TRANSPORT", "http")
    monkeypatch.setenv("EFFEKSEER_MCP_PORT", port)
    monkeypatch.setattr(server.mcp.settings, "port", 8000)
    with pytest.raises(ValueError):
        server.main()

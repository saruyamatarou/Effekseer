import inspect
import json
import math
import socket

import pytest

from effekseer_mcp.bridge_client import (
    BRIDGE_HOST,
    DEFAULT_BRIDGE_PORT,
    EffekseerBridgeClient,
    EffekseerBridgeCommandError,
    EffekseerBridgeConnectionError,
)


class FakeSocket:
    def __init__(self, response: bytes = b'{"ok":true}\n') -> None:
        self.response = response
        self.sent = b""
        self.timeout: float | None = None

    def __enter__(self) -> "FakeSocket":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def settimeout(self, timeout: float) -> None:
        self.timeout = timeout

    def sendall(self, data: bytes) -> None:
        self.sent += data

    def recv(self, size: int) -> bytes:
        del size
        if not self.response:
            return b""

        chunk = self.response[:1]
        self.response = self.response[1:]
        return chunk


@pytest.mark.parametrize(
    ("method_name", "expected_command"),
    [
        ("ping", "ping"),
        ("get_status", "get_status"),
        ("get_bridge_capabilities", "get_bridge_capabilities"),
        ("get_node_tree", "get_node_tree"),
        ("add_node_to_selected", "add_node_to_selected"),
    ],
)
def test_bridge_methods_send_allowed_json(
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    expected_command: str,
) -> None:
    fake_socket = FakeSocket(b'{"result":"ok"}\n')
    calls: list[tuple[tuple[str, int], float | None]] = []

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        calls.append((address, timeout))
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    client = EffekseerBridgeClient(timeout_seconds=1.5)
    response = getattr(client, method_name)()

    assert response == {"result": "ok"}
    assert calls == [((BRIDGE_HOST, DEFAULT_BRIDGE_PORT), 1.5)]
    assert fake_socket.timeout == 1.5
    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": expected_command,
    }
    assert fake_socket.sent.endswith(b"\n")


def test_bridge_port_comes_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_socket = FakeSocket()
    calls: list[tuple[str, int]] = []

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del timeout
        calls.append(address)
        return fake_socket

    monkeypatch.setenv("EFFEKSEER_BRIDGE_PORT", "50124")
    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    EffekseerBridgeClient().ping()

    assert calls == [(BRIDGE_HOST, 50124)]


def test_bridge_rejects_disallowed_command() -> None:
    client = EffekseerBridgeClient()

    with pytest.raises(EffekseerBridgeCommandError):
        client.request("run_shell", {"command": "ping"})


def test_bridge_request_sends_params(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    EffekseerBridgeClient().request(
        "select_node_by_id",
        {"editorNodeId": 10},
    )

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": "select_node_by_id",
        "params": {"editorNodeId": 10},
    }


def test_bridge_request_omits_params_when_none(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    EffekseerBridgeClient().request("ping")

    assert json.loads(fake_socket.sent.decode("utf-8")) == {"command": "ping"}


def test_bridge_select_node_by_automation_id_sends_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    EffekseerBridgeClient().select_node_by_automation_id("auto-root")

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": "select_node_by_automation_id",
        "params": {"automationNodeId": "auto-root"},
    }


def test_bridge_add_node_to_parent_by_automation_id_sends_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    EffekseerBridgeClient().add_node_to_parent_by_automation_id(
        "auto-root",
        "Child",
    )

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": "add_node_to_parent_by_automation_id",
        "params": {
            "parentAutomationNodeId": "auto-root",
            "name": "Child",
        },
    }


def test_bridge_rename_node_by_automation_id_sends_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    EffekseerBridgeClient().rename_node_by_automation_id("auto-child", "Renamed")

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": "rename_node_by_automation_id",
        "params": {
            "automationNodeId": "auto-child",
            "name": "Renamed",
        },
    }


@pytest.mark.parametrize(
    ("method_name", "expected_command"),
    [
        (
            "get_node_basic_info_by_automation_id",
            "get_node_basic_info_by_automation_id",
        ),
        (
            "get_node_parameter_groups_by_automation_id",
            "get_node_parameter_groups_by_automation_id",
        ),
        (
            "get_node_base_parameters_by_automation_id",
            "get_node_base_parameters_by_automation_id",
        ),
        (
            "get_node_generation_parameters_by_automation_id",
            "get_node_generation_parameters_by_automation_id",
        ),
        (
            "get_node_transform_parameters_by_automation_id",
            "get_node_transform_parameters_by_automation_id",
        ),
        (
            "get_node_drawing_parameters_by_automation_id",
            "get_node_drawing_parameters_by_automation_id",
        ),
        (
            "get_node_renderer_parameters_by_automation_id",
            "get_node_renderer_parameters_by_automation_id",
        ),
    ],
)
def test_bridge_parameter_read_commands_send_automation_id_params(
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    expected_command: str,
) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    getattr(EffekseerBridgeClient(), method_name)("auto-child")

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": expected_command,
        "params": {"automationNodeId": "auto-child"},
    }


def test_bridge_remove_node_by_automation_id_sends_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    EffekseerBridgeClient().remove_node_by_automation_id("auto-child")

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": "remove_node_by_automation_id",
        "params": {"automationNodeId": "auto-child"},
    }


def test_bridge_duplicate_node_by_automation_id_sends_name_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    EffekseerBridgeClient().duplicate_node_by_automation_id("auto-child", "Copy")

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": "duplicate_node_by_automation_id",
        "params": {
            "automationNodeId": "auto-child",
            "name": "Copy",
        },
    }


def test_bridge_insert_parent_node_by_automation_id_sends_name_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    EffekseerBridgeClient().insert_parent_node_by_automation_id(
        "auto-child",
        "Wrapper",
    )

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": "insert_parent_node_by_automation_id",
        "params": {
            "automationNodeId": "auto-child",
            "name": "Wrapper",
        },
    }


def test_bridge_set_node_is_rendered_sends_bool_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    EffekseerBridgeClient().set_node_is_rendered_by_automation_id(
        "auto-child",
        False,
    )

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": "set_node_is_rendered_by_automation_id",
        "params": {
            "automationNodeId": "auto-child",
            "isRendered": False,
        },
    }


def test_bridge_set_node_is_rendered_rejects_non_bool() -> None:
    with pytest.raises(EffekseerBridgeCommandError, match="is_rendered must be a bool"):
        EffekseerBridgeClient().set_node_is_rendered_by_automation_id(
            "auto-child",
            "false",  # type: ignore[arg-type]
        )


def test_bridge_set_node_max_generation_sends_int_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    EffekseerBridgeClient().set_node_max_generation_by_automation_id(
        "auto-child",
        4,
    )

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": "set_node_max_generation_by_automation_id",
        "params": {
            "automationNodeId": "auto-child",
            "maxGeneration": 4,
        },
    }


def test_bridge_set_node_life_sends_int_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    EffekseerBridgeClient().set_node_life_by_automation_id(
        "auto-child",
        10,
        2,
        20,
    )

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": "set_node_life_by_automation_id",
        "params": {
            "automationNodeId": "auto-child",
            "center": 10,
            "min": 2,
            "max": 20,
        },
    }


def random_vector_payload(
    center: float,
    min: float,
    max: float,
) -> dict[str, dict[str, float]]:
    return {
        "x": {"center": center, "min": min, "max": max},
        "y": {"center": center, "min": min, "max": max},
        "z": {"center": center, "min": min, "max": max},
    }


def test_bridge_set_node_generation_time_sends_random_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    EffekseerBridgeClient().set_node_generation_time_by_automation_id(
        "auto-child",
        1.5,
        0.5,
        2.5,
    )

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": "set_node_generation_time_by_automation_id",
        "params": {
            "automationNodeId": "auto-child",
            "center": 1.5,
            "min": 0.5,
            "max": 2.5,
        },
    }


@pytest.mark.parametrize(
    ("method_name", "value", "expected_command", "expected_key"),
    [
        (
            "set_node_location_type_by_automation_id",
            "PVA",
            "set_node_location_type_by_automation_id",
            "locationType",
        ),
        (
            "set_node_scale_type_by_automation_id",
            "PVA",
            "set_node_scale_type_by_automation_id",
            "scaleType",
        ),
    ],
)
def test_bridge_set_node_motion_type_commands_send_params(
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    value: str,
    expected_command: str,
    expected_key: str,
) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    getattr(EffekseerBridgeClient(), method_name)("auto-child", value)

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": expected_command,
        "params": {
            "automationNodeId": "auto-child",
            expected_key: value,
        },
    }


@pytest.mark.parametrize(
    ("method_name", "expected_command", "primary_key"),
    [
        (
            "set_node_location_pva_by_automation_id",
            "set_node_location_pva_by_automation_id",
            "location",
        ),
        (
            "set_node_scale_pva_by_automation_id",
            "set_node_scale_pva_by_automation_id",
            "scale",
        ),
    ],
)
def test_bridge_set_node_pva_commands_send_random_vector_params(
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    expected_command: str,
    primary_key: str,
) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    first = random_vector_payload(1.0, 0.5, 1.5)
    velocity = random_vector_payload(2.0, 1.0, 3.0)
    acceleration = random_vector_payload(4.0, 3.0, 5.0)
    getattr(EffekseerBridgeClient(), method_name)(
        "auto-child",
        first,
        velocity,
        acceleration,
    )

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": expected_command,
        "params": {
            "automationNodeId": "auto-child",
            primary_key: first,
            "velocity": velocity,
            "acceleration": acceleration,
        },
    }


def test_bridge_set_node_fade_in_out_sends_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    EffekseerBridgeClient().set_node_fade_in_out_by_automation_id(
        "auto-child",
        "Use",
        3.0,
        "WithinLifetime",
        7.0,
    )

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": "set_node_fade_in_out_by_automation_id",
        "params": {
            "automationNodeId": "auto-child",
            "fadeInType": "Use",
            "fadeInFrame": 3.0,
            "fadeOutType": "WithinLifetime",
            "fadeOutFrame": 7.0,
        },
    }


def test_bridge_set_node_color_all_fixed_rgba_sends_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    EffekseerBridgeClient().set_node_color_all_fixed_rgba_by_automation_id(
        "auto-child",
        1,
        2,
        3,
        4,
    )

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": "set_node_color_all_fixed_rgba_by_automation_id",
        "params": {
            "automationNodeId": "auto-child",
            "r": 1,
            "g": 2,
            "b": 3,
            "a": 4,
        },
    }


def test_bridge_set_node_sprite_corner_colors_fixed_rgba_sends_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    EffekseerBridgeClient().set_node_sprite_corner_colors_fixed_rgba_by_automation_id(
        "auto-child",
        {"r": 1, "g": 2, "b": 3, "a": 4},
        {"r": 5, "g": 6, "b": 7, "a": 8},
        {"r": 9, "g": 10, "b": 11, "a": 12},
        {"r": 13, "g": 14, "b": 15, "a": 16},
    )

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": "set_node_sprite_corner_colors_fixed_rgba_by_automation_id",
        "params": {
            "automationNodeId": "auto-child",
            "lowerLeft": {"r": 1, "g": 2, "b": 3, "a": 4},
            "lowerRight": {"r": 5, "g": 6, "b": 7, "a": 8},
            "upperLeft": {"r": 9, "g": 10, "b": 11, "a": 12},
            "upperRight": {"r": 13, "g": 14, "b": 15, "a": 16},
        },
    }


@pytest.mark.parametrize(
    ("method_name", "value_name", "value", "expected_command", "expected_key"),
    [
        (
            "set_node_alpha_blend_by_automation_id",
            "alpha_blend",
            "Add",
            "set_node_alpha_blend_by_automation_id",
            "alphaBlend",
        ),
        (
            "set_node_z_write_by_automation_id",
            "z_write",
            False,
            "set_node_z_write_by_automation_id",
            "zWrite",
        ),
        (
            "set_node_z_test_by_automation_id",
            "z_test",
            False,
            "set_node_z_test_by_automation_id",
            "zTest",
        ),
        (
            "set_node_renderer_type_by_automation_id",
            "renderer_type",
            "Ribbon",
            "set_node_renderer_type_by_automation_id",
            "rendererType",
        ),
    ],
)
def test_bridge_set_node_drawing_renderer_scalar_commands_send_params(
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    value_name: str,
    value: object,
    expected_command: str,
    expected_key: str,
) -> None:
    del value_name
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    getattr(EffekseerBridgeClient(), method_name)("auto-child", value)

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": expected_command,
        "params": {
            "automationNodeId": "auto-child",
            expected_key: value,
        },
    }


@pytest.mark.parametrize("invalid_value", [True, -1, 256, "1"])
def test_bridge_set_node_color_all_fixed_rgba_rejects_invalid_channel(
    invalid_value: object,
) -> None:
    with pytest.raises(EffekseerBridgeCommandError):
        EffekseerBridgeClient().set_node_color_all_fixed_rgba_by_automation_id(
            "auto-child",
            invalid_value,  # type: ignore[arg-type]
            0,
            0,
            255,
        )


@pytest.mark.parametrize(
    "invalid_corner",
    [
        {"r": 1, "g": 2, "b": 3},
        {"r": True, "g": 2, "b": 3, "a": 4},
    ],
)
def test_bridge_set_node_sprite_corner_colors_fixed_rgba_rejects_invalid_corner(
    invalid_corner: dict[str, object],
) -> None:
    valid = {"r": 1, "g": 2, "b": 3, "a": 4}
    with pytest.raises(EffekseerBridgeCommandError):
        EffekseerBridgeClient().set_node_sprite_corner_colors_fixed_rgba_by_automation_id(
            "auto-child",
            invalid_corner,  # type: ignore[arg-type]
            valid,
            valid,
            valid,
        )


@pytest.mark.parametrize("invalid_value", [1, "Screen"])
def test_bridge_set_node_alpha_blend_rejects_invalid_value(
    invalid_value: object,
) -> None:
    with pytest.raises(EffekseerBridgeCommandError):
        EffekseerBridgeClient().set_node_alpha_blend_by_automation_id(
            "auto-child",
            invalid_value,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("invalid_value", [1, "Mesh"])
def test_bridge_set_node_renderer_type_rejects_invalid_value(
    invalid_value: object,
) -> None:
    with pytest.raises(EffekseerBridgeCommandError):
        EffekseerBridgeClient().set_node_renderer_type_by_automation_id(
            "auto-child",
            invalid_value,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("method_name", "invalid_value"),
    [
        ("set_node_z_write_by_automation_id", 1),
        ("set_node_z_test_by_automation_id", "false"),
    ],
)
def test_bridge_set_node_z_flags_reject_non_bool(
    method_name: str,
    invalid_value: object,
) -> None:
    with pytest.raises(EffekseerBridgeCommandError):
        getattr(EffekseerBridgeClient(), method_name)(
            "auto-child",
            invalid_value,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("method_name", "expected_command"),
    [
        ("get_workspace_status", "get_workspace_status"),
    ],
)
def test_bridge_workspace_no_param_commands_send_no_params(
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    expected_command: str,
) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    getattr(EffekseerBridgeClient(), method_name)()

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": expected_command,
    }


@pytest.mark.parametrize(
    ("method_name", "expected_command"),
    [
        ("save_project_to_workspace", "save_project_to_workspace"),
        ("open_project_from_workspace", "open_project_from_workspace"),
        ("export_runtime_effect_to_workspace", "export_runtime_effect_to_workspace"),
    ],
)
def test_bridge_workspace_file_commands_send_relative_paths(
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    expected_command: str,
) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    path = (
        "outputs/smoke.efk"
        if method_name == "export_runtime_effect_to_workspace"
        else "outputs/smoke.efkefc"
    )
    getattr(EffekseerBridgeClient(), method_name)(path)

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": expected_command,
        "params": {"path": path},
    }


def test_bridge_open_project_allows_legacy_efkproj(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    EffekseerBridgeClient().open_project_from_workspace("samples/sample_effects/FireBall.efkproj")

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": "open_project_from_workspace",
        "params": {"path": "samples/sample_effects/FireBall.efkproj"},
    }


@pytest.mark.parametrize(
    "invalid_path",
    [
        "outputs/smoke.efk",
        "outputs/smoke.efkproj",
        "../smoke.efkefc",
        "outputs/../smoke.efkefc",
        "C:/outside/smoke.efkefc",
    ],
)
def test_bridge_workspace_project_commands_reject_unsafe_paths(
    invalid_path: str,
) -> None:
    with pytest.raises(EffekseerBridgeCommandError):
        EffekseerBridgeClient().save_project_to_workspace(invalid_path)


@pytest.mark.parametrize(
    "invalid_path",
    [
        "outputs/smoke.efk",
        "outputs/smoke.txt",
        "../smoke.efkproj",
        "outputs/../smoke.efkproj",
        "C:/outside/smoke.efkproj",
    ],
)
def test_bridge_workspace_open_project_command_rejects_unsafe_paths(
    invalid_path: str,
) -> None:
    with pytest.raises(EffekseerBridgeCommandError):
        EffekseerBridgeClient().open_project_from_workspace(invalid_path)


@pytest.mark.parametrize(
    "invalid_path",
    [
        "outputs/smoke.efkefc",
        "outputs/smoke.txt",
        "../smoke.efk",
        "outputs/../smoke.efk",
        "C:/outside/smoke.efk",
    ],
)
def test_bridge_workspace_export_command_rejects_unsafe_paths(
    invalid_path: str,
) -> None:
    with pytest.raises(EffekseerBridgeCommandError):
        EffekseerBridgeClient().export_runtime_effect_to_workspace(invalid_path)


@pytest.mark.parametrize(
    ("method_name", "expected_command"),
    [
        (
            "set_node_color_texture_from_workspace_by_automation_id",
            "set_node_color_texture_from_workspace_by_automation_id",
        ),
        (
            "set_node_normal_texture_from_workspace_by_automation_id",
            "set_node_normal_texture_from_workspace_by_automation_id",
        ),
    ],
)
def test_bridge_texture_workspace_commands_send_relative_paths(
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    expected_command: str,
) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    getattr(EffekseerBridgeClient(), method_name)(
        "auto-child",
        "inputs/textures/smoke.png",
    )

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": expected_command,
        "params": {
            "automationNodeId": "auto-child",
            "path": "inputs/textures/smoke.png",
        },
    }


@pytest.mark.parametrize(
    "valid_path",
    [
        "inputs/a.png",
        "inputs/a.jpg",
        "inputs/a.jpeg",
        "inputs/a.tga",
        "inputs/a.dds",
        "inputs/a.bmp",
        "inputs/a.gif",
    ],
)
def test_bridge_texture_workspace_commands_accept_allowlisted_extensions(
    monkeypatch: pytest.MonkeyPatch,
    valid_path: str,
) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    EffekseerBridgeClient().set_node_color_texture_from_workspace_by_automation_id(
        "auto-child",
        valid_path,
    )

    assert json.loads(fake_socket.sent.decode("utf-8"))["params"]["path"] == valid_path


@pytest.mark.parametrize(
    "invalid_path",
    [
        "inputs/smoke.exe",
        "inputs/smoke.txt",
        "../smoke.png",
        "inputs/../smoke.png",
        "C:/outside/smoke.png",
    ],
)
def test_bridge_texture_workspace_commands_reject_unsafe_paths(
    invalid_path: str,
) -> None:
    with pytest.raises(EffekseerBridgeCommandError):
        EffekseerBridgeClient().set_node_color_texture_from_workspace_by_automation_id(
            "auto-child",
            invalid_path,
        )


@pytest.mark.parametrize(
    ("method_name", "expected_command"),
    [
        (
            "clear_node_color_texture_by_automation_id",
            "clear_node_color_texture_by_automation_id",
        ),
        (
            "clear_node_normal_texture_by_automation_id",
            "clear_node_normal_texture_by_automation_id",
        ),
    ],
)
def test_bridge_clear_texture_commands_send_automation_id(
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    expected_command: str,
) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    getattr(EffekseerBridgeClient(), method_name)("auto-child")

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": expected_command,
        "params": {"automationNodeId": "auto-child"},
    }


def test_bridge_material_workspace_command_sends_relative_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    EffekseerBridgeClient().set_node_material_from_workspace_by_automation_id(
        "auto-child",
        "inputs/materials/smoke.efkmat",
    )

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": "set_node_material_from_workspace_by_automation_id",
        "params": {
            "automationNodeId": "auto-child",
            "path": "inputs/materials/smoke.efkmat",
        },
    }


@pytest.mark.parametrize(
    "invalid_path",
    [
        "inputs/materials/smoke.png",
        "inputs/materials/smoke.txt",
        "inputs/materials/smoke.exe",
        "../smoke.efkmat",
        "inputs/../smoke.efkmat",
        "C:/outside/smoke.efkmat",
    ],
)
def test_bridge_material_workspace_command_rejects_unsafe_paths(
    invalid_path: str,
) -> None:
    with pytest.raises(EffekseerBridgeCommandError):
        EffekseerBridgeClient().set_node_material_from_workspace_by_automation_id(
            "auto-child",
            invalid_path,
        )


def test_bridge_clear_material_command_sends_automation_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    EffekseerBridgeClient().clear_node_material_by_automation_id("auto-child")

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": "clear_node_material_by_automation_id",
        "params": {"automationNodeId": "auto-child"},
    }


def test_bridge_model_workspace_command_sends_relative_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    EffekseerBridgeClient().set_node_model_from_workspace_by_automation_id(
        "auto-child",
        "inputs/models/smoke.efkmodel",
    )

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": "set_node_model_from_workspace_by_automation_id",
        "params": {
            "automationNodeId": "auto-child",
            "path": "inputs/models/smoke.efkmodel",
        },
    }


@pytest.mark.parametrize(
    "invalid_path",
    [
        "inputs/models/smoke.efkmat",
        "inputs/models/smoke.txt",
        "inputs/models/smoke.exe",
        "../smoke.efkmodel",
        "inputs/../smoke.efkmodel",
        "C:/outside/smoke.efkmodel",
    ],
)
def test_bridge_model_workspace_command_rejects_unsafe_paths(
    invalid_path: str,
) -> None:
    with pytest.raises(EffekseerBridgeCommandError):
        EffekseerBridgeClient().set_node_model_from_workspace_by_automation_id(
            "auto-child",
            invalid_path,
        )


@pytest.mark.parametrize(
    ("method_name", "expected_command"),
    [
        (
            "set_node_fixed_location_by_automation_id",
            "set_node_fixed_location_by_automation_id",
        ),
        (
            "set_node_fixed_rotation_by_automation_id",
            "set_node_fixed_rotation_by_automation_id",
        ),
        (
            "set_node_fixed_scale_by_automation_id",
            "set_node_fixed_scale_by_automation_id",
        ),
    ],
)
def test_bridge_set_node_fixed_vector_sends_number_params(
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    expected_command: str,
) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    getattr(EffekseerBridgeClient(), method_name)("auto-child", 1, 2.5, -3.0)

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": expected_command,
        "params": {
            "automationNodeId": "auto-child",
            "x": 1,
            "y": 2.5,
            "z": -3.0,
        },
    }


@pytest.mark.parametrize("invalid_value", [True, "4"])
def test_bridge_set_node_max_generation_rejects_non_int(
    invalid_value: object,
) -> None:
    with pytest.raises(EffekseerBridgeCommandError, match="max_generation must be"):
        EffekseerBridgeClient().set_node_max_generation_by_automation_id(
            "auto-child",
            invalid_value,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("invalid_value", [False, "10"])
def test_bridge_set_node_life_rejects_non_int(invalid_value: object) -> None:
    with pytest.raises(EffekseerBridgeCommandError, match="center must be"):
        EffekseerBridgeClient().set_node_life_by_automation_id(
            "auto-child",
            invalid_value,  # type: ignore[arg-type]
            1,
            2,
        )


@pytest.mark.parametrize("invalid_value", [True, "1.0", math.nan, math.inf, -math.inf])
def test_bridge_set_node_generation_time_rejects_invalid_number(
    invalid_value: object,
) -> None:
    with pytest.raises(EffekseerBridgeCommandError, match="center must be"):
        EffekseerBridgeClient().set_node_generation_time_by_automation_id(
            "auto-child",
            invalid_value,  # type: ignore[arg-type]
            0.0,
            1.0,
        )


@pytest.mark.parametrize(
    ("method_name", "invalid_value"),
    [
        ("set_node_location_type_by_automation_id", "Easing"),
        ("set_node_location_type_by_automation_id", 1),
        ("set_node_scale_type_by_automation_id", "SinglePVA"),
        ("set_node_scale_type_by_automation_id", True),
    ],
)
def test_bridge_set_node_motion_type_rejects_invalid_value(
    method_name: str,
    invalid_value: object,
) -> None:
    with pytest.raises(EffekseerBridgeCommandError):
        getattr(EffekseerBridgeClient(), method_name)(
            "auto-child",
            invalid_value,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("invalid_value", [True, "1.0", math.nan, math.inf, -math.inf])
def test_bridge_set_node_pva_rejects_invalid_random_number(
    invalid_value: object,
) -> None:
    invalid = {
        "x": {"center": invalid_value, "min": 0.0, "max": 1.0},
        "y": {"center": 0.0, "min": 0.0, "max": 1.0},
        "z": {"center": 0.0, "min": 0.0, "max": 1.0},
    }
    valid = random_vector_payload(0.0, 0.0, 1.0)

    with pytest.raises(EffekseerBridgeCommandError, match="location.x.center"):
        EffekseerBridgeClient().set_node_location_pva_by_automation_id(
            "auto-child",
            invalid,  # type: ignore[arg-type]
            valid,
            valid,
        )


@pytest.mark.parametrize(
    ("fade_in_type", "fade_in_frame", "fade_out_type", "fade_out_frame"),
    [
        ("Use", True, "WithinLifetime", 1.0),
        ("Enabled", 1.0, "WithinLifetime", 1.0),
        ("Use", 1.0, "Lifetime", 1.0),
        ("Use", 1.0, "WithinLifetime", math.nan),
    ],
)
def test_bridge_set_node_fade_in_out_rejects_invalid_values(
    fade_in_type: object,
    fade_in_frame: object,
    fade_out_type: object,
    fade_out_frame: object,
) -> None:
    with pytest.raises(EffekseerBridgeCommandError):
        EffekseerBridgeClient().set_node_fade_in_out_by_automation_id(
            "auto-child",
            fade_in_type,  # type: ignore[arg-type]
            fade_in_frame,  # type: ignore[arg-type]
            fade_out_type,  # type: ignore[arg-type]
            fade_out_frame,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("invalid_value", [True, "1.0", math.nan, math.inf, -math.inf])
def test_bridge_set_node_fixed_vector_rejects_invalid_number(
    invalid_value: object,
) -> None:
    with pytest.raises(EffekseerBridgeCommandError, match="x must be a finite number"):
        EffekseerBridgeClient().set_node_fixed_location_by_automation_id(
            "auto-child",
            invalid_value,  # type: ignore[arg-type]
            0.0,
            0.0,
        )


@pytest.mark.parametrize(
    ("method_name", "expected_command"),
    [
        ("undo", "undo"),
        ("redo", "redo"),
        ("play_viewer", "play_viewer"),
        ("stop_viewer", "stop_viewer"),
        ("step_viewer", "step_viewer"),
        ("back_step_viewer", "back_step_viewer"),
    ],
)
def test_bridge_no_param_commands_send_no_params(
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    expected_command: str,
) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    getattr(EffekseerBridgeClient(), method_name)()

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": expected_command,
    }


def test_bridge_add_node_to_parent_sends_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    EffekseerBridgeClient().add_node_to_parent(1, "Child")

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": "add_node_to_parent",
        "params": {
            "parentEditorNodeId": 1,
            "name": "Child",
        },
    }


def test_bridge_rename_node_sends_params(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_socket = FakeSocket()

    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        return fake_socket

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    EffekseerBridgeClient().rename_node(2, "Renamed")

    assert json.loads(fake_socket.sent.decode("utf-8")) == {
        "command": "rename_node",
        "params": {
            "editorNodeId": 2,
            "name": "Renamed",
        },
    }


def test_bridge_timeout_becomes_clear_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        raise TimeoutError("timed out")

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    with pytest.raises(EffekseerBridgeConnectionError, match="timed out"):
        EffekseerBridgeClient().ping()


def test_bridge_connection_refused_becomes_clear_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_create_connection(
        address: tuple[str, int],
        timeout: float | None = None,
    ) -> FakeSocket:
        del address, timeout
        raise ConnectionRefusedError("refused")

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    with pytest.raises(EffekseerBridgeConnectionError, match="not reachable"):
        EffekseerBridgeClient().ping()


def test_bridge_does_not_expose_host_configuration() -> None:
    parameters = inspect.signature(EffekseerBridgeClient).parameters

    assert "host" not in parameters

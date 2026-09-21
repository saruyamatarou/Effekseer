import json
import math
import os
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from effekseer_mcp.paths import ensure_workspace_path, resolve_workspace

BRIDGE_HOST = "127.0.0.1"
DEFAULT_BRIDGE_PORT = 50123
DEFAULT_TIMEOUT_SECONDS = 3.0
ALPHA_BLEND_VALUES = frozenset({"Opacity", "Blend", "Add", "Sub", "Mul"})
RENDERER_TYPE_VALUES = frozenset({"Sprite", "Ribbon", "Ring", "Model", "Track"})
LOCATION_TYPE_VALUES = frozenset({"Fixed", "PVA"})
SCALE_TYPE_VALUES = frozenset({"Fixed", "PVA"})
FADE_IN_TYPE_VALUES = frozenset({"None", "Use"})
FADE_OUT_TYPE_VALUES = frozenset({"None", "WithinLifetime", "AfterRemoved"})
RGBA_KEYS = ("r", "g", "b", "a")
VECTOR3_KEYS = ("x", "y", "z")
RANDOM_KEYS = ("center", "min", "max")
TEXTURE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".tga", ".dds", ".bmp", ".gif"})
ALLOWED_COMMANDS = frozenset(
    {
        "ping",
        "get_status",
        "get_bridge_capabilities",
        "get_workspace_status",
        "save_project_to_workspace",
        "open_project_from_workspace",
        "export_runtime_effect_to_workspace",
        "get_node_tree",
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
        "set_node_generation_time_by_automation_id",
        "set_node_location_type_by_automation_id",
        "set_node_location_pva_by_automation_id",
        "set_node_scale_type_by_automation_id",
        "set_node_scale_pva_by_automation_id",
        "set_node_fade_in_out_by_automation_id",
        "set_node_color_all_fixed_rgba_by_automation_id",
        "set_node_sprite_corner_colors_fixed_rgba_by_automation_id",
        "set_node_alpha_blend_by_automation_id",
        "set_node_z_write_by_automation_id",
        "set_node_z_test_by_automation_id",
        "set_node_renderer_type_by_automation_id",
        "set_node_color_texture_from_workspace_by_automation_id",
        "set_node_normal_texture_from_workspace_by_automation_id",
        "clear_node_color_texture_by_automation_id",
        "clear_node_normal_texture_by_automation_id",
        "set_node_material_from_workspace_by_automation_id",
        "clear_node_material_by_automation_id",
        "set_node_model_from_workspace_by_automation_id",
    }
)


class EffekseerBridgeError(RuntimeError):
    """Base error for Effekseer Automation Bridge failures."""


class EffekseerBridgeCommandError(EffekseerBridgeError):
    """Raised when a command is not allowed."""


class EffekseerBridgeConnectionError(EffekseerBridgeError):
    """Raised when the bridge cannot be reached."""


class EffekseerBridgeProtocolError(EffekseerBridgeError):
    """Raised when the bridge response is not valid JSON object data."""


@dataclass(frozen=True)
class EffekseerBridgeClient:
    port: int | None = None
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    def request(self, command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send an allowlisted JSON-line command to the local bridge."""
        if command not in ALLOWED_COMMANDS:
            raise EffekseerBridgeCommandError(f"command is not allowed: {command}")

        payload: dict[str, Any] = {"command": command}
        if params is not None:
            payload["params"] = params

        return self._send_json_line(payload)

    def ping(self) -> dict[str, Any]:
        return self.request("ping")

    def get_status(self) -> dict[str, Any]:
        return self.request("get_status")

    def get_bridge_capabilities(self) -> dict[str, Any]:
        return self.request("get_bridge_capabilities")

    def get_workspace_status(self) -> dict[str, Any]:
        return self.request("get_workspace_status")

    def save_project_to_workspace(self, path: str) -> dict[str, Any]:
        return self.request(
            "save_project_to_workspace",
            {"path": normalize_workspace_save_project_path(path)},
        )

    def open_project_from_workspace(self, path: str) -> dict[str, Any]:
        return self.request(
            "open_project_from_workspace",
            {"path": normalize_workspace_open_project_path(path)},
        )

    def export_runtime_effect_to_workspace(self, path: str) -> dict[str, Any]:
        return self.request(
            "export_runtime_effect_to_workspace",
            {"path": normalize_workspace_runtime_effect_path(path)},
        )

    def get_node_tree(self) -> dict[str, Any]:
        return self.request("get_node_tree")

    def add_node_to_selected(self) -> dict[str, Any]:
        return self.request("add_node_to_selected")

    def select_node_by_automation_id(
        self,
        automation_node_id: str,
    ) -> dict[str, Any]:
        return self.request(
            "select_node_by_automation_id",
            {"automationNodeId": automation_node_id},
        )

    def add_node_to_parent_by_automation_id(
        self,
        parent_automation_node_id: str,
        name: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "parentAutomationNodeId": parent_automation_node_id,
        }
        if name is not None:
            params["name"] = name

        return self.request("add_node_to_parent_by_automation_id", params)

    def rename_node_by_automation_id(
        self,
        automation_node_id: str,
        name: str,
    ) -> dict[str, Any]:
        return self.request(
            "rename_node_by_automation_id",
            {
                "automationNodeId": automation_node_id,
                "name": name,
            },
        )

    def remove_node_by_automation_id(
        self,
        automation_node_id: str,
    ) -> dict[str, Any]:
        return self.request(
            "remove_node_by_automation_id",
            {"automationNodeId": automation_node_id},
        )

    def duplicate_node_by_automation_id(
        self,
        automation_node_id: str,
        name: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"automationNodeId": automation_node_id}
        if name is not None:
            params["name"] = name

        return self.request("duplicate_node_by_automation_id", params)

    def insert_parent_node_by_automation_id(
        self,
        automation_node_id: str,
        name: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"automationNodeId": automation_node_id}
        if name is not None:
            params["name"] = name

        return self.request("insert_parent_node_by_automation_id", params)

    def undo(self) -> dict[str, Any]:
        return self.request("undo")

    def redo(self) -> dict[str, Any]:
        return self.request("redo")

    def play_viewer(self) -> dict[str, Any]:
        return self.request("play_viewer")

    def stop_viewer(self) -> dict[str, Any]:
        return self.request("stop_viewer")

    def step_viewer(self) -> dict[str, Any]:
        return self.request("step_viewer")

    def back_step_viewer(self) -> dict[str, Any]:
        return self.request("back_step_viewer")

    def get_node_basic_info_by_automation_id(
        self,
        automation_node_id: str,
    ) -> dict[str, Any]:
        return self.request(
            "get_node_basic_info_by_automation_id",
            {"automationNodeId": automation_node_id},
        )

    def get_node_parameter_groups_by_automation_id(
        self,
        automation_node_id: str,
    ) -> dict[str, Any]:
        return self.request(
            "get_node_parameter_groups_by_automation_id",
            {"automationNodeId": automation_node_id},
        )

    def get_node_base_parameters_by_automation_id(
        self,
        automation_node_id: str,
    ) -> dict[str, Any]:
        return self.request(
            "get_node_base_parameters_by_automation_id",
            {"automationNodeId": automation_node_id},
        )

    def get_node_generation_parameters_by_automation_id(
        self,
        automation_node_id: str,
    ) -> dict[str, Any]:
        return self.request(
            "get_node_generation_parameters_by_automation_id",
            {"automationNodeId": automation_node_id},
        )

    def get_node_transform_parameters_by_automation_id(
        self,
        automation_node_id: str,
    ) -> dict[str, Any]:
        return self.request(
            "get_node_transform_parameters_by_automation_id",
            {"automationNodeId": automation_node_id},
        )

    def get_node_drawing_parameters_by_automation_id(
        self,
        automation_node_id: str,
    ) -> dict[str, Any]:
        return self.request(
            "get_node_drawing_parameters_by_automation_id",
            {"automationNodeId": automation_node_id},
        )

    def get_node_renderer_parameters_by_automation_id(
        self,
        automation_node_id: str,
    ) -> dict[str, Any]:
        return self.request(
            "get_node_renderer_parameters_by_automation_id",
            {"automationNodeId": automation_node_id},
        )

    def set_node_is_rendered_by_automation_id(
        self,
        automation_node_id: str,
        is_rendered: bool,
    ) -> dict[str, Any]:
        if not isinstance(is_rendered, bool):
            raise EffekseerBridgeCommandError("is_rendered must be a bool")

        return self.request(
            "set_node_is_rendered_by_automation_id",
            {
                "automationNodeId": automation_node_id,
                "isRendered": is_rendered,
            },
        )

    def set_node_max_generation_by_automation_id(
        self,
        automation_node_id: str,
        max_generation: int,
    ) -> dict[str, Any]:
        return self.request(
            "set_node_max_generation_by_automation_id",
            {
                "automationNodeId": automation_node_id,
                "maxGeneration": _require_int("max_generation", max_generation),
            },
        )

    def set_node_life_by_automation_id(
        self,
        automation_node_id: str,
        center: int,
        min: int,
        max: int,
    ) -> dict[str, Any]:
        return self.request(
            "set_node_life_by_automation_id",
            {
                "automationNodeId": automation_node_id,
                "center": _require_int("center", center),
                "min": _require_int("min", min),
                "max": _require_int("max", max),
            },
        )

    def set_node_fixed_location_by_automation_id(
        self,
        automation_node_id: str,
        x: float,
        y: float,
        z: float,
    ) -> dict[str, Any]:
        return self._set_node_fixed_vector_by_automation_id(
            "set_node_fixed_location_by_automation_id",
            automation_node_id,
            x,
            y,
            z,
        )

    def set_node_fixed_rotation_by_automation_id(
        self,
        automation_node_id: str,
        x: float,
        y: float,
        z: float,
    ) -> dict[str, Any]:
        return self._set_node_fixed_vector_by_automation_id(
            "set_node_fixed_rotation_by_automation_id",
            automation_node_id,
            x,
            y,
            z,
        )

    def set_node_fixed_scale_by_automation_id(
        self,
        automation_node_id: str,
        x: float,
        y: float,
        z: float,
    ) -> dict[str, Any]:
        return self._set_node_fixed_vector_by_automation_id(
            "set_node_fixed_scale_by_automation_id",
            automation_node_id,
            x,
            y,
            z,
        )

    def _set_node_fixed_vector_by_automation_id(
        self,
        command: str,
        automation_node_id: str,
        x: float,
        y: float,
        z: float,
    ) -> dict[str, Any]:
        return self.request(
            command,
            {
                "automationNodeId": automation_node_id,
                "x": _require_finite_number("x", x),
                "y": _require_finite_number("y", y),
                "z": _require_finite_number("z", z),
            },
        )

    def set_node_generation_time_by_automation_id(
        self,
        automation_node_id: str,
        center: float,
        min: float,
        max: float,
    ) -> dict[str, Any]:
        return self.request(
            "set_node_generation_time_by_automation_id",
            {
                "automationNodeId": automation_node_id,
                "center": _require_finite_number("center", center),
                "min": _require_finite_number("min", min),
                "max": _require_finite_number("max", max),
            },
        )

    def set_node_location_type_by_automation_id(
        self,
        automation_node_id: str,
        location_type: str,
    ) -> dict[str, Any]:
        return self.request(
            "set_node_location_type_by_automation_id",
            {
                "automationNodeId": automation_node_id,
                "locationType": _require_allowed_string(
                    "location_type",
                    location_type,
                    LOCATION_TYPE_VALUES,
                ),
            },
        )

    def set_node_location_pva_by_automation_id(
        self,
        automation_node_id: str,
        location: dict[str, dict[str, float]],
        velocity: dict[str, dict[str, float]],
        acceleration: dict[str, dict[str, float]],
    ) -> dict[str, Any]:
        return self.request(
            "set_node_location_pva_by_automation_id",
            {
                "automationNodeId": automation_node_id,
                "location": _require_vector3_random("location", location),
                "velocity": _require_vector3_random("velocity", velocity),
                "acceleration": _require_vector3_random(
                    "acceleration",
                    acceleration,
                ),
            },
        )

    def set_node_scale_type_by_automation_id(
        self,
        automation_node_id: str,
        scale_type: str,
    ) -> dict[str, Any]:
        return self.request(
            "set_node_scale_type_by_automation_id",
            {
                "automationNodeId": automation_node_id,
                "scaleType": _require_allowed_string(
                    "scale_type",
                    scale_type,
                    SCALE_TYPE_VALUES,
                ),
            },
        )

    def set_node_scale_pva_by_automation_id(
        self,
        automation_node_id: str,
        scale: dict[str, dict[str, float]],
        velocity: dict[str, dict[str, float]],
        acceleration: dict[str, dict[str, float]],
    ) -> dict[str, Any]:
        return self.request(
            "set_node_scale_pva_by_automation_id",
            {
                "automationNodeId": automation_node_id,
                "scale": _require_vector3_random("scale", scale),
                "velocity": _require_vector3_random("velocity", velocity),
                "acceleration": _require_vector3_random(
                    "acceleration",
                    acceleration,
                ),
            },
        )

    def set_node_fade_in_out_by_automation_id(
        self,
        automation_node_id: str,
        fade_in_type: str,
        fade_in_frame: float,
        fade_out_type: str,
        fade_out_frame: float,
    ) -> dict[str, Any]:
        return self.request(
            "set_node_fade_in_out_by_automation_id",
            {
                "automationNodeId": automation_node_id,
                "fadeInType": _require_allowed_string(
                    "fade_in_type",
                    fade_in_type,
                    FADE_IN_TYPE_VALUES,
                ),
                "fadeInFrame": _require_finite_number(
                    "fade_in_frame",
                    fade_in_frame,
                ),
                "fadeOutType": _require_allowed_string(
                    "fade_out_type",
                    fade_out_type,
                    FADE_OUT_TYPE_VALUES,
                ),
                "fadeOutFrame": _require_finite_number(
                    "fade_out_frame",
                    fade_out_frame,
                ),
            },
        )

    def set_node_color_all_fixed_rgba_by_automation_id(
        self,
        automation_node_id: str,
        r: int,
        g: int,
        b: int,
        a: int,
    ) -> dict[str, Any]:
        return self.request(
            "set_node_color_all_fixed_rgba_by_automation_id",
            {
                "automationNodeId": automation_node_id,
                "r": _require_rgba_channel("r", r),
                "g": _require_rgba_channel("g", g),
                "b": _require_rgba_channel("b", b),
                "a": _require_rgba_channel("a", a),
            },
        )

    def set_node_sprite_corner_colors_fixed_rgba_by_automation_id(
        self,
        automation_node_id: str,
        lower_left: dict[str, int],
        lower_right: dict[str, int],
        upper_left: dict[str, int],
        upper_right: dict[str, int],
    ) -> dict[str, Any]:
        return self.request(
            "set_node_sprite_corner_colors_fixed_rgba_by_automation_id",
            {
                "automationNodeId": automation_node_id,
                "lowerLeft": _require_rgba("lower_left", lower_left),
                "lowerRight": _require_rgba("lower_right", lower_right),
                "upperLeft": _require_rgba("upper_left", upper_left),
                "upperRight": _require_rgba("upper_right", upper_right),
            },
        )

    def set_node_alpha_blend_by_automation_id(
        self,
        automation_node_id: str,
        alpha_blend: str,
    ) -> dict[str, Any]:
        return self.request(
            "set_node_alpha_blend_by_automation_id",
            {
                "automationNodeId": automation_node_id,
                "alphaBlend": _require_allowed_string(
                    "alpha_blend",
                    alpha_blend,
                    ALPHA_BLEND_VALUES,
                ),
            },
        )

    def set_node_z_write_by_automation_id(
        self,
        automation_node_id: str,
        z_write: bool,
    ) -> dict[str, Any]:
        return self.request(
            "set_node_z_write_by_automation_id",
            {
                "automationNodeId": automation_node_id,
                "zWrite": _require_bool("z_write", z_write),
            },
        )

    def set_node_z_test_by_automation_id(
        self,
        automation_node_id: str,
        z_test: bool,
    ) -> dict[str, Any]:
        return self.request(
            "set_node_z_test_by_automation_id",
            {
                "automationNodeId": automation_node_id,
                "zTest": _require_bool("z_test", z_test),
            },
        )

    def set_node_renderer_type_by_automation_id(
        self,
        automation_node_id: str,
        renderer_type: str,
    ) -> dict[str, Any]:
        return self.request(
            "set_node_renderer_type_by_automation_id",
            {
                "automationNodeId": automation_node_id,
                "rendererType": _require_allowed_string(
                    "renderer_type",
                    renderer_type,
                    RENDERER_TYPE_VALUES,
                ),
            },
        )

    def set_node_color_texture_from_workspace_by_automation_id(
        self,
        automation_node_id: str,
        path: str,
    ) -> dict[str, Any]:
        return self.request(
            "set_node_color_texture_from_workspace_by_automation_id",
            {
                "automationNodeId": automation_node_id,
                "path": normalize_workspace_texture_path(path),
            },
        )

    def set_node_normal_texture_from_workspace_by_automation_id(
        self,
        automation_node_id: str,
        path: str,
    ) -> dict[str, Any]:
        return self.request(
            "set_node_normal_texture_from_workspace_by_automation_id",
            {
                "automationNodeId": automation_node_id,
                "path": normalize_workspace_texture_path(path),
            },
        )

    def clear_node_color_texture_by_automation_id(
        self,
        automation_node_id: str,
    ) -> dict[str, Any]:
        return self.request(
            "clear_node_color_texture_by_automation_id",
            {"automationNodeId": automation_node_id},
        )

    def clear_node_normal_texture_by_automation_id(
        self,
        automation_node_id: str,
    ) -> dict[str, Any]:
        return self.request(
            "clear_node_normal_texture_by_automation_id",
            {"automationNodeId": automation_node_id},
        )

    def set_node_material_from_workspace_by_automation_id(
        self,
        automation_node_id: str,
        path: str,
    ) -> dict[str, Any]:
        return self.request(
            "set_node_material_from_workspace_by_automation_id",
            {
                "automationNodeId": automation_node_id,
                "path": normalize_workspace_material_path(path),
            },
        )

    def clear_node_material_by_automation_id(
        self,
        automation_node_id: str,
    ) -> dict[str, Any]:
        return self.request(
            "clear_node_material_by_automation_id",
            {"automationNodeId": automation_node_id},
        )

    def set_node_model_from_workspace_by_automation_id(
        self,
        automation_node_id: str,
        path: str,
    ) -> dict[str, Any]:
        return self.request(
            "set_node_model_from_workspace_by_automation_id",
            {
                "automationNodeId": automation_node_id,
                "path": normalize_workspace_model_path(path),
            },
        )

    def select_node_by_id(self, editor_node_id: int) -> dict[str, Any]:
        return self.request(
            "select_node_by_id",
            {"editorNodeId": editor_node_id},
        )

    def add_node_to_parent(
        self,
        parent_editor_node_id: int,
        name: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"parentEditorNodeId": parent_editor_node_id}
        if name is not None:
            params["name"] = name

        return self.request("add_node_to_parent", params)

    def rename_node(self, editor_node_id: int, name: str) -> dict[str, Any]:
        return self.request(
            "rename_node",
            {
                "editorNodeId": editor_node_id,
                "name": name,
            },
        )

    def _send_json_line(self, payload: dict[str, Any]) -> dict[str, Any]:
        port = self.port if self.port is not None else get_bridge_port()
        request_bytes = (json.dumps(payload, separators=(",", ":")) + "\n").encode(
            "utf-8"
        )

        try:
            with socket.create_connection(
                (BRIDGE_HOST, port),
                timeout=self.timeout_seconds,
            ) as sock:
                sock.settimeout(self.timeout_seconds)
                sock.sendall(request_bytes)
                response_line = _read_response_line(sock)
        except TimeoutError as exc:
            raise EffekseerBridgeConnectionError(
                f"Effekseer Automation Bridge timed out on {BRIDGE_HOST}:{port}"
            ) from exc
        except OSError as exc:
            raise EffekseerBridgeConnectionError(
                f"Effekseer Automation Bridge is not reachable on {BRIDGE_HOST}:{port}"
            ) from exc

        return _decode_response(response_line)


def get_bridge_port() -> int:
    raw_port = os.getenv("EFFEKSEER_BRIDGE_PORT", str(DEFAULT_BRIDGE_PORT))
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise EffekseerBridgeConnectionError(
            "EFFEKSEER_BRIDGE_PORT must be an integer"
        ) from exc

    if not 1 <= port <= 65535:
        raise EffekseerBridgeConnectionError(
            "EFFEKSEER_BRIDGE_PORT must be between 1 and 65535"
        )

    return port


def _read_response_line(sock: socket.socket) -> bytes:
    chunks: list[bytes] = []

    while True:
        chunk = sock.recv(1)
        if chunk == b"":
            break
        chunks.append(chunk)
        if chunk == b"\n":
            break

    if not chunks:
        raise EffekseerBridgeProtocolError("bridge returned an empty response")

    return b"".join(chunks)


def _decode_response(response_line: bytes) -> dict[str, Any]:
    try:
        response = json.loads(response_line.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EffekseerBridgeProtocolError("bridge returned invalid JSON") from exc

    if not isinstance(response, dict):
        raise EffekseerBridgeProtocolError("bridge response must be a JSON object")

    return response


def _require_int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise EffekseerBridgeCommandError(f"{name} must be an int")

    return value


def _require_finite_number(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise EffekseerBridgeCommandError(f"{name} must be a finite number")
    if not math.isfinite(value):
        raise EffekseerBridgeCommandError(f"{name} must be a finite number")

    return value


def _require_bool(name: str, value: bool) -> bool:
    if not isinstance(value, bool):
        raise EffekseerBridgeCommandError(f"{name} must be a bool")

    return value


def _require_rgba_channel(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise EffekseerBridgeCommandError(f"{name} must be an int")
    if not 0 <= value <= 255:
        raise EffekseerBridgeCommandError(f"{name} must be between 0 and 255")

    return value


def _require_rgba(name: str, value: dict[str, int]) -> dict[str, int]:
    if not isinstance(value, dict):
        raise EffekseerBridgeCommandError(f"{name} must be an rgba object")

    missing_keys = set(RGBA_KEYS) - value.keys()
    if missing_keys:
        raise EffekseerBridgeCommandError(
            f"{name} missing rgba keys: " + ", ".join(sorted(missing_keys))
        )

    return {
        key: _require_rgba_channel(f"{name}.{key}", value[key])
        for key in RGBA_KEYS
    }


def _require_random_number(
    name: str,
    value: dict[str, float],
) -> dict[str, float]:
    if not isinstance(value, dict):
        raise EffekseerBridgeCommandError(f"{name} must be a random number object")

    missing_keys = set(RANDOM_KEYS) - value.keys()
    if missing_keys:
        raise EffekseerBridgeCommandError(
            f"{name} missing random keys: " + ", ".join(sorted(missing_keys))
        )

    return {
        key: _require_finite_number(f"{name}.{key}", value[key])
        for key in RANDOM_KEYS
    }


def _require_vector3_random(
    name: str,
    value: dict[str, dict[str, float]],
) -> dict[str, dict[str, float]]:
    if not isinstance(value, dict):
        raise EffekseerBridgeCommandError(f"{name} must be a vector3 random object")

    missing_keys = set(VECTOR3_KEYS) - value.keys()
    if missing_keys:
        raise EffekseerBridgeCommandError(
            f"{name} missing vector keys: " + ", ".join(sorted(missing_keys))
        )

    return {
        key: _require_random_number(f"{name}.{key}", value[key])
        for key in VECTOR3_KEYS
    }


def _require_allowed_string(
    name: str,
    value: str,
    allowed_values: frozenset[str],
) -> str:
    if not isinstance(value, str):
        raise EffekseerBridgeCommandError(f"{name} must be a string")
    if value not in allowed_values:
        raise EffekseerBridgeCommandError(
            f"{name} must be one of: " + ", ".join(sorted(allowed_values))
        )

    return value


def normalize_workspace_project_path(
    path: str,
    *,
    workspace: str | Path | None = None,
) -> str:
    return normalize_workspace_save_project_path(path, workspace=workspace)


def normalize_workspace_save_project_path(
    path: str,
    *,
    workspace: str | Path | None = None,
) -> str:
    return normalize_workspace_file_path(
        path,
        extension=".efkefc",
        label="project path",
        workspace=workspace,
    )


def normalize_workspace_open_project_path(
    path: str,
    *,
    workspace: str | Path | None = None,
) -> str:
    return normalize_workspace_file_path(
        path,
        extensions=frozenset({".efkefc", ".efkproj"}),
        label="project path",
        workspace=workspace,
    )


def normalize_workspace_runtime_effect_path(
    path: str,
    *,
    workspace: str | Path | None = None,
) -> str:
    return normalize_workspace_file_path(
        path,
        extension=".efk",
        label="runtime effect path",
        workspace=workspace,
    )


def normalize_workspace_texture_path(
    path: str,
    *,
    workspace: str | Path | None = None,
) -> str:
    return normalize_workspace_file_path(
        path,
        extensions=TEXTURE_EXTENSIONS,
        label="texture path",
        workspace=workspace,
    )


def normalize_workspace_material_path(
    path: str,
    *,
    workspace: str | Path | None = None,
) -> str:
    return normalize_workspace_file_path(
        path,
        extension=".efkmat",
        label="material path",
        workspace=workspace,
    )


def normalize_workspace_model_path(
    path: str,
    *,
    workspace: str | Path | None = None,
) -> str:
    return normalize_workspace_file_path(
        path,
        extension=".efkmodel",
        label="model path",
        workspace=workspace,
    )


def normalize_workspace_file_path(
    path: str,
    *,
    extension: str | None = None,
    extensions: frozenset[str] | None = None,
    label: str,
    workspace: str | Path | None = None,
) -> str:
    allowed_extensions = extensions or frozenset({extension}) if extension else extensions
    if not allowed_extensions:
        raise EffekseerBridgeCommandError(f"{label} has no allowed extensions")

    requested_path = Path(path)
    if requested_path.is_absolute():
        raise EffekseerBridgeCommandError(f"{label} must be workspace-relative")
    if ".." in requested_path.parts:
        raise EffekseerBridgeCommandError(f"{label} must not contain '..'")
    if requested_path.suffix.lower() not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise EffekseerBridgeCommandError(f"{label} must use one of: {allowed}")

    workspace_path = resolve_workspace(workspace)
    resolved_path = ensure_workspace_path(requested_path, workspace_path)
    relative_path = resolved_path.relative_to(workspace_path)
    return relative_path.as_posix()

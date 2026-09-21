from __future__ import annotations

import json
import math
import random
import struct
import zlib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from effekseer_mcp.paths import ensure_workspace_path

BUILTIN_TEXTURE_DIR = "inputs/textures/builtin"
BUILTIN_TEXTURE_SET = "builtin"
BUILTIN_TEXTURE_ROLES = frozenset(
    {
        "core",
        "spark",
        "smoke",
        "slash",
        "ring",
        "trail",
        "ripple",
    }
)


class TextureLibraryError(ValueError):
    """Raised when a texture library request is invalid."""


@dataclass(frozen=True)
class BuiltinTexture:
    id: str
    filename: str
    role: str
    tags: tuple[str, ...]
    recommended_blend: str
    notes: str
    generator: Callable[[int], list[tuple[int, int, int, int]]]

    @property
    def path(self) -> str:
        return f"{BUILTIN_TEXTURE_DIR}/{self.filename}"

    def manifest_entry(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "path": self.path,
            "role": self.role,
            "tags": list(self.tags),
            "license": "generated_by_effekseer_mcp",
            "source": "procedural",
            "recommended_blend": self.recommended_blend,
            "notes": self.notes,
        }


def list_builtin_textures() -> list[dict[str, Any]]:
    """Return built-in procedural texture metadata with workspace-relative paths."""
    return [texture.manifest_entry() for texture in BUILTIN_TEXTURES]


def get_builtin_texture(role: str, variant: str | None = None) -> str:
    """Return a workspace-relative built-in texture path for a role."""
    role = require_role(role)
    if variant is not None:
        if not isinstance(variant, str) or not variant:
            raise TextureLibraryError("texture variant must be a non-empty string")
        for texture in BUILTIN_TEXTURES:
            if texture.role == role and (
                texture.id == variant or texture.filename == variant
            ):
                return texture.path
        raise TextureLibraryError(f"unknown built-in texture variant: {variant}")

    return get_default_texture_set()[role]


def get_default_texture_set() -> dict[str, str]:
    """Return the default role-to-texture mapping for high-level recipes."""
    return {
        "core": f"{BUILTIN_TEXTURE_DIR}/core_glow.png",
        "spark": f"{BUILTIN_TEXTURE_DIR}/spark_star.png",
        "smoke": f"{BUILTIN_TEXTURE_DIR}/smoke_puff_01.png",
        "slash": f"{BUILTIN_TEXTURE_DIR}/slash_arc.png",
        "ring": f"{BUILTIN_TEXTURE_DIR}/ring_soft.png",
        "trail": f"{BUILTIN_TEXTURE_DIR}/trail_streak.png",
        "ripple": f"{BUILTIN_TEXTURE_DIR}/ripple_ring.png",
    }


def resolve_texture_roles(
    texture_set: str | None,
    overrides: dict[str, str] | None,
) -> dict[str, str]:
    """Resolve texture roles from an allowlisted texture set and role overrides."""
    if texture_set is None or texture_set == BUILTIN_TEXTURE_SET:
        resolved = get_default_texture_set()
    else:
        raise TextureLibraryError(
            f"unsupported texture set: {texture_set}. Supported sets: {BUILTIN_TEXTURE_SET}"
        )

    if overrides is None:
        return resolved
    if not isinstance(overrides, dict):
        raise TextureLibraryError("texture overrides must be an object")

    for role, path in overrides.items():
        role = require_role(role)
        resolved[role] = validate_workspace_relative_texture_path(path)
    return resolved


def generate_builtin_textures(
    workspace: str | Path | None = None,
    *,
    size: int = 128,
) -> dict[str, Any]:
    """Generate built-in procedural RGBA PNG textures and a manifest."""
    if size < 16:
        raise TextureLibraryError("texture size must be at least 16")

    output_dir = ensure_workspace_path(BUILTIN_TEXTURE_DIR, workspace)
    output_dir.mkdir(parents=True, exist_ok=True)

    textures = []
    for texture in BUILTIN_TEXTURES:
        output_path = output_dir / texture.filename
        write_png_rgba(output_path, size, size, texture.generator(size))
        textures.append(texture.manifest_entry())

    manifest = {
        "texture_set": BUILTIN_TEXTURE_SET,
        "generated_at": "procedural",
        "textures": textures,
    }
    manifest_path = output_dir / "texture_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "texture_set": BUILTIN_TEXTURE_SET,
        "directory": BUILTIN_TEXTURE_DIR,
        "manifest_path": f"{BUILTIN_TEXTURE_DIR}/texture_manifest.json",
        "textures": textures,
    }


def ensure_builtin_textures(workspace: str | Path | None = None) -> dict[str, Any]:
    """Generate the built-in texture pack when its manifest is missing."""
    manifest_path = ensure_workspace_path(
        f"{BUILTIN_TEXTURE_DIR}/texture_manifest.json",
        workspace,
    )
    if manifest_path.exists():
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return generate_builtin_textures(workspace)


def require_role(role: str) -> str:
    if role not in BUILTIN_TEXTURE_ROLES:
        supported = ", ".join(sorted(BUILTIN_TEXTURE_ROLES))
        raise TextureLibraryError(
            f"unsupported texture role: {role}. Supported roles: {supported}"
        )
    return role


def validate_workspace_relative_texture_path(path: str) -> str:
    if not isinstance(path, str) or not path:
        raise TextureLibraryError("texture path must be a non-empty string")
    requested = Path(path)
    if requested.is_absolute():
        raise TextureLibraryError("texture path must be workspace-relative")
    if ".." in requested.parts:
        raise TextureLibraryError("texture path must not contain '..'")
    return requested.as_posix()


def write_png_rgba(
    path: Path,
    width: int,
    height: int,
    pixels: list[tuple[int, int, int, int]],
) -> None:
    if len(pixels) != width * height:
        raise TextureLibraryError("pixel count did not match image dimensions")

    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for r, g, b, a in pixels[y * width : (y + 1) * width]:
            raw.extend((clamp_byte(r), clamp_byte(g), clamp_byte(b), clamp_byte(a)))

    png = bytearray()
    png.extend(b"\x89PNG\r\n\x1a\n")
    png.extend(png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)))
    png.extend(png_chunk(b"IDAT", zlib.compress(bytes(raw), level=9)))
    png.extend(png_chunk(b"IEND", b""))
    path.write_bytes(bytes(png))


def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(chunk_type)
    checksum = zlib.crc32(data, checksum)
    return (
        struct.pack(">I", len(data))
        + chunk_type
        + data
        + struct.pack(">I", checksum & 0xFFFFFFFF)
    )


def clamp_byte(value: float | int) -> int:
    return max(0, min(255, int(round(value))))


def alpha_pixel(alpha: float) -> tuple[int, int, int, int]:
    value = clamp_byte(alpha)
    return (255, 255, 255, value)


def radial_falloff(size: int, x: int, y: int, radius: float = 1.0) -> float:
    center = (size - 1) / 2.0
    dx = (x - center) / (center * radius)
    dy = (y - center) / (center * radius)
    return math.sqrt(dx * dx + dy * dy)


def soft_circle(size: int) -> list[tuple[int, int, int, int]]:
    return [
        alpha_pixel(255.0 * max(0.0, 1.0 - radial_falloff(size, x, y) ** 2.2))
        for y in range(size)
        for x in range(size)
    ]


def core_glow(size: int) -> list[tuple[int, int, int, int]]:
    pixels = []
    for y in range(size):
        for x in range(size):
            d = radial_falloff(size, x, y)
            hot = max(0.0, 1.0 - d * 2.6)
            glow = max(0.0, 1.0 - d) ** 2.0
            pixels.append(alpha_pixel(255.0 * min(1.0, hot + glow * 0.75)))
    return pixels


def spark_dot(size: int) -> list[tuple[int, int, int, int]]:
    return [
        alpha_pixel(255.0 * max(0.0, 1.0 - radial_falloff(size, x, y) * 3.2) ** 1.5)
        for y in range(size)
        for x in range(size)
    ]


def spark_star(size: int) -> list[tuple[int, int, int, int]]:
    center = (size - 1) / 2.0
    pixels = []
    for y in range(size):
        for x in range(size):
            dx = abs(x - center) / center
            dy = abs(y - center) / center
            diagonal = abs(dx - dy)
            cross = max(0.0, 1.0 - min(dx, dy) * 7.0)
            diag = max(0.0, 1.0 - diagonal * 9.0) * max(0.0, 1.0 - (dx + dy) * 1.6)
            core = max(0.0, 1.0 - radial_falloff(size, x, y) * 4.0)
            pixels.append(alpha_pixel(255.0 * min(1.0, core + cross * 0.8 + diag * 0.7)))
    return pixels


def smoke_puff(seed: int) -> Callable[[int], list[tuple[int, int, int, int]]]:
    def generate(size: int) -> list[tuple[int, int, int, int]]:
        rng = random.Random(seed)
        blobs = [
            (
                rng.uniform(-0.35, 0.35),
                rng.uniform(-0.3, 0.3),
                rng.uniform(0.22, 0.42),
                rng.uniform(0.35, 0.85),
            )
            for _ in range(12)
        ]
        center = (size - 1) / 2.0
        pixels = []
        for y in range(size):
            for x in range(size):
                nx = (x - center) / center
                ny = (y - center) / center
                alpha = 0.0
                for bx, by, radius, weight in blobs:
                    d = math.sqrt((nx - bx) ** 2 + (ny - by) ** 2) / radius
                    alpha += max(0.0, 1.0 - d * d) * weight
                pixels.append(alpha_pixel(120.0 * min(1.0, alpha)))
        return blur_alpha(pixels, size, passes=2)

    return generate


def slash_arc(size: int) -> list[tuple[int, int, int, int]]:
    pixels = []
    center = (size - 1) / 2.0
    for y in range(size):
        for x in range(size):
            nx = (x - center) / center
            ny = (y - center) / center
            angle = math.atan2(ny, nx)
            radius = math.sqrt(nx * nx + ny * ny)
            arc_angle = -0.25 < angle < 1.15
            arc_radius = 0.45 < radius < 0.88
            taper = max(0.0, 1.0 - abs(radius - 0.66) * 7.0)
            pixels.append(alpha_pixel(255.0 * taper if arc_angle and arc_radius else 0.0))
    return blur_alpha(pixels, size, passes=1)


def ring_soft(size: int) -> list[tuple[int, int, int, int]]:
    pixels = []
    for y in range(size):
        for x in range(size):
            d = radial_falloff(size, x, y)
            ring = max(0.0, 1.0 - abs(d - 0.58) * 9.0)
            pixels.append(alpha_pixel(210.0 * ring))
    return blur_alpha(pixels, size, passes=1)


def trail_streak(size: int) -> list[tuple[int, int, int, int]]:
    pixels = []
    center = (size - 1) / 2.0
    for y in range(size):
        for x in range(size):
            nx = x / (size - 1)
            dy = abs(y - center) / center
            length = max(0.0, 1.0 - nx) ** 1.2
            thickness = max(0.0, 1.0 - dy * 7.5)
            pixels.append(alpha_pixel(255.0 * length * thickness))
    return blur_alpha(pixels, size, passes=1)


def ripple_ring(size: int) -> list[tuple[int, int, int, int]]:
    pixels = []
    for y in range(size):
        for x in range(size):
            d = radial_falloff(size, x, y, radius=0.9)
            alpha = max(0.0, 1.0 - abs(d - 0.72) * 12.0)
            alpha += max(0.0, 1.0 - abs(d - 0.43) * 14.0) * 0.55
            pixels.append(alpha_pixel(180.0 * min(1.0, alpha)))
    return blur_alpha(pixels, size, passes=1)


def blur_alpha(
    pixels: list[tuple[int, int, int, int]],
    size: int,
    *,
    passes: int,
) -> list[tuple[int, int, int, int]]:
    current = pixels
    for _ in range(passes):
        blurred = []
        for y in range(size):
            for x in range(size):
                total = 0
                count = 0
                for oy in (-1, 0, 1):
                    for ox in (-1, 0, 1):
                        sx = x + ox
                        sy = y + oy
                        if 0 <= sx < size and 0 <= sy < size:
                            total += current[sy * size + sx][3]
                            count += 1
                blurred.append(alpha_pixel(total / count))
        current = blurred
    return current


BUILTIN_TEXTURES = (
    BuiltinTexture(
        "soft_circle",
        "soft_circle.png",
        "core",
        ("soft", "circle", "alpha"),
        "Add",
        "Soft circular alpha mask for subtle glow sprites.",
        soft_circle,
    ),
    BuiltinTexture(
        "core_glow",
        "core_glow.png",
        "core",
        ("core", "glow", "alpha"),
        "Add",
        "Bright central glow for cores and magic bullets.",
        core_glow,
    ),
    BuiltinTexture(
        "spark_dot",
        "spark_dot.png",
        "spark",
        ("spark", "dot", "particle"),
        "Add",
        "Small round spark particle.",
        spark_dot,
    ),
    BuiltinTexture(
        "spark_star",
        "spark_star.png",
        "spark",
        ("spark", "star", "particle"),
        "Add",
        "Small star-like spark particle.",
        spark_star,
    ),
    BuiltinTexture(
        "smoke_puff_01",
        "smoke_puff_01.png",
        "smoke",
        ("smoke", "puff", "soft"),
        "Blend",
        "Soft procedural smoke puff variant 1.",
        smoke_puff(101),
    ),
    BuiltinTexture(
        "smoke_puff_02",
        "smoke_puff_02.png",
        "smoke",
        ("smoke", "puff", "soft"),
        "Blend",
        "Soft procedural smoke puff variant 2.",
        smoke_puff(202),
    ),
    BuiltinTexture(
        "slash_arc",
        "slash_arc.png",
        "slash",
        ("slash", "arc", "blade"),
        "Add",
        "Curved slash alpha mask.",
        slash_arc,
    ),
    BuiltinTexture(
        "ring_soft",
        "ring_soft.png",
        "ring",
        ("ring", "heal", "soft"),
        "Add",
        "Soft circular ring for healing or magic circles.",
        ring_soft,
    ),
    BuiltinTexture(
        "trail_streak",
        "trail_streak.png",
        "trail",
        ("trail", "streak", "motion"),
        "Add",
        "Horizontal streak for trails and afterimages.",
        trail_streak,
    ),
    BuiltinTexture(
        "ripple_ring",
        "ripple_ring.png",
        "ripple",
        ("ripple", "ring", "water"),
        "Blend",
        "Soft double ripple ring for water-style effects.",
        ripple_ring,
    ),
)

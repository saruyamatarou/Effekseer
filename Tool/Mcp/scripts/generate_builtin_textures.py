from __future__ import annotations

import argparse
from collections.abc import Sequence

from effekseer_mcp.config import load_config
from effekseer_mcp.texture_library import generate_builtin_textures


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate built-in procedural Effekseer texture PNGs.",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=128,
        help="Square texture size in pixels. Defaults to 128.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = generate_builtin_textures(load_config().workspace, size=args.size)
    print(f"Generated {len(result['textures'])} built-in textures")
    print(result["manifest_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

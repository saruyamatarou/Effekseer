"""Build a standalone MCP runtime (requires uv only on the build machine)."""
import argparse
from pathlib import Path
import shutil
import subprocess


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=root.parents[1] / "Dev/release")
    args = parser.parse_args()
    output = args.output.resolve()
    subprocess.run([
        "uv", "run", "--project", str(root), "--locked", "--group", "bundle",
        "python", "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
        "--name", "effekseer-mcp", "--paths", str(root / "src"),
        "--collect-all", "mcp", "--collect-all", "uvicorn",
        "--copy-metadata", "effekseer-mcp",
        "--add-data", f"{root / 'SampleEffects'}:SampleEffects",
        "--distpath", str(root / "dist"), "--workpath", str(root / "build"),
        "--specpath", str(root / "build"), str(root / "scripts/bundle_entry.py"),
    ], check=True, cwd=root)
    shutil.copytree(root / "dist/effekseer-mcp", output / "mcp", dirs_exist_ok=True)
    print(f"MCP runtime installed in {output / 'mcp'}")


if __name__ == "__main__":
    main()

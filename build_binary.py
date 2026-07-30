"""Build script for OSWG - builds SvelteKit UI and PyInstaller binary."""

import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
UI_DIR = ROOT / "ui"
STATIC_DEST = ROOT / "src" / "oswg" / "static"
DIST_DIR = ROOT / "dist"


def build_frontend() -> None:
    """Build the SvelteKit frontend."""
    if not UI_DIR.exists():
        print(f"UI directory not found at {UI_DIR}, skipping frontend build.")
        STATIC_DEST.mkdir(parents=True, exist_ok=True)
        (STATIC_DEST / "index.html").touch()
        return

    print("Building SvelteKit frontend...")

    if not (UI_DIR / "node_modules").exists():
        print("Installing npm dependencies...")
        subprocess.run(["npm", "ci"], cwd=UI_DIR, check=True)

    subprocess.run(["npm", "run", "build"], cwd=UI_DIR, check=True)

    build_output = UI_DIR / "build"
    if not build_output.exists():
        print("ERROR: SvelteKit build did not produce a 'build' directory")
        sys.exit(1)

    if STATIC_DEST.exists():
        shutil.rmtree(STATIC_DEST)
    shutil.copytree(build_output, STATIC_DEST)
    print(f"Static files copied to {STATIC_DEST}")


def build_binary() -> None:
    """Build the PyInstaller binary."""
    print("Building PyInstaller binary...")
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)

    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "oswg.spec", "--clean", "--noconfirm"],
        cwd=ROOT,
        check=True,
    )

    system = platform.system().lower()

    if system in ("darwin", "linux"):
        binary_name = "oswg"
    else:
        binary_name = "oswg.exe"

    binary_path = DIST_DIR / binary_name
    if binary_path.exists():
        size_mb = binary_path.stat().st_size / (1024 * 1024)
        print(f"Binary built: {binary_path} ({size_mb:.1f} MB)")
    else:
        print(f"ERROR: Binary not found at {binary_path}")
        sys.exit(1)


def main() -> None:
    build_frontend()
    build_binary()
    print("Build complete!")


if __name__ == "__main__":
    main()

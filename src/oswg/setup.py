"""Detection and installation helpers for OSWG's optional extras.

Used by ``oswg setup``. Stdlib-only so it works with no extra installed.
"""

from __future__ import annotations

import importlib.metadata as _md
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

# Approximate on-disk size in MB for the space estimate.
SIZE_MB = {
    "js": 136,  # playwright package + deps
    "chromium": 550,  # chromium + headless shell + ffmpeg
    "auth": 1,  # httpx-ntlm + ntlm-auth
    "hashcat": 80,
    "john": 40,
}


def in_venv() -> bool:
    return bool(os.environ.get("VIRTUAL_ENV")) or sys.prefix != sys.base_prefix


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def browser_cache_dir() -> Path:
    home = Path.home()
    system = platform.system()
    if system == "Darwin":
        return home / "Library" / "Caches" / "ms-playwright"
    if system == "Windows":
        local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
        return local / "ms-playwright"
    return home / ".cache" / "ms-playwright"


def chromium_installed() -> bool:
    cache = browser_cache_dir()
    if not cache.is_dir():
        return False
    try:
        return any(p.name.startswith("chromium") for p in cache.iterdir())
    except OSError:
        return False


def tool(name: str) -> str | None:
    return shutil.which(name)


def hashcat_hint() -> str:
    system = platform.system()
    if system == "Darwin":
        return "brew install hashcat"
    if system == "Windows":
        return "choco install hashcat"
    for mgr, cmd in (
        ("apt", "sudo apt install hashcat"),
        ("dnf", "sudo dnf install hashcat"),
        ("pacman", "sudo pacman -S hashcat"),
    ):
        if shutil.which(mgr):
            return cmd
    return "install hashcat with your system package manager"


def editable_source_dir() -> Path | None:
    """The source directory when oswg is installed editable, else None."""
    try:
        dist = _md.distribution("oswg")
        direct = Path(dist._path) / "direct_url.json"  # type: ignore[attr-defined]
        if not direct.exists():
            return None
        data = json.loads(direct.read_text())
        if data.get("dir_info", {}).get("editable"):
            url = data.get("url", "")
            if url.startswith("file://"):
                return Path(unquote(url[len("file://") :])).resolve()
    except Exception:
        return None
    return None


def pip_target(extra: str) -> str:
    src = editable_source_dir()
    if src is not None:
        return f"{src}[{extra}]"
    return f"oswg[{extra}]"


def detect() -> dict:
    return {
        "venv": in_venv(),
        "frozen": is_frozen(),
        "js": has_module("playwright"),
        "chromium": chromium_installed(),
        "auth": has_module("httpx_ntlm"),
        "hashcat": tool("hashcat"),
        "john": tool("john"),
    }


def run(cmd: list[str]) -> bool:
    """Run a command with live output; returns success."""
    try:
        return subprocess.run(cmd).returncode == 0
    except Exception as e:
        print(f"  failed to run: {e}")
        return False


def install_js() -> bool:
    return run([sys.executable, "-m", "pip", "install", pip_target("js")])


def install_chromium() -> bool:
    return run([sys.executable, "-m", "playwright", "install", "chromium"])


def install_auth() -> bool:
    return run([sys.executable, "-m", "pip", "install", pip_target("auth")])

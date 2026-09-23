"""Fixtures for Playwright E2E tests (app, fixture site, browser)."""

import os
import socket
import subprocess
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - depends on the `js` extra
    sync_playwright = None

TESTS_E2E = Path(__file__).parent

SITE_PAGES = {
    "index.html": "<h1>Home</h1><a href='p2.html'>two</a>",
    "p2.html": "<h1>Page Two</h1><a href='p3.html'>three</a>",
    "p3.html": "<h1>Page Three</h1><a href='p4.html'>four</a>",
    "p4.html": "<h1>Page Four</h1>",
}


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def site_url(tmp_path_factory):
    """Serve a tiny multi-page site on a free port."""
    root = tmp_path_factory.mktemp("site")
    for name, body in SITE_PAGES.items():
        (root / name).write_text(body)
    port = _free_port()
    handler = lambda *a, **k: SimpleHTTPRequestHandler(*a, directory=str(root), **k)  # noqa: E731
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}/"
    server.shutdown()


@pytest.fixture(scope="session")
def app_url(tmp_path_factory):
    """Boot the OSWG web app on a free port with an isolated data dir."""
    data_dir = tmp_path_factory.mktemp("oswg-data")
    port = _free_port()
    env = {**os.environ, "OSWG_DATA_DIR": str(data_dir)}
    proc = subprocess.Popen(
        [sys.executable, "-m", "oswg.cli", "ui", "--no-browser", "--port", str(port)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    import urllib.request

    deadline = time.time() + 60
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("oswg ui exited during startup")
        try:
            with urllib.request.urlopen(f"{base}/api/v1/info", timeout=2):
                yield base
                break
        except Exception:
            time.sleep(1)
    else:
        proc.kill()
        raise RuntimeError("oswg ui did not become ready in time")
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture(scope="session")
def browser():
    if sync_playwright is None:
        pytest.skip("playwright not installed — run `pip install -e '.[js]'`")
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def page(browser):
    context = browser.new_context()
    p = context.new_page()
    yield p
    context.close()


@pytest.fixture(scope="session", autouse=True)
def _require_ui_build():
    pkg = Path(os.path.dirname(__import__("oswg").__file__))
    if not (pkg / "static").exists():
        pytest.skip("UI not built — run `make build` first (CI does this before e2e)")
    yield

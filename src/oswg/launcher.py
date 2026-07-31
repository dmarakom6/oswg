"""UI launcher - starts FastAPI server in a background thread with auto port increment."""

from __future__ import annotations

import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

from oswg import __version__


def find_free_port(start_port: int = 8000, max_attempts: int = 10) -> int:
    """Find a free port starting from start_port, auto-incrementing if busy."""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port found in range {start_port}-{start_port + max_attempts - 1}")


def _get_static_path() -> Path:
    """Get the path to the bundled SvelteKit static files."""
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS) / "oswg" / "static"
    else:
        base = Path(__file__).parent / "static"
    if not base.exists():
        base.mkdir(parents=True, exist_ok=True)
    return base


def _create_app(static_path: Path):
    """Create the FastAPI app with static file serving."""
    from contextlib import asynccontextmanager

    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware

    from oswg.database import db
    from oswg.routers import generate, jobs, mutate, scrape
    from oswg.services.progress import progress_tracker

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await db.init()
        yield

    app = FastAPI(
        title="OSWG API",
        version=__version__,
        description="API for generating targeted wordlists from website content",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(generate.router, prefix="/api/v1", tags=["generate"])
    app.include_router(scrape.router, prefix="/api/v1", tags=["scrape"])
    app.include_router(mutate.router, prefix="/api/v1", tags=["mutate"])
    app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    if (static_path / "index.html").exists():

        class SafeStaticFiles:
            """ASGI app that serves static files but passes through WebSocket/lifespan scopes."""

            def __init__(self, directory: str, html: bool = False):
                from fastapi.staticfiles import StaticFiles

                self._app = StaticFiles(directory=directory, html=html)

            async def __call__(self, scope, receive, send):
                if scope["type"] == "http":
                    return await self._app(scope, receive, send)

        app.mount("/", SafeStaticFiles(directory=str(static_path), html=True), name="static")
    else:
        @app.get("/")
        async def serve_index():
            return {
                "message": "OSWG API is running. Web UI not bundled in this install. Use the CLI: oswg --help"
            }

    @app.websocket("/ws/jobs/{job_id}")
    async def websocket_endpoint(websocket: WebSocket, job_id: str):
        await websocket.accept()
        await progress_tracker.connect(job_id, websocket)
        try:
            progress = progress_tracker.get_progress(job_id)
            if progress:
                await websocket.send_json(
                    {
                        "job_id": job_id,
                        "status": progress["status"],
                        "progress": progress["progress"],
                        "message": progress.get("message"),
                    }
                )
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            await progress_tracker.disconnect(job_id, websocket)
        except Exception:
            await progress_tracker.disconnect(job_id, websocket)

    return app


def _wait_for_server(host: str, port: int, timeout: float = 10.0) -> bool:
    """Wait for the server to be ready."""
    import httpx

    url = f"http://{host}:{port}/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with httpx.Client(timeout=1.0) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    return True
        except Exception:
            time.sleep(0.2)
    return False


def start_server(host: str = "127.0.0.1", port: int = 8000, open_browser: bool = True) -> None:
    """Start the OSWG web dashboard."""
    import uvicorn  # Lazy import: avoids hang on frozen app startup when not using UI

    actual_port = find_free_port(port)

    static_path = _get_static_path()
    app = _create_app(static_path)

    def _run_server():
        uvicorn.run(app, host=host, port=actual_port, log_level="warning")

    server_thread = threading.Thread(target=_run_server, daemon=True)
    server_thread.start()

    url = f"http://{host}:{actual_port}"

    if open_browser:
        if not webbrowser.open(url):
            print(f"Could not open browser. Visit: {url}")
        else:
            print(f"Dashboard opened at {url}")
    else:
        print(f"Dashboard available at {url}")

    print("Press Ctrl+C to stop the server.")
    print(f"OSWG v{__version__}")

    try:
        while server_thread.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nShutting down...")

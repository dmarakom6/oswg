"""System router - liveness, readiness, and app info."""

from __future__ import annotations

import os
import time
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from oswg import __version__
from oswg.database import db
from oswg.services.file_manager import file_manager
from oswg.services.job_manager import job_manager

router = APIRouter()

_START_TIME = time.monotonic()


def _uptime_seconds() -> int:
    return int(time.monotonic() - _START_TIME)


def _js_available() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


def _storage_writable(path: Path) -> bool:
    return path.is_dir() and os.access(path, os.W_OK)


@router.get("/health")
async def health():
    """Liveness check: 200 while the process is running."""
    return {
        "status": "healthy",
        "version": __version__,
        "uptime_seconds": _uptime_seconds(),
    }


@router.get("/api/v1/info")
async def info():
    """App version and optional-feature availability for the web UI."""
    return {"version": __version__, "js_available": _js_available()}


@router.get("/health/ready")
async def readiness():
    """Readiness check: verifies critical dependencies.

    Returns 200 when healthy, 503 when the database or storage is unhealthy.
    """
    checks: dict = {}
    healthy = True

    try:
        latency = await db.ping()
        checks["database"] = {"ok": True, "latency_ms": round(latency, 2)}
    except Exception as e:
        healthy = False
        checks["database"] = {"ok": False, "error": str(e)}

    storage_path = file_manager.storage_path
    try:
        writable = _storage_writable(storage_path)
        if writable:
            stats = file_manager.get_storage_stats()
            files = stats["total_files"]
            size_mb = stats["total_size_mb"]
        else:
            files = 0
            size_mb = 0.0
        checks["storage"] = {
            "ok": writable,
            "path": str(storage_path),
            "writable": writable,
            "files": files,
            "size_mb": size_mb,
        }
        if not writable:
            healthy = False
    except Exception as e:
        healthy = False
        checks["storage"] = {
            "ok": False,
            "path": str(storage_path),
            "writable": False,
            "error": str(e),
        }

    checks["js_render"] = {"ok": _js_available()}

    try:
        active_jobs: int | None = len(await job_manager.get_active_jobs())
    except Exception:
        active_jobs = None

    payload = {
        "status": "healthy" if healthy else "unhealthy",
        "version": __version__,
        "uptime_seconds": _uptime_seconds(),
        "checks": checks,
        "active_jobs": active_jobs,
    }
    return JSONResponse(payload, status_code=200 if healthy else 503)

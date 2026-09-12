"""Tests for the health, readiness, and info endpoints."""

import httpx
import pytest
from fastapi import FastAPI

from oswg.database import db
from oswg.routers import system
from oswg.services.file_manager import file_manager


@pytest.fixture
async def client(tmp_path, monkeypatch):
    (tmp_path / "db").mkdir()
    (tmp_path / "storage").mkdir()
    monkeypatch.setattr(db, "db_path", tmp_path / "db" / "oswg-test.db")
    monkeypatch.setattr(file_manager, "storage_path", tmp_path / "storage")
    await db.init()

    app = FastAPI()
    app.include_router(system.router)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_liveness(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert isinstance(body["version"], str) and body["version"]
    assert isinstance(body["uptime_seconds"], int)
    assert body["uptime_seconds"] >= 0


async def test_info(client):
    resp = await client.get("/api/v1/info")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["version"], str)
    assert isinstance(body["js_available"], bool)


async def test_readiness_healthy(client):
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["checks"]["database"]["ok"] is True
    assert body["checks"]["database"]["latency_ms"] >= 0
    assert body["checks"]["storage"]["ok"] is True
    assert body["checks"]["storage"]["writable"] is True
    assert body["checks"]["storage"]["files"] == 0
    assert isinstance(body["checks"]["js_render"]["ok"], bool)
    assert body["active_jobs"] == 0


async def test_readiness_db_failure(client, monkeypatch):
    async def broken_ping():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(db, "ping", broken_ping)

    resp = await client.get("/health/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "unhealthy"
    assert body["checks"]["database"]["ok"] is False
    assert "database unavailable" in body["checks"]["database"]["error"]
    assert body["checks"]["storage"]["ok"] is True


async def test_readiness_storage_unwritable(client, monkeypatch):
    monkeypatch.setattr(system, "_storage_writable", lambda path: False)

    resp = await client.get("/health/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "unhealthy"
    assert body["checks"]["storage"]["ok"] is False
    assert body["checks"]["storage"]["writable"] is False
    assert body["checks"]["database"]["ok"] is True

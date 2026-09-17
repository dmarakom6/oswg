"""Tests for the URL history endpoint."""

import httpx
import pytest
from fastapi import FastAPI

from oswg.database import db
from oswg.models import JobType
from oswg.routers import jobs as jobs_router


@pytest.fixture
async def client(tmp_path, monkeypatch):
    (tmp_path / "db").mkdir()
    monkeypatch.setattr(db, "db_path", tmp_path / "db" / "oswg-test.db")
    db._url_history_cache = None
    await db.init()
    app = FastAPI()
    app.include_router(jobs_router.router, prefix="/api/v1")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _seed_job(job_id: str, url: str):
    await db.create_job(
        job_id=job_id,
        job_type=JobType.GENERATE,
        config={"url": url},
        retention_seconds=3600,
    )


async def test_url_history_orders_by_count(client):
    await _seed_job("a", "https://example.com/a")
    await _seed_job("b", "https://example.com/a")
    await _seed_job("c", "https://example.com/b")

    resp = await client.get("/api/v1/jobs/url-history")
    assert resp.status_code == 200
    urls = resp.json()["urls"]
    assert [u["url"] for u in urls] == ["https://example.com/a", "https://example.com/b"]
    assert urls[0]["count"] == 2


async def test_url_history_filters_by_q(client):
    await _seed_job("a", "https://example.com/a")
    await _seed_job("b", "https://docs.python.org/3/")

    resp = await client.get("/api/v1/jobs/url-history", params={"q": "python"})
    urls = resp.json()["urls"]
    assert [u["url"] for u in urls] == ["https://docs.python.org/3/"]


async def test_url_history_empty(client):
    resp = await client.get("/api/v1/jobs/url-history")
    assert resp.json()["urls"] == []


async def test_url_history_invalidated_on_delete(client):
    await _seed_job("a", "https://example.com/a")
    assert len((await client.get("/api/v1/jobs/url-history")).json()["urls"]) == 1

    await db.delete_job("a")
    assert db._url_history_cache is None
    assert (await client.get("/api/v1/jobs/url-history")).json()["urls"] == []


async def test_clear_all_jobs_deletes_everything(client):
    await _seed_job("a", "https://example.com/a")
    await _seed_job("b", "https://example.com/b")

    resp = await client.post("/api/v1/jobs/clear")
    assert resp.status_code == 200
    assert resp.json()["cleared"] == 2
    assert db._url_history_cache is None
    assert (await client.get("/api/v1/jobs/url-history")).json()["urls"] == []


async def test_url_history_excludes_expired(client, monkeypatch):
    await _seed_job("a", "https://example.com/a")
    # Force the job's expiry into the past.
    import aiosqlite

    async with aiosqlite.connect(db.db_path) as conn:
        await conn.execute(
            "UPDATE jobs SET expires_at = ? WHERE id = 'a'",
            ("2000-01-01T00:00:00",),
        )
        await conn.commit()
    db._url_history_cache = None

    assert (await client.get("/api/v1/jobs/url-history")).json()["urls"] == []

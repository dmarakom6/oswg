"""Tests for the keyword-cloud word counts (scrape + generate)."""

import http.server
import socketserver
import threading
from contextlib import contextmanager

import httpx
import pytest
from fastapi import FastAPI

from oswg.core.generator import WordlistGenerator
from oswg.core.models import GenerationConfig
from oswg.core.scraper import Scraper
from oswg.routers import jobs as jobs_router
from oswg.services.file_manager import file_manager
from oswg.services.job_manager import job_manager as job_manager_singleton

PAGE = b"""<html><body>
<h1>alpha beta alpha gamma alpha</h1>
<p>delta epsilon</p>
<a href="/page2.html">two</a>
</body></html>"""
PAGE2 = b"""<html><body><h1>alpha beta zeta</h1></body></html>"""


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = PAGE2 if self.path.startswith("/page2") else PAGE
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # silence request logging
        pass


@contextmanager
def _serving():
    with socketserver.TCPServer(("127.0.0.1", 0), _Handler) as httpd:
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{httpd.server_address[1]}/"
        finally:
            httpd.shutdown()


# --- scraper captures real keyword frequencies ---------------------------


async def test_scraper_captures_keyword_counts():
    with _serving() as base:
        scraper = Scraper(max_pages=3)
        content = await scraper.scrape(base)
    assert content.keyword_counts
    assert content.keyword_counts["alpha"] >= 4  # 3 on home + 1 on page2
    assert content.keyword_counts["beta"] >= 2
    assert set(content.keyword_counts) == set(content.keywords)


# --- generator computes mutation-family sizes -----------------------------


async def test_generator_base_word_families():
    with _serving() as base:
        config = GenerationConfig(target_size=50, min_word_length=1)
        result = await WordlistGenerator().generate(base, config)
    assert result.base_word_counts
    assert all(v >= 1 for v in result.base_word_counts.values())
    assert set(result.base_word_counts) <= set(result.base_words)
    # The most productive base word appears in the wordlist the most.
    biggest = max(result.base_word_counts, key=result.base_word_counts.get)
    assert biggest in result.words or any(biggest in w for w in result.words)


# --- API endpoint ---------------------------------------------------------


@pytest.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setattr(file_manager, "storage_path", tmp_path)
    app = FastAPI()
    app.include_router(jobs_router.router, prefix="/api/v1")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_word_counts_endpoint(client, monkeypatch):
    async def fake_status(job_id):
        return {"id": job_id, "status": "completed"}

    monkeypatch.setattr(job_manager_singleton, "get_job_status", fake_status)
    file_manager.save_word_counts("job1", {"alpha": 5, "beta": 9, "gamma": 2})

    resp = await client.get("/api/v1/jobs/job1/word-counts")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert [w["word"] for w in body["words"]] == ["beta", "alpha", "gamma"]
    assert body["words"][0]["count"] == 9


async def test_word_counts_limit(client, monkeypatch):
    async def fake_status(job_id):
        return {"id": job_id, "status": "completed"}

    monkeypatch.setattr(job_manager_singleton, "get_job_status", fake_status)
    file_manager.save_word_counts("job1", {"a": 1, "b": 2, "c": 3})

    resp = await client.get("/api/v1/jobs/job1/word-counts?limit=2")
    assert resp.status_code == 200
    assert len(resp.json()["words"]) == 2
    assert resp.json()["words"][0]["word"] == "c"


async def test_word_counts_404(client, monkeypatch):
    async def fake_status(job_id):
        return {"id": job_id, "status": "completed"}

    monkeypatch.setattr(job_manager_singleton, "get_job_status", fake_status)
    resp = await client.get("/api/v1/jobs/nope/word-counts")
    assert resp.status_code == 404


async def test_word_counts_requires_completed(client, monkeypatch):
    async def fake_status(job_id):
        return {"id": job_id, "status": "processing"}

    monkeypatch.setattr(job_manager_singleton, "get_job_status", fake_status)
    resp = await client.get("/api/v1/jobs/job1/word-counts")
    assert resp.status_code == 400

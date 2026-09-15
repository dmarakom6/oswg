"""Tests for the mutation tree (generate jobs)."""

import http.server
import socketserver
import threading
from contextlib import contextmanager

import httpx
import pytest
from fastapi import FastAPI

from oswg.core.generator import WordlistGenerator
from oswg.core.models import GenerationConfig
from oswg.routers import jobs as jobs_router
from oswg.services.file_manager import file_manager
from oswg.services.job_manager import job_manager as job_manager_singleton

PAGE = b"""<html><body>
<h1>alpha gamma</h1>
<p>delta epsilon</p>
<a href="/page2.html">two</a>
</body></html>"""
PAGE2 = b"""<html><body><h1>zeta theta</h1></body></html>"""


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = PAGE2 if self.path.startswith("/page2") else PAGE
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
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


async def test_generator_builds_mutation_tree():
    with _serving() as base:
        config = GenerationConfig(target_size=200, min_word_length=1)
        result = await WordlistGenerator().generate(base, config)
    assert result.mutation_tree
    output = set(result.words)
    for base_word, variants in result.mutation_tree.items():
        assert base_word in result.base_words
        assert variants
        assert all(v in output for v in variants)


@pytest.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setattr(file_manager, "storage_path", tmp_path)
    app = FastAPI()
    app.include_router(jobs_router.router, prefix="/api/v1")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_mutation_tree_endpoint(client, monkeypatch):
    async def fake_status(job_id):
        return {"id": job_id, "status": "completed"}

    monkeypatch.setattr(job_manager_singleton, "get_job_status", fake_status)
    file_manager.save_mutation_tree("job1", {"apple": ["apple", "APPLE"], "pear": ["pear"]})

    resp = await client.get("/api/v1/jobs/job1/mutation-tree")
    assert resp.status_code == 200
    tree = resp.json()["tree"]
    assert tree["apple"] == ["apple", "APPLE"]
    assert tree["pear"] == ["pear"]


async def test_mutation_tree_404(client, monkeypatch):
    async def fake_status(job_id):
        return {"id": job_id, "status": "completed"}

    monkeypatch.setattr(job_manager_singleton, "get_job_status", fake_status)
    resp = await client.get("/api/v1/jobs/nope/mutation-tree")
    assert resp.status_code == 404

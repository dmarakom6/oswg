"""Tests for job templates and presets."""

import httpx
import pytest
from fastapi import FastAPI

from oswg.core.presets import PRESETS
from oswg.database import db
from oswg.models import GenerateRequest, JobType
from oswg.routers import templates as templates_router
from oswg.services.template_store import template_store


@pytest.fixture
async def client(tmp_path, monkeypatch):
    (tmp_path / "db").mkdir()
    monkeypatch.setattr(db, "db_path", tmp_path / "db" / "oswg-test.db")
    monkeypatch.setattr(template_store, "path", tmp_path / "templates.json")
    await db.init()
    app = FastAPI()
    app.include_router(templates_router.router, prefix="/api/v1")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _gen_config():
    return {
        "url": "https://example.com",
        "size": 1000,
        "max_pages": 5,
        "enable_leet": False,
        "auth_pass": "secret",
        "cookies": {"session": "abc"},
    }


async def test_template_store_crud_and_sanitize(tmp_path):
    store = template_store
    store.path = tmp_path / "templates.json"
    record = store.save("my-gen", "generate", _gen_config())
    assert record["name"] == "my-gen"

    saved = store.get("my-gen")["config"]
    assert "auth_pass" not in saved and "cookies" not in saved
    assert saved["size"] == 1000

    assert [t["name"] for t in store.list()] == ["my-gen"]
    assert store.delete("my-gen") is True
    assert store.delete("my-gen") is False


def test_presets_are_valid_generate_configs():
    for name, config in PRESETS.items():
        full = {"url": "https://example.com", "size": 1, "max_pages": 1, **config}
        GenerateRequest.model_validate(full)


async def test_save_and_list_template(client):
    resp = await client.post(
        "/api/v1/templates",
        json={"name": "t1", "type": "generate", "config": _gen_config()},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "t1"

    listed = await client.get("/api/v1/templates")
    assert listed.status_code == 200
    names = [t["name"] for t in listed.json()["templates"]]
    assert "t1" in names


async def test_save_template_drops_secrets(client):
    await client.post(
        "/api/v1/templates",
        json={"name": "t1", "type": "generate", "config": _gen_config()},
    )
    stored = template_store.get("t1")["config"]
    assert "auth_pass" not in stored and "cookies" not in stored


async def test_save_template_from_job(client):
    await db.create_job(
        job_id="job1",
        job_type=JobType.GENERATE,
        config=_gen_config(),
        retention_seconds=3600,
    )
    resp = await client.post(
        "/api/v1/templates", json={"name": "fromjob", "from_job": "job1"}
    )
    assert resp.status_code == 200
    assert resp.json()["type"] == "generate"
    assert "auth_pass" not in template_store.get("fromjob")["config"]


async def test_save_template_from_missing_job(client):
    resp = await client.post(
        "/api/v1/templates", json={"name": "x", "from_job": "nope"}
    )
    assert resp.status_code == 404


async def test_delete_template(client):
    await client.post(
        "/api/v1/templates",
        json={"name": "t1", "type": "generate", "config": _gen_config()},
    )
    resp = await client.delete("/api/v1/templates/t1")
    assert resp.status_code == 200 and resp.json()["deleted"] is True
    assert (await client.delete("/api/v1/templates/t1")).status_code == 404


async def test_presets_endpoint(client):
    resp = await client.get("/api/v1/presets")
    assert resp.status_code == 200
    assert set(resp.json()["presets"]) == {"quick", "standard", "aggressive", "extreme"}


def test_config_overlay_applies_base_when_flag_at_default():
    from oswg.cli import _apply_config_overlay
    from oswg.core.models import GenerationConfig

    config = GenerationConfig(target_size=10000, enable_leet=True)
    flags = {"size": 10000, "no_leet": False}
    _apply_config_overlay(config, {"size": 5000, "enable_leet": False}, flags)
    assert config.target_size == 5000
    assert config.enable_leet is False


def test_config_overlay_keeps_flag_when_not_default():
    from oswg.cli import _apply_config_overlay
    from oswg.core.models import GenerationConfig

    config = GenerationConfig(target_size=20000)
    _apply_config_overlay(config, {"size": 5000}, {"size": 20000})
    assert config.target_size == 20000

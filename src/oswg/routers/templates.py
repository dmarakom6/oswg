"""Templates & presets router."""

import json

from fastapi import APIRouter, HTTPException

from oswg.core.presets import PRESETS
from oswg.database import db
from oswg.models import ErrorResponse, GenerateRequest, ScrapeRequest, TemplateSaveRequest
from oswg.services.template_store import template_store

router = APIRouter()

_VALID_TYPES = ("generate", "scrape")


def _validate_config(type_: str, config: dict) -> None:
    try:
        if type_ == "generate":
            GenerateRequest.model_validate(config)
        elif type_ == "scrape":
            ScrapeRequest.model_validate(config)
        else:
            raise HTTPException(status_code=400, detail="type must be 'generate' or 'scrape'")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid {type_} config: {e}") from e


@router.get("/templates")
async def list_templates():
    """List saved templates (metadata only)."""
    return {"templates": template_store.list()}


@router.post(
    "/templates",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "Referenced job not found"},
    },
)
async def save_template(request: TemplateSaveRequest):
    """Save a template from a config or from a completed job's config."""
    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Template name is required")

    if request.from_job:
        job = await db.get_job(request.from_job)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {request.from_job} not found")
        if job["type"] not in _VALID_TYPES:
            raise HTTPException(status_code=400, detail="Only generate/scrape jobs can be templates")
        type_ = job["type"]
        try:
            config = json.loads(job["config"])
        except (ValueError, TypeError) as e:
            raise HTTPException(status_code=400, detail="Stored job config is invalid") from e
    else:
        type_ = request.type
        config = request.config
        if type_ not in _VALID_TYPES:
            raise HTTPException(status_code=400, detail="type must be 'generate' or 'scrape'")
        if not config:
            raise HTTPException(status_code=400, detail="config is required (or use from_job)")

    _validate_config(type_, config)
    return template_store.save(name, type_, config)


@router.get(
    "/templates/{name}",
    responses={
        404: {"model": ErrorResponse, "description": "Template not found"},
    },
)
async def get_template(name: str):
    """Get a single template including its config."""
    record = template_store.get(name)
    if not record:
        raise HTTPException(status_code=404, detail=f"Template '{name}' not found")
    return {"name": name, "type": record.get("type"), "config": record.get("config", {})}


@router.delete(
    "/templates/{name}",
    responses={
        404: {"model": ErrorResponse, "description": "Template not found"},
    },
)
async def delete_template(name: str):
    """Delete a saved template."""
    if not template_store.delete(name):
        raise HTTPException(status_code=404, detail=f"Template '{name}' not found")
    return {"deleted": True}


@router.get("/presets")
async def get_presets():
    """Built-in generate presets (lightweight -> extreme)."""
    return {"presets": PRESETS}

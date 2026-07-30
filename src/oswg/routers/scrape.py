"""Scrape router - keyword scraping endpoint."""

import json

from fastapi import APIRouter, BackgroundTasks, HTTPException

from oswg.config import settings
from oswg.core.scraper import Scraper
from oswg.models import (
    ErrorResponse,
    JobResponse,
    JobStatus,
    JobType,
    ScrapeRequest,
)
from oswg.services.file_manager import file_manager
from oswg.services.job_manager import job_manager

router = APIRouter()


async def execute_scrape(job_id: str) -> dict:
    """Execute keyword scraping job."""
    job = await job_manager.get_job_status(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    config_data = json.loads(job["config"])

    await job_manager.update_progress(job_id, 10.0, "Starting scraper...")

    scraper = Scraper(
        max_pages=config_data.get("max_pages", settings.max_pages_default)
    )

    await job_manager.update_progress(job_id, 30.0, "Scraping website...")

    content = await scraper.scrape(config_data["url"])

    await job_manager.update_progress(job_id, 70.0, "Processing keywords...")

    keywords = content.keywords

    await job_manager.update_progress(job_id, 85.0, "Saving keywords...")

    file_path = file_manager.save_words(job_id, keywords)

    await job_manager.update_progress(job_id, 95.0, "Finalizing...")

    return {
        "file_path": str(file_path),
        "keywords_count": len(keywords),
        "title": content.title,
        "meta_description": content.meta_description,
    }


@router.post(
    "/scrape",
    response_model=JobResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def scrape_keywords(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
) -> JobResponse:
    """Scrape keywords from a website URL."""
    try:
        config = {
            "url": request.url,
            "max_pages": request.max_pages,
        }

        job_id = await job_manager.create_job(
            job_type=JobType.SCRAPE,
            config=config,
            executor=execute_scrape,
            retention_seconds=request.retention_seconds,
        )

        background_tasks.add_task(job_manager.execute_job, job_id, execute_scrape)

        return JobResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            message="Keyword scraping started",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

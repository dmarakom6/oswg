"""Generate router - wordlist generation endpoint."""

from fastapi import APIRouter, BackgroundTasks, HTTPException

from oswg.config import settings
from oswg.core import WordlistGenerator
from oswg.core.models import GenerationConfig
from oswg.models import (
    ErrorResponse,
    GenerateRequest,
    JobResponse,
    JobStatus,
    JobType,
)
from oswg.services.file_manager import file_manager
from oswg.services.job_manager import job_manager

router = APIRouter()


async def execute_generate(job_id: str) -> dict:
    """Execute wordlist generation job."""
    job = await job_manager.get_job_status(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    import json

    config_data = json.loads(job["config"])

    await job_manager.update_progress(job_id, 10.0, "Starting scraper...")

    generator = WordlistGenerator()
    generator.scraper.max_pages = config_data.get(
        "max_pages", settings.max_pages_default
    )
    generator.scraper.min_word_length = config_data.get("min_length", 3)
    generator.scraper.max_word_length = config_data.get("max_length", 32)

    await job_manager.update_progress(job_id, 20.0, "Scraping website...")

    generation_config = GenerationConfig(
        target_size=config_data.get("size", 10000),
        min_word_length=config_data.get("min_length", 3),
        max_word_length=config_data.get("max_length", 32),
        enable_leet=config_data.get("enable_leet", True),
        enable_numbers=config_data.get("enable_numbers", True),
        enable_special=config_data.get("enable_special", False),
        leet_level=config_data.get("leet_level", 1),
        deduplicate=config_data.get("deduplicate", True),
        filter_stopwords=config_data.get("filter_stopwords", True),
        stopword_threshold=config_data.get("stopword_threshold", 0.5),
        extra_stopwords=config_data.get("extra_stopwords", []),
    )

    await job_manager.update_progress(job_id, 40.0, "Generating mutations...")

    result = await generator.generate(
        config_data["url"],
        generation_config,
        urls=config_data.get("urls") or None,
        sitemap=config_data.get("sitemap", False),
    )

    await job_manager.update_progress(job_id, 80.0, "Saving wordlist...")

    file_path = file_manager.save_words(job_id, result.words)

    await job_manager.update_progress(job_id, 95.0, "Finalizing...")

    return {
        "file_path": str(file_path),
        "words_count": result.unique_words,
        "source_keywords": result.source_keywords,
    }


@router.post(
    "/generate",
    response_model=JobResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def generate_wordlist(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
) -> JobResponse:
    """Generate a targeted wordlist from a website URL."""
    try:
        config = {
            "url": request.url,
            "urls": request.urls,
            "sitemap": request.sitemap,
            "size": request.size,
            "max_pages": request.max_pages,
            "min_length": request.min_length,
            "max_length": request.max_length,
            "enable_leet": request.enable_leet,
            "enable_numbers": request.enable_numbers,
            "enable_special": request.enable_special,
            "leet_level": request.leet_level,
            "deduplicate": request.deduplicate,
            "filter_stopwords": request.filter_stopwords,
            "stopword_threshold": request.stopword_threshold,
            "extra_stopwords": request.extra_stopwords,
        }

        job_id = await job_manager.create_job(
            job_type=JobType.GENERATE,
            config=config,
            executor=execute_generate,
            retention_seconds=request.retention_seconds,
        )

        background_tasks.add_task(job_manager.execute_job, job_id, execute_generate)

        return JobResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            message="Wordlist generation started",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

"""Scrape router - keyword scraping endpoint."""

import json

from fastapi import APIRouter, BackgroundTasks, HTTPException

from oswg.config import settings
from oswg.core.cookie_file import parse_cookie_file
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


def _parse_cookie_text(text: str | None) -> list:
    """Parse pasted cookies.txt contents into Cookie objects."""
    if not text:
        return []
    return parse_cookie_file(text)


def _parse_session_text(text: str | None) -> dict | None:
    """Parse pasted storage_state JSON text."""
    from oswg.core.session import parse_session_text

    try:
        return parse_session_text(text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


async def execute_scrape(job_id: str) -> dict:
    """Execute keyword scraping job."""
    job = await job_manager.get_job_status(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    config_data = json.loads(job["config"])

    await job_manager.update_progress(job_id, 10.0, "Starting scraper...")

    scraper = Scraper(
        max_pages=config_data.get("max_pages", settings.max_pages_default),
        timeout=config_data.get("timeout", 30.0),
        respect_robots=config_data.get("respect_robots", False),
        user_agent=config_data.get("user_agent"),
        rate_limit=config_data.get("rate_limit", 0.0),
        jitter=config_data.get("jitter", False),
        headers=config_data.get("headers") or None,
        cookies=config_data.get("cookies") or None,
        proxy=config_data.get("proxy"),
        allow_subdomains=config_data.get("allow_subdomains", False),
        include_paths=config_data.get("include_paths", []),
        exclude_patterns=config_data.get("exclude_patterns", []),
        crawl_strategy=config_data.get("crawl_strategy", "bfs"),
        js_render=config_data.get("js_render", False),
        storage_state=_parse_session_text(config_data.get("storage_state")),
    )
    scraper.cookie_jar = _parse_cookie_text(config_data.get("cookie_file")) + scraper.cookie_jar

    await job_manager.update_progress(job_id, 30.0, "Scraping website...")

    urls = config_data.get("urls") or None
    sitemap = config_data.get("sitemap", False)

    if urls:
        content = await scraper.scrape_urls([config_data["url"]] + urls, sitemap=sitemap)
    else:
        content = await scraper.scrape(config_data["url"], sitemap=sitemap)

    await job_manager.update_progress(job_id, 70.0, "Processing keywords...")

    keywords = content.keywords

    await job_manager.update_progress(job_id, 85.0, "Saving keywords...")

    file_path = file_manager.save_words(job_id, keywords)
    file_manager.save_graph(job_id, scraper.link_graph)

    screenshot_count = 0
    for i, png in enumerate(scraper.screenshots):
        if png is not None:
            file_manager.save_screenshot(job_id, i, png)
            screenshot_count += 1

    await job_manager.update_progress(job_id, 95.0, "Finalizing...")

    return {
        "file_path": str(file_path),
        "keywords_count": len(keywords),
        "title": content.title,
        "meta_description": content.meta_description,
        "crawl_strategy": config_data.get("crawl_strategy", "bfs"),
        "screenshot_count": screenshot_count,
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
        _parse_session_text(request.storage_state)
        config = {
            "url": request.url,
            "urls": request.urls,
            "sitemap": request.sitemap,
            "max_pages": request.max_pages,
            "timeout": request.timeout,
            "respect_robots": request.respect_robots,
            "user_agent": request.user_agent,
            "rate_limit": request.rate_limit,
            "jitter": request.jitter,
            "headers": request.headers,
            "cookies": request.cookies,
            "cookie_file": request.cookie_file,
            "storage_state": request.storage_state,
            "proxy": request.proxy,
            "allow_subdomains": request.allow_subdomains,
            "include_paths": request.include_paths,
            "exclude_patterns": request.exclude_patterns,
            "crawl_strategy": request.crawl_strategy,
            "js_render": request.js_render,
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

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

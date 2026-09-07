"""Generate router - wordlist generation endpoint."""

from fastapi import APIRouter, BackgroundTasks, HTTPException

from oswg.config import settings
from oswg.core import WordlistGenerator
from oswg.core.models import GenerationConfig, default_years
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


def _resolve_merge_words(request: GenerateRequest) -> list[str]:
    """Combine uploaded words with bundled/rockyou lists for merging."""
    from oswg.core.wordlists import detect_rockyou, iter_builtin, iter_wordlist

    words = list(request.merge_words)
    if request.merge_builtin:
        words.extend(iter_builtin())
    if request.merge_rockyou:
        rockyou = detect_rockyou()
        if rockyou is not None:
            words.extend(iter_wordlist(rockyou))
    return words


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
    generator.scraper.timeout = config_data.get("timeout", 30.0)
    generator.scraper.respect_robots = config_data.get("respect_robots", False)
    generator.scraper.user_agent = config_data.get("user_agent")
    generator.scraper.rate_limit = config_data.get("rate_limit", 0.0)
    generator.scraper.jitter = config_data.get("jitter", False)
    generator.scraper.headers = config_data.get("headers") or None
    generator.scraper.cookies = config_data.get("cookies") or None
    generator.scraper.proxy = config_data.get("proxy")

    await job_manager.update_progress(job_id, 20.0, "Scraping website...")

    generation_config = GenerationConfig(
        target_size=config_data.get("size", 10000),
        min_word_length=config_data.get("min_length", 3),
        max_word_length=config_data.get("max_length", 32),
        enable_leet=config_data.get("enable_leet", True),
        enable_uppercase=config_data.get("enable_uppercase", True),
        enable_reverse_leet=config_data.get("enable_reverse_leet", False),
        enable_numbers=config_data.get("enable_numbers", True),
        enable_special=config_data.get("enable_special", False),
        leet_level=config_data.get("leet_level", 1),
        deduplicate=config_data.get("deduplicate", True),
        filter_stopwords=config_data.get("filter_stopwords", True),
        stopword_threshold=config_data.get("stopword_threshold", 0.5),
        extra_stopwords=config_data.get("extra_stopwords", []),
        common_years=config_data.get("common_years") or default_years(),
        special_chars=config_data.get("special_chars") or ["!", "@", "#", "$"],
        merge_words=config_data.get("merge_words", []),
        merge_max=config_data.get("merge_max", 5000),
        enable_random_combine=config_data.get("enable_random_combine", False),
        random_combine_count=config_data.get("random_combine_count", 1000),
        random_combine_seed=config_data.get("random_combine_seed"),
        ai_enabled=config_data.get("ai_enabled", False),
        ai_provider=config_data.get("ai_provider", "auto"),
        ai_model=config_data.get("ai_model"),
        ai_base_url=config_data.get("ai_base_url"),
        ai_max_words=config_data.get("ai_max_words", 1000),
        ai_words_per_word=config_data.get("ai_words_per_word", 3),
        ai_max_concurrency=config_data.get("ai_max_concurrency", 2),
        ai_timeout=config_data.get("ai_timeout", 30.0),
    )

    if generation_config.ai_enabled:
        from oswg.core.ai import AIError, resolve_ai_config

        try:
            resolved = await resolve_ai_config(
                provider=generation_config.ai_provider,
                model=generation_config.ai_model,
                base_url=generation_config.ai_base_url,
            )
        except AIError as exc:
            await job_manager.update_progress(job_id, 40.0, f"AI provider error: {exc}")
            raise ValueError(str(exc)) from exc
        generation_config.ai_provider = resolved.provider
        generation_config.ai_model = resolved.model
        generation_config.ai_base_url = resolved.base_url
        await job_manager.update_progress(job_id, 42.0, f"AI provider: {resolved.display_name}")

    await job_manager.update_progress(job_id, 40.0, "Generating mutations...")

    result = await generator.generate(
        config_data["url"],
        generation_config,
        urls=config_data.get("urls") or None,
        sitemap=config_data.get("sitemap", False),
    )

    rule_format = config_data.get("rule_format")
    if rule_format:
        from oswg.core.rulegen import generate_rules

        rules = generate_rules(generation_config, format=rule_format)
        await job_manager.update_progress(job_id, 80.0, "Saving rules...")
        file_path = file_manager.save_rules(job_id, rules, result.base_words)
    else:
        await job_manager.update_progress(job_id, 80.0, "Saving wordlist...")
        file_path = file_manager.save_words(job_id, result.words)

    await job_manager.update_progress(job_id, 95.0, "Finalizing...")

    return {
        "file_path": str(file_path),
        "words_count": result.unique_words,
        "source_keywords": result.source_keywords,
        "truncated_count": result.truncated_count,
        "rule_format": rule_format,
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
            "enable_uppercase": request.enable_uppercase,
            "enable_reverse_leet": request.enable_reverse_leet,
            "enable_numbers": request.enable_numbers,
            "enable_special": request.enable_special,
            "leet_level": request.leet_level,
            "deduplicate": request.deduplicate,
            "filter_stopwords": request.filter_stopwords,
            "stopword_threshold": request.stopword_threshold,
            "extra_stopwords": request.extra_stopwords,
            "common_years": request.common_years,
            "special_chars": request.special_chars,
            "timeout": request.timeout,
            "respect_robots": request.respect_robots,
            "user_agent": request.user_agent,
            "rate_limit": request.rate_limit,
            "jitter": request.jitter,
            "headers": request.headers,
            "cookies": request.cookies,
            "proxy": request.proxy,
            "merge_words": _resolve_merge_words(request),
            "merge_max": request.merge_max,
            "enable_random_combine": request.enable_random_combine,
            "random_combine_count": request.random_combine_count,
            "random_combine_seed": request.random_combine_seed,
            "ai_enabled": request.ai_enabled,
            "ai_provider": request.ai_provider,
            "ai_model": request.ai_model,
            "ai_base_url": request.ai_base_url,
            "ai_max_words": request.ai_max_words,
            "ai_words_per_word": request.ai_words_per_word,
            "ai_max_concurrency": request.ai_max_concurrency,
            "ai_timeout": request.ai_timeout,
            "rule_format": request.rule_format,
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

"""Jobs router - job status and download endpoints."""

import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse

from oswg.core.export import (
    FORMATS,
    MEDIA_TYPES,
    build_metadata,
    compress_bytes,
    render_bytes,
)
from oswg.database import db
from oswg.models import ErrorResponse, JobListItem, JobStatusResponse
from oswg.services.file_manager import file_manager
from oswg.services.job_manager import job_manager

router = APIRouter()


@router.post(
    "/jobs/clear",
    status_code=200,
    responses={
        500: {"model": ErrorResponse, "description": "Failed to clear jobs"},
    },
)
async def clear_jobs():
    """Clear all jobs and their files."""
    job_ids = await job_manager.clear_all_jobs()
    for job_id in job_ids:
        file_manager.delete_file(job_id)
    return {"cleared": len(job_ids)}


@router.get(
    "/jobs",
    response_model=list[JobListItem],
)
async def list_jobs():
    """List all non-expired jobs with TTL."""
    jobs = await job_manager.get_active_jobs()
    result = []
    for job in jobs:
        expires_at = datetime.fromisoformat(job["expires_at"])
        ttl = max(0, int((expires_at - datetime.utcnow()).total_seconds()))
        file_size = None
        if job["status"] == "completed" and file_manager.file_exists(job["id"]):
            file_size = file_manager.get_file_size(job["id"])
        url = None
        try:
            url = json.loads(job["config"]).get("url")
        except (ValueError, TypeError):
            pass
        result.append(
            JobListItem(
                job_id=job["id"],
                type=job["type"],
                status=job["status"],
                progress=job["progress"],
                created_at=datetime.fromisoformat(job["created_at"]),
                expires_at=expires_at,
                ttl_seconds=ttl,
                file_size_bytes=file_size,
                url=url,
            )
        )
    return result


@router.get(
    "/jobs/url-history",
    responses={
        500: {"model": ErrorResponse, "description": "Failed to load URL history"},
    },
)
async def get_url_history(q: str = "", limit: int = 10):
    """Return recently used primary URLs for autocomplete."""
    urls = await db.url_history(q=q or None, limit=min(max(limit, 1), 50))
    return {"urls": urls}


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Job not found"},
    },
)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """Get the status of a job."""
    job = await job_manager.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    stats = {}
    if job.get("result_stats"):
        try:
            stats = json.loads(job["result_stats"])
        except (ValueError, TypeError):
            stats = {}

    return JobStatusResponse(
        job_id=job["id"],
        type=job["type"],
        status=job["status"],
        progress=job["progress"],
        created_at=datetime.fromisoformat(job["created_at"]),
        updated_at=datetime.fromisoformat(job["updated_at"]),
        completed_at=(
            datetime.fromisoformat(job["completed_at"])
            if job.get("completed_at")
            else None
        ),
        error_message=job.get("error_message"),
        result_file=job.get("result_file"),
        words_count=stats.get("words_count"),
        source_keywords=stats.get("source_keywords"),
        truncated_count=stats.get("truncated_count"),
        rule_format=stats.get("rule_format"),
        crawl_strategy=stats.get("crawl_strategy"),
        screenshot_count=stats.get("screenshot_count"),
        email_count=stats.get("email_count"),
        username_count=stats.get("username_count"),
    )


@router.get(
    "/jobs/{job_id}/download",
    responses={
        404: {"model": ErrorResponse, "description": "Job or file not found"},
    },
)
async def download_job_result(
    job_id: str,
    target: str = "rules",
    format: str = "txt",
    gzip: bool = False,
):
    """Download a completed job's result file.

    ``target`` selects which file: ``rules`` (default), ``base``, or
    ``wordlist``. ``format`` (txt/json/csv) and ``gzip`` apply to wordlist
    exports; rules/base are line-based text and ignore ``format``.
    """
    job = await job_manager.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} is not completed (status: {job['status']})",
        )

    if target not in ("rules", "base", "wordlist", "usernames"):
        raise HTTPException(status_code=400, detail=f"Unknown target '{target}'")

    if format not in FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown format '{format}' (expected one of: {', '.join(FORMATS)})",
        )

    if target in ("rules", "base", "usernames"):
        extension = {
            "rules": ".rules",
            "base": ".base.txt",
            "usernames": ".usernames.txt",
        }[target]
        if not file_manager.file_exists(job_id, extension):
            raise HTTPException(
                status_code=404,
                detail=f"File ({extension}) for job {job_id} not found",
            )
        data = file_manager.get_file_path(job_id, extension).read_bytes()
        if gzip:
            data = compress_bytes(data)
        filename = f"oswg_{job_id}{extension}" + (".gz" if gzip else "")
        media_type = "application/gzip" if gzip else MEDIA_TYPES["txt"]
        return Response(
            content=data,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    if not file_manager.file_exists(job_id, ".txt"):
        raise HTTPException(
            status_code=404, detail=f"File (.txt) for job {job_id} not found"
        )

    words = (
        file_manager.get_file_path(job_id, ".txt")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    metadata = _job_export_metadata(job)
    extra = None
    if format == "json" and file_manager.file_exists(job_id, ".usernames.txt"):
        extra = {
            "usernames": file_manager.get_file_path(job_id, ".usernames.txt")
            .read_text(encoding="utf-8")
            .splitlines()
        }
    data = render_bytes(words, fmt=format, metadata=metadata, compress=gzip, extra=extra)
    extension = {"txt": ".txt", "json": ".json", "csv": ".csv"}[format]
    filename = f"oswg_{job_id}{extension}" + (".gz" if gzip else "")
    media_type = "application/gzip" if gzip else MEDIA_TYPES[format]
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _job_export_metadata(job: dict) -> dict:
    """Build JSON export metadata from a job row."""
    from oswg import __version__

    config: dict = {}
    if job.get("config"):
        try:
            config = json.loads(job["config"])
        except (ValueError, TypeError):
            config = {}

    stats: dict = {}
    if job.get("result_stats"):
        try:
            stats = json.loads(job["result_stats"])
        except (ValueError, TypeError):
            stats = {}

    source = {}
    if config.get("url"):
        source["url"] = config["url"]
    if config.get("urls"):
        source["urls"] = config["urls"]
    if config.get("sitemap"):
        source["sitemap"] = True
    for key in ("title", "meta_description"):
        if stats.get(key):
            source[key] = stats[key]

    return build_metadata(
        version=__version__,
        created_at=job.get("created_at"),
        completed_at=job.get("completed_at"),
        job_id=job.get("id"),
        job_type=job.get("type"),
        source=source or None,
        stats=stats or None,
        config=config,
    )


@router.get(
    "/jobs/{job_id}/graph",
    responses={
        404: {"model": ErrorResponse, "description": "Job or graph file not found"},
    },
)
async def get_job_graph(job_id: str):
    """Return the crawl graph (nodes + edges) for a completed job."""
    job = await job_manager.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} is not completed (status: {job['status']})",
        )

    graph_path = file_manager.get_file_path(job_id, ".json")
    if not graph_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Crawl graph for job {job_id} not found"
        )

    import json as json_mod

    with open(graph_path, "r", encoding="utf-8") as f:
        data = json_mod.load(f)

    link_graph: dict[str, list[str]] = data.get("link_graph", {})

    stats = {}
    if job.get("result_stats"):
        try:
            stats = json_mod.loads(job["result_stats"])
        except (ValueError, TypeError):
            stats = {}

    # Build nodes (crawled pages) and edges (parent -> child).
    nodes = [{"id": url} for url in link_graph]
    edges = []
    for parent, children in link_graph.items():
        for child in children:
            if child in link_graph:
                edges.append([parent, child])

    return {
        "job_id": job_id,
        "crawl_strategy": stats.get("crawl_strategy"),
        "nodes": nodes,
        "edges": edges,
    }


@router.get(
    "/jobs/{job_id}/word-counts",
    responses={
        404: {"model": ErrorResponse, "description": "Job or word counts not found"},
    },
)
async def get_job_word_counts(job_id: str, limit: int = 200):
    """Return word frequencies for a completed job's keyword cloud."""
    job = await job_manager.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} is not completed (status: {job['status']})",
        )

    counts_path = file_manager.get_file_path(job_id, ".word-counts.json")
    if not counts_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Word counts for job {job_id} not found"
        )

    counts: dict[str, int] = json.loads(counts_path.read_text(encoding="utf-8"))
    words = [
        {"word": word, "count": count}
        for word, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    ]

    return {"job_id": job_id, "total": len(counts), "words": words}


@router.get(
    "/jobs/{job_id}/mutation-tree",
    responses={
        404: {"model": ErrorResponse, "description": "Job or mutation tree not found"},
    },
)
async def get_job_mutation_tree(job_id: str, limit: int = 200):
    """Return a generate job's mutation tree (base word -> surviving variants)."""
    job = await job_manager.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} is not completed (status: {job['status']})",
        )

    tree_path = file_manager.get_file_path(job_id, ".mutation-tree.json")
    if not tree_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Mutation tree for job {job_id} not found"
        )

    tree: dict[str, list[str]] = json.loads(tree_path.read_text(encoding="utf-8"))
    ordered = sorted(tree.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:limit]

    return {"job_id": job_id, "tree": dict(ordered)}


@router.get(
    "/jobs/{job_id}/screenshot",
    responses={
        404: {"model": ErrorResponse, "description": "Job or screenshot not found"},
    },
)
async def get_job_screenshot(job_id: str, page: int = 0):
    """Return a rendered-page screenshot (PNG) for a job."""
    job = await job_manager.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} is not completed (status: {job['status']})",
        )

    path = file_manager.get_screenshot_path(job_id, page)
    if path is None:
        raise HTTPException(
            status_code=404, detail=f"Screenshot {page} for job {job_id} not found"
        )

    return FileResponse(path=path, media_type="image/png")


@router.get(
    "/jobs/{job_id}/preview",
    responses={
        404: {"model": ErrorResponse, "description": "Job or file not found"},
    },
)
async def preview_job_result(job_id: str, limit: int = 100):
    """Preview the first N words/rules of a completed job's result."""
    job = await job_manager.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} is not completed (status: {job['status']})",
        )

    stats = {}
    if job.get("result_stats"):
        try:
            stats = json.loads(job["result_stats"])
        except (ValueError, TypeError):
            stats = {}

    if job["type"] == "test":
        result_path = file_manager.get_file_path(job_id, ".test.json")
        if not result_path.exists():
            raise HTTPException(
                status_code=404, detail=f"Test result for job {job_id} not found"
            )
        result = json.loads(result_path.read_text(encoding="utf-8"))
        return {
            "job_id": job_id,
            "mode": "test",
            "tool": result.get("tool"),
            "kind": result.get("kind"),
            "found": result.get("found", 0),
            "entries": result.get("entries", []),
        }

    rule_format = stats.get("rule_format")

    if rule_format:
        rules_path = file_manager.get_file_path(job_id, ".rules")
        base_path = file_manager.get_file_path(job_id, ".base.txt")
        if not rules_path.exists() or not base_path.exists():
            raise HTTPException(
                status_code=404, detail=f"Rule files for job {job_id} not found"
            )

        with open(rules_path, "r", encoding="utf-8") as f:
            rule_lines = [line.strip() for line in f if line.strip()]
        with open(base_path, "r", encoding="utf-8") as f:
            base_words = [line.strip() for line in f if line.strip()]

        return {
            "job_id": job_id,
            "mode": "rules",
            "format": rule_format,
            "rules": rule_lines[:limit],
            "rules_total": len(rule_lines),
            "rules_truncated": len(rule_lines) > limit,
            "base_words": base_words[:limit],
            "base_total": len(base_words),
            "base_truncated": len(base_words) > limit,
            "rules_path": str(rules_path),
            "base_path": str(base_path),
        }

    if not file_manager.file_exists(job_id):
        raise HTTPException(
            status_code=404, detail=f"Result file for job {job_id} not found"
        )

    file_path = file_manager.get_file_path(job_id)
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    total = len(lines)
    preview = [line.strip() for line in lines[:limit] if line.strip()]

    usernames: list[str] = []
    if file_manager.file_exists(job_id, ".usernames.txt"):
        with open(
            file_manager.get_file_path(job_id, ".usernames.txt"),
            "r",
            encoding="utf-8",
        ) as f:
            usernames = [line.strip() for line in f if line.strip()]

    return {
        "job_id": job_id,
        "mode": "wordlist",
        "total_words": total,
        "preview": preview,
        "truncated": total > limit,
        "usernames": usernames,
        "usernames_total": len(usernames),
    }

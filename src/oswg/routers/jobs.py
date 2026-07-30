"""Jobs router - job status and download endpoints."""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

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
    jobs = await job_manager.get_active_jobs()
    for job in jobs:
        file_manager.delete_file(job["id"])
        await job_manager.delete_job(job["id"])
    return {"cleared": len(jobs)}


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
            )
        )
    return result


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
    )


@router.get(
    "/jobs/{job_id}/download",
    responses={
        404: {"model": ErrorResponse, "description": "Job or file not found"},
    },
)
async def download_job_result(job_id: str) -> FileResponse:
    """Download the result file for a completed job."""
    job = await job_manager.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} is not completed (status: {job['status']})",
        )

    if not file_manager.file_exists(job_id):
        raise HTTPException(
            status_code=404, detail=f"Result file for job {job_id} not found"
        )

    file_path = file_manager.get_file_path(job_id)

    return FileResponse(
        path=file_path,
        filename=f"oswg_{job_id}.txt",
        media_type="text/plain",
    )


@router.get(
    "/jobs/{job_id}/preview",
    responses={
        404: {"model": ErrorResponse, "description": "Job or file not found"},
    },
)
async def preview_job_result(job_id: str, limit: int = 100):
    """Preview the first N words of a completed job's wordlist."""
    job = await job_manager.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} is not completed (status: {job['status']})",
        )

    if not file_manager.file_exists(job_id):
        raise HTTPException(
            status_code=404, detail=f"Result file for job {job_id} not found"
        )

    file_path = file_manager.get_file_path(job_id)
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    total = len(lines)
    preview = [line.strip() for line in lines[:limit] if line.strip()]

    return {
        "job_id": job_id,
        "total_words": total,
        "preview": preview,
        "truncated": total > limit,
    }

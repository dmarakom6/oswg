"""Job manager service - handles background job execution."""

import uuid
from typing import Callable, Optional

from oswg.config import settings
from oswg.database import db
from oswg.models import JobStatus, JobType
from oswg.services.progress import progress_tracker


class JobManager:
    """Manages background job execution and tracking."""

    async def create_job(
        self,
        job_type: JobType,
        config: dict,
        executor: Callable,
        retention_seconds: Optional[int] = None,
    ) -> str:
        """Create a new job and return job_id."""
        job_id = str(uuid.uuid4())
        retention = retention_seconds or settings.default_retention_seconds

        await db.create_job(
            job_id=job_id,
            job_type=job_type,
            config=config,
            retention_seconds=retention,
        )

        return job_id

    async def execute_job(
        self,
        job_id: str,
        executor: Callable,
    ) -> None:
        """Execute a job in the background."""
        try:
            await db.update_job_status(
                job_id=job_id,
                status=JobStatus.PROCESSING,
                progress=0.0,
            )

            await progress_tracker.register_job(job_id)

            result = await executor(job_id)

            await db.update_job_status(
                job_id=job_id,
                status=JobStatus.COMPLETED,
                progress=100.0,
                result_file=result.get("file_path"),
            )

            await progress_tracker.complete_job(job_id)

        except Exception as e:
            await db.update_job_status(
                job_id=job_id,
                status=JobStatus.FAILED,
                progress=0.0,
                error_message=str(e),
            )
            await progress_tracker.fail_job(job_id, str(e))

    async def update_progress(
        self,
        job_id: str,
        progress: float,
        message: Optional[str] = None,
    ) -> None:
        """Update job progress and notify WebSocket clients."""
        await db.update_job_status(
            job_id=job_id,
            status=JobStatus.PROCESSING,
            progress=progress,
        )

        await progress_tracker.update_progress(job_id, progress, message)

    async def get_job_status(self, job_id: str) -> Optional[dict]:
        """Get job status."""
        return await db.get_job(job_id)

    async def get_active_jobs(self) -> list[dict]:
        """Get all non-expired jobs."""
        return await db.get_active_jobs()

    async def delete_job(self, job_id: str) -> None:
        """Delete a job from the database."""
        await db.delete_job(job_id)

    async def cleanup_expired(self) -> list[str]:
        """Clean up expired jobs and files."""
        expired_ids = await db.cleanup_expired_jobs()
        return expired_ids


job_manager = JobManager()

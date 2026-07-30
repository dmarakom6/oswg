"""SQLite database layer for OSWG API."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import aiosqlite

from oswg.config import settings
from oswg.models import JobStatus, JobType


class Database:
    """SQLite database manager."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.database_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def init(self) -> None:
        """Initialize database schema."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,
                    config TEXT,
                    result_file TEXT,
                    error_message TEXT,
                    retention_seconds INTEGER NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """
            )
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_jobs_expires_at
                ON jobs(expires_at)
                """
            )
            await db.commit()

    async def create_job(
        self,
        job_id: str,
        job_type: JobType,
        config: dict,
        retention_seconds: int,
    ) -> None:
        """Create a new job."""
        now = datetime.utcnow().isoformat()
        expires_at = (
            datetime.utcnow() + timedelta(seconds=retention_seconds)
        ).isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO jobs
                (id, type, status, progress, created_at, updated_at,
                 config, retention_seconds, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    job_type.value,
                    JobStatus.PENDING.value,
                    0.0,
                    now,
                    now,
                    json.dumps(config),
                    retention_seconds,
                    expires_at,
                ),
            )
            await db.commit()

    async def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        progress: float,
        error_message: Optional[str] = None,
        result_file: Optional[str] = None,
    ) -> None:
        """Update job status and progress."""
        now = datetime.utcnow().isoformat()
        completed_at = (
            now if status in (JobStatus.COMPLETED, JobStatus.FAILED) else None
        )

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE jobs
                SET status = ?, progress = ?, updated_at = ?,
                    completed_at = COALESCE(?, completed_at),
                    error_message = COALESCE(?, error_message),
                    result_file = COALESCE(?, result_file)
                WHERE id = ?
                """,
                (
                    status.value,
                    progress,
                    now,
                    completed_at,
                    error_message,
                    result_file,
                    job_id,
                ),
            )
            await db.commit()

    async def get_job(self, job_id: str) -> Optional[dict]:
        """Get a job by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM jobs WHERE id = ?", (job_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None

    async def get_expired_jobs(self) -> list[dict]:
        """Get all expired jobs."""
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM jobs WHERE expires_at < ?", (now,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_active_jobs(self) -> list[dict]:
        """Get all non-expired jobs."""
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM jobs WHERE expires_at >= ? ORDER BY created_at DESC",
                (now,),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def delete_job(self, job_id: str) -> None:
        """Delete a job."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            await db.commit()

    async def cleanup_expired_jobs(self) -> list[str]:
        """Delete expired jobs and return their IDs."""
        expired = await self.get_expired_jobs()
        job_ids = [job["id"] for job in expired]

        if job_ids:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "DELETE FROM jobs WHERE expires_at < ?",
                    (datetime.utcnow().isoformat(),),
                )
                await db.commit()

        return job_ids


db = Database()

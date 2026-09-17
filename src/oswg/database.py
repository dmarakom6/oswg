"""SQLite database layer for OSWG API."""

import asyncio
import json
import time
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
        self._url_history_cache: Optional[tuple[float, list[dict]]] = None
        self._url_history_ttl = 30.0
        self._url_history_loading = False

    async def init(self) -> None:
        """Initialize database schema."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA busy_timeout=5000")
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
                    result_stats TEXT,
                    error_message TEXT,
                    retention_seconds INTEGER NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """
            )
            try:
                await db.execute("ALTER TABLE jobs ADD COLUMN result_stats TEXT")
            except Exception:
                pass
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
        url = (config or {}).get("url")
        if url and self._url_history_cache is not None:
            _, urls = self._url_history_cache
            found = next((u for u in urls if u["url"] == url), None)
            if found:
                found["count"] += 1
            else:
                urls.append({"url": url, "count": 1})

    async def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        progress: float,
        error_message: Optional[str] = None,
        result_file: Optional[str] = None,
        result_stats: Optional[str] = None,
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
                    result_file = COALESCE(?, result_file),
                    result_stats = COALESCE(?, result_stats)
                WHERE id = ?
                """,
                (
                    status.value,
                    progress,
                    now,
                    completed_at,
                    error_message,
                    result_file,
                    result_stats,
                    job_id,
                ),
            )
            await db.commit()

    async def ping(self) -> float:
        """Check database connectivity; returns latency in milliseconds.

        Raises on failure.
        """
        start = time.perf_counter()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("SELECT 1")
        return (time.perf_counter() - start) * 1000

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

    async def url_history(self, q: Optional[str] = None, limit: int = 10) -> list[dict]:
        """Return distinct primary URLs from jobs, by usage count then recency.

        The full list is cached; new jobs update it incrementally and a
        stale cache is refreshed in the background, so reads are fast.
        """
        now = time.monotonic()
        if self._url_history_cache is None:
            self._url_history_cache = (now, await self._load_url_history())
        elif (
            now - self._url_history_cache[0] > self._url_history_ttl
            and not self._url_history_loading
        ):
            self._url_history_loading = True
            asyncio.create_task(self._refresh_url_history())

        urls = self._url_history_cache[1]
        if q:
            needle = q.lower()
            urls = [u for u in urls if needle in u["url"].lower()]
        return urls[:limit]

    async def _refresh_url_history(self) -> None:
        try:
            self._url_history_cache = (time.monotonic(), await self._load_url_history())
        finally:
            self._url_history_loading = False

    async def _load_url_history(self) -> list[dict]:
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT json_extract(config, '$.url') AS url, COUNT(*) AS cnt
                FROM jobs
                WHERE json_extract(config, '$.url') IS NOT NULL
                  AND expires_at > ?
                GROUP BY url
                ORDER BY cnt DESC, MAX(created_at) DESC
                """,
                (now,),
            ) as cursor:
                rows = await cursor.fetchall()
        return [{"url": row["url"], "count": row["cnt"]} for row in rows]

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
        self._url_history_cache = None

    async def clear_all_jobs(self) -> list[str]:
        """Delete every job row, returning the deleted ids."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT id FROM jobs") as cursor:
                rows = await cursor.fetchall()
            await db.execute("DELETE FROM jobs")
            await db.commit()
        self._url_history_cache = None
        return [row["id"] for row in rows]

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
            self._url_history_cache = None

        return job_ids


db = Database()

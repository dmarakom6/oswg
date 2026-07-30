"""Progress tracking service - manages WebSocket connections and progress updates."""

import asyncio
from datetime import datetime
from typing import Optional

from fastapi import WebSocket


class ProgressTracker:
    """Tracks job progress and manages WebSocket connections."""

    def __init__(self):
        self.connections: dict[str, list[WebSocket]] = {}
        self.job_progress: dict[str, dict] = {}
        self.lock = asyncio.Lock()

    async def connect(self, job_id: str, websocket: WebSocket) -> None:
        """Register a WebSocket connection for a job."""
        async with self.lock:
            if job_id not in self.connections:
                self.connections[job_id] = []
            self.connections[job_id].append(websocket)

    async def disconnect(self, job_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        async with self.lock:
            if job_id in self.connections:
                self.connections[job_id] = [
                    ws for ws in self.connections[job_id] if ws != websocket
                ]
                if not self.connections[job_id]:
                    del self.connections[job_id]

    async def register_job(self, job_id: str) -> None:
        """Register a new job for tracking."""
        self.job_progress[job_id] = {
            "status": "processing",
            "progress": 0.0,
            "message": None,
            "updated_at": datetime.utcnow().isoformat(),
            "last_broadcast_progress": 0.0,
        }

    async def update_progress(
        self,
        job_id: str,
        progress: float,
        message: Optional[str] = None,
    ) -> None:
        """Update job progress and broadcast to WebSocket clients."""
        if job_id in self.job_progress:
            self.job_progress[job_id]["progress"] = progress
            self.job_progress[job_id]["message"] = message
            self.job_progress[job_id]["updated_at"] = datetime.utcnow().isoformat()

            last_broadcast = self.job_progress[job_id].get(
                "last_broadcast_progress", 0.0
            )
            if progress - last_broadcast >= 5.0 or progress >= 100.0:
                self.job_progress[job_id]["last_broadcast_progress"] = progress
                await self.broadcast(
                    job_id,
                    {
                        "job_id": job_id,
                        "status": "processing",
                        "progress": progress,
                        "message": message,
                    },
                )

    async def complete_job(self, job_id: str) -> None:
        """Mark job as completed and notify WebSocket clients."""
        if job_id in self.job_progress:
            self.job_progress[job_id] = {
                "status": "completed",
                "progress": 100.0,
                "message": "Job completed successfully",
                "updated_at": datetime.utcnow().isoformat(),
            }

        await self.broadcast(
            job_id,
            {
                "job_id": job_id,
                "status": "completed",
                "progress": 100.0,
                "message": "Job completed successfully",
            },
        )

    async def fail_job(self, job_id: str, error: str) -> None:
        """Mark job as failed and notify WebSocket clients."""
        if job_id in self.job_progress:
            self.job_progress[job_id] = {
                "status": "failed",
                "progress": 0.0,
                "message": error,
                "updated_at": datetime.utcnow().isoformat(),
            }

        await self.broadcast(
            job_id,
            {
                "job_id": job_id,
                "status": "failed",
                "progress": 0.0,
                "message": error,
            },
        )

    def get_progress(self, job_id: str) -> Optional[dict]:
        """Get current progress for a job."""
        return self.job_progress.get(job_id)

    async def broadcast(self, job_id: str, message: dict) -> None:
        """Send message to all WebSocket clients for a job."""
        async with self.lock:
            if job_id in self.connections:
                disconnected = []
                for ws in self.connections[job_id]:
                    try:
                        await ws.send_json(message)
                    except Exception:
                        disconnected.append(ws)

                for ws in disconnected:
                    await self.disconnect(job_id, ws)

    def cleanup_job(self, job_id: str) -> None:
        """Remove job from tracking."""
        self.job_progress.pop(job_id, None)
        self.connections.pop(job_id, None)


progress_tracker = ProgressTracker()

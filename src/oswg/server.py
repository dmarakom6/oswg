"""OSWG API - FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from oswg.config import settings
from oswg.database import db
from oswg.routers import generate, jobs, mutate, scrape
from oswg.services.progress import progress_tracker


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    await db.init()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API for generating targeted wordlists from website content",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generate.router, prefix=settings.api_prefix, tags=["generate"])
app.include_router(scrape.router, prefix=settings.api_prefix, tags=["scrape"])
app.include_router(mutate.router, prefix=settings.api_prefix, tags=["mutate"])
app.include_router(jobs.router, prefix=settings.api_prefix, tags=["jobs"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.websocket("/ws/jobs/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time job progress updates."""
    await websocket.accept()
    await progress_tracker.connect(job_id, websocket)

    try:
        progress = progress_tracker.get_progress(job_id)
        if progress:
            await websocket.send_json(
                {
                    "job_id": job_id,
                    "status": progress["status"],
                    "progress": progress["progress"],
                    "message": progress.get("message"),
                }
            )

        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        await progress_tracker.disconnect(job_id, websocket)
    except Exception:
        await progress_tracker.disconnect(job_id, websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "oswg_api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )

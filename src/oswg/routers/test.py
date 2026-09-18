"""Test router - wordlist testing endpoint."""

import asyncio
import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException

from oswg.core import test_runner
from oswg.core.test_runner import TestToolError
from oswg.models import (
    ErrorResponse,
    JobResponse,
    JobStatus,
    JobType,
    TestRequest,
)
from oswg.services.file_manager import file_manager
from oswg.services.job_manager import job_manager

router = APIRouter()


def _write_if_set(tmp: Path, config: dict, key: str, name: str) -> None:
    if config.get(key):
        (tmp / f"{name}.txt").write_text(config[key])


async def execute_test(job_id: str) -> dict:
    """Run an external cracking tool against a wordlist."""
    job = await job_manager.get_job_status(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")
    config = json.loads(job["config"])
    tool = config["tool"]

    await job_manager.update_progress(job_id, 15, "Preparing inputs...")

    with tempfile.TemporaryDirectory(prefix="oswg-test-") as td:
        tmp = Path(td)
        inputs: dict = {}

        wordlist_job_id = config.get("wordlist_job_id")
        if wordlist_job_id:
            base = file_manager.get_file_path(wordlist_job_id)
            if not base.exists():
                raise ValueError(f"Referenced job {wordlist_job_id} has no wordlist file")
            inputs["wordlist"] = base
        else:
            wordlist = tmp / "wordlist.txt"
            wordlist.write_text(config.get("wordlist_text") or "")
            inputs["wordlist"] = wordlist

        if config.get("mode") is not None:
            inputs["mode"] = config["mode"]
        for key, name in (
            ("hashes_text", "hashes"),
            ("users_text", "users"),
            ("rules_text", "rules"),
            ("capture_text", "capture"),
        ):
            _write_if_set(tmp, config, key, name)
            if config.get(key):
                inputs[name] = tmp / f"{name}.txt"
        for key in ("host", "service", "url"):
            if config.get(key):
                inputs[key] = config[key]

        await job_manager.update_progress(job_id, 30, f"Running {tool}...")
        try:
            result = await asyncio.to_thread(test_runner.run, tool, inputs)
        except TestToolError as e:
            raise ValueError(str(e)) from e

        file_manager.save_test_result(job_id, result)

    await job_manager.update_progress(job_id, 100, f"{tool} finished")
    return {"tool": tool, "kind": result["kind"], "found": result["found"]}


@router.post(
    "/test",
    response_model=JobResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def test_wordlist(
    request: TestRequest,
    background_tasks: BackgroundTasks,
) -> JobResponse:
    """Test a wordlist against a target with an external tool."""
    try:
        if not test_runner.available().get(request.tool):
            raise HTTPException(
                status_code=400,
                detail=f"Tool '{request.tool}' is not installed. Run 'oswg setup' to see how to install it.",
            )
        config = {
            "tool": request.tool,
            "wordlist_job_id": request.wordlist_job_id,
            "wordlist_text": request.wordlist_text,
            "mode": request.mode,
            "hashes_text": request.hashes_text,
            "users_text": request.users_text,
            "rules_text": request.rules_text,
            "host": request.host,
            "service": request.service,
            "url": request.url,
            "capture_text": request.capture_text,
        }

        job_id = await job_manager.create_job(
            job_type=JobType.TEST,
            config=config,
            executor=execute_test,
            retention_seconds=request.retention_seconds,
        )

        background_tasks.add_task(job_manager.execute_job, job_id, execute_test)

        return JobResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            message="Test started",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

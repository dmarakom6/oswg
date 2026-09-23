"""End-to-end test of the CLI job-id -> template-save round trip."""

import os
import re
import subprocess
import sys

import pytest

pytestmark = pytest.mark.e2e

UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def _run_cli(data_dir, *args):
    env = {**os.environ, "OSWG_DATA_DIR": str(data_dir)}
    return subprocess.run(
        [sys.executable, "-m", "oswg.cli", *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_cli_generate_to_template_roundtrip(site_url, tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    out = tmp_path / "words.txt"

    gen = _run_cli(data_dir, "generate", site_url, "-o", str(out), "--preset", "quick")
    assert gen.returncode == 0, gen.stderr

    job_id = UUID_RE.search(gen.stdout)
    assert job_id, f"no Job ID in output:\n{gen.stdout}"

    jobs = _run_cli(data_dir, "jobs")
    assert job_id.group(0) in jobs.stdout

    save = _run_cli(data_dir, "template", "save", "cli-tpl", "--type", "generate", "--from-job", job_id.group(0))
    assert save.returncode == 0, save.stderr
    assert "Saved template 'cli-tpl'" in save.stdout

    templates = _run_cli(data_dir, "template", "list")
    assert "cli-tpl" in templates.stdout

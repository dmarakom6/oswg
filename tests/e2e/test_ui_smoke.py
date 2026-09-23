"""Playwright E2E smoke tests for the OSWG UI."""

import time

import pytest

try:
    from playwright.sync_api import expect
except ImportError:  # pragma: no cover - depends on the `js` extra
    expect = None

pytestmark = pytest.mark.e2e


def _expand_templates(page):
    summary = page.locator("summary", has_text="Templates & Presets").first
    if not page.locator("#template-preset").first.is_visible():
        summary.click()
    page.locator("#template-preset").first.wait_for(state="visible", timeout=10000)


def _wordlist_size(page) -> str:
    row = page.get_by_text("Wordlist size").first
    return row.locator("xpath=ancestor::div[1]//input").input_value()


def test_preset_applies_shows_selection_and_disables_template(app_url, page):
    page.goto(app_url, wait_until="networkidle")
    _expand_templates(page)

    page.locator("#template-preset").first.select_option("quick")
    page.wait_for_timeout(300)

    expect(page.locator("#template-preset").first).to_have_value("quick")
    assert _wordlist_size(page) == "1000"
    expect(page.locator("#template-select").first).to_be_disabled()

    # None re-enables the template dropdown
    page.locator("#template-preset").first.select_option("")
    page.wait_for_timeout(200)
    expect(page.locator("#template-select").first).to_be_enabled()


def test_save_template_from_completed_job(app_url, site_url, page):
    page.goto(app_url, wait_until="networkidle")
    page.locator("input[placeholder*='example.com']").first.fill(site_url)
    _expand_templates(page)
    page.locator("#template-preset").first.select_option("quick")
    page.get_by_role("button", name="Generate Wordlist").first.click()

    deadline = time.time() + 60
    done = False
    while time.time() < deadline:
        time.sleep(1)
        data = page.request.get(f"{app_url}/api/v1/jobs").json()
        jobs = data if isinstance(data, list) else data.get("jobs", [])
        if any(j.get("status") == "completed" for j in jobs):
            done = True
            break
    assert done, "generate job did not complete"
    page.wait_for_timeout(800)

    # Job ID shown in the right pane
    latest = (data if isinstance(data, list) else data.get("jobs", []))[0]
    job_id = latest.get("job_id", "")
    assert job_id and page.get_by_text(job_id, exact=True).count() > 0

    # Save via the modal (button next to Visualize)
    viz = page.get_by_role("button", name="Visualize", exact=True).last
    viz.locator("xpath=preceding-sibling::button[1]").click()
    modal = page.locator("[aria-label='Save template']")
    expect(modal).to_be_visible()
    modal.locator("input").fill("e2e-job-template")
    modal.get_by_role("button", name="Save", exact=True).click()
    page.wait_for_timeout(800)

    # Template appears in the Generate tab dropdown
    _expand_templates(page)
    opts = page.locator("#template-select").first.locator("option").all_inner_texts()
    assert any("e2e-job-template" in o for o in opts)


def test_clear_all_templates(app_url, page):
    import json as _json

    page.goto(app_url, wait_until="networkidle")

    def _seed(name, type_, config):
        page.request.post(
            f"{app_url}/api/v1/templates",
            data=_json.dumps({"name": name, "type": type_, "config": config}),
            headers={"content-type": "application/json"},
        )

    _seed("seed-one", "generate", {"url": "https://example.com", "size": 100, "max_pages": 1})
    _seed("seed-two", "scrape", {"url": "https://example.com", "max_pages": 1})

    page.reload(wait_until="networkidle")  # refetch so the block sees the seeds
    _expand_templates(page)
    opts = page.locator("#template-select").first.locator("option").all_inner_texts()
    assert any("seed-one" in o for o in opts)
    assert any("seed-two" in o for o in opts)

    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Clear all").first.click()
    page.wait_for_timeout(600)

    templates = page.request.get(f"{app_url}/api/v1/templates").json().get("templates", [])
    assert templates == []
    assert page.locator("#template-select").first.locator("option").all_inner_texts() == ["None"]

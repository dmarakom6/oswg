"""Interactive login and Playwright storage-state sessions."""

from __future__ import annotations

import asyncio
import json
import stat
from pathlib import Path

from oswg.core.cookie_file import Cookie

ROBOTS_USER_AGENT = "oswg"


async def interactive_login(
    url: str,
    *,
    timeout: float = 300.0,
    user_agent: str | None = None,
    proxy: str | None = None,
    headers: dict[str, str] | None = None,
    on_prompt=None,
) -> dict:
    """Open a headed browser, let the user log in, and capture the session.

    Returns a Playwright storage_state dict (cookies + localStorage).
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError as e:
        raise RuntimeError(
            "Interactive login requires Playwright. Run 'oswg setup' to install it (Playwright + Chromium)."
        ) from e

    if on_prompt:
        on_prompt(
            "A browser window has opened. Log in, then press Enter here to capture the session."
        )

    proxy_settings = {"server": proxy} if proxy else None
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            proxy=proxy_settings,
        )
        context = await browser.new_context(
            user_agent=user_agent or ROBOTS_USER_AGENT,
            ignore_https_errors=True,
            extra_http_headers=headers or None,
        )
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
        except Exception:
            pass

        await asyncio.to_thread(input, "")
        state = await context.storage_state()
        await browser.close()

    return state


def save_session(state: dict, path: Path) -> Path:
    """Write a storage_state dict to disk with owner-only permissions."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    return path


def load_session(path: Path) -> dict:
    """Read a storage_state dict from disk."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def parse_session_text(text: str | None) -> dict | None:
    """Parse pasted storage_state JSON text, or None when empty/invalid."""
    if not text or not text.strip():
        return None
    try:
        state = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid storage_state JSON: {e}") from e
    if not isinstance(state, dict):
        raise ValueError("storage_state JSON must be an object")
    return state


def cookies_from_session(state: dict | None) -> list[Cookie]:
    """Extract Cookie objects (for the httpx path) from a storage_state dict."""
    if not state:
        return []
    cookies: list[Cookie] = []
    for raw in state.get("cookies") or []:
        name = raw.get("name")
        value = raw.get("value")
        if not name:
            continue
        expires = raw.get("expires")
        if not isinstance(expires, (int, float)) or expires < 0:
            expires = 0
        cookies.append(
            Cookie(
                domain=raw.get("domain", ""),
                path=raw.get("path") or "/",
                secure=bool(raw.get("secure", False)),
                expires=int(expires),
                name=name,
                value=str(value if value is not None else ""),
            )
        )
    return cookies

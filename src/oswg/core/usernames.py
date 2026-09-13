"""Username extraction from a scraped page."""

import re
from urllib.parse import unquote

from bs4 import BeautifulSoup

from oswg.core.emails import extract_emails

_PROFILE_PATH_RE = re.compile(
    r"^/(?:users?|profile|author|members?|team)/([^/]+?)(?:/|$)"
)
_AT_PATH_RE = re.compile(r"^/@([^/]+?)(?:/|$)")

_AUTHOR_META_NAMES = ("author",)
_AUTHOR_META_PROPERTIES = ("og:author", "article:author", "author")

# Structural path segments that are not usernames (from profile URLs).
_DENYLIST = {
    "profile",
    "profiles",
    "user",
    "users",
    "author",
    "authors",
    "member",
    "members",
    "team",
    "login",
    "register",
    "signup",
    "account",
    "index",
    "home",
    "edit",
    "new",
    "search",
    "browse",
}

_USERNAME_CHARS = re.compile(r"^[a-z0-9._-]+$")


def _clean(value: str) -> str | None:
    """Normalize a candidate username, or None if it should be rejected."""
    cleaned = unquote(value).lower()
    # Drop any query string or fragment.
    for sep in ("?", "#"):
        if sep in cleaned:
            cleaned = cleaned.split(sep, 1)[0]
    cleaned = cleaned.strip().strip(".,;:!?")
    if not cleaned:
        return None
    if "@" in cleaned:  # keep usernames out of full emails
        cleaned = cleaned.split("@")[0]
    if not cleaned:
        return None
    if not (2 <= len(cleaned) <= 32):
        return None
    if not _USERNAME_CHARS.match(cleaned):
        return None
    if cleaned in _DENYLIST:
        return None
    return cleaned


def _from_email_local_parts(raw_html: str) -> list[str]:
    """Usernames derived from the local part of email addresses."""
    result = []
    for email in extract_emails(raw_html):
        local = email.split("@")[0]
        clean = _clean(local)
        if clean and clean not in result:
            result.append(clean)
    return result


def _from_author_metadata(soup: BeautifulSoup) -> list[str]:
    """Usernames from author/creator metadata (FAB-style)."""
    result = []
    for meta in soup.find_all("meta"):
        attrs = {k.lower(): (v or "").strip() for k, v in meta.attrs.items()}
        name = attrs.get("name") or attrs.get("property")
        if name in _AUTHOR_META_NAMES or name in _AUTHOR_META_PROPERTIES:
            content = attrs.get("content")
            if content:
                # og:author/article:author often carry a profile URL.
                for candidate in _split_author_value(content):
                    clean = _clean(candidate)
                    if clean and clean not in result:
                        result.append(clean)
    for a_tag in soup.find_all("a", attrs={"rel": "author"}):
        text = a_tag.get_text(strip=True)
        if text:
            for candidate in _split_author_value(text):
                clean = _clean(candidate)
                if clean and clean not in result:
                    result.append(clean)
    return result


def _split_author_value(content: str) -> list[str]:
    """Extract candidate username values from an author meta value.

    Whitespace/comma-separated tokens are treated individually so a
    display name like "Jane Doe" yields both "jane" and "doe".
    """
    parts: list[str] = []
    for candidate in re.split(r"[\s,;]+", content):
        candidate = candidate.strip()
        if not candidate:
            continue
        if candidate.startswith(("http://", "https://", "www.")):
            path = re.sub(r"^https?://[^/]+/", "", candidate).split("?")[0].rstrip("/")
            if path:
                parts.append(path.rsplit("/", 1)[-1])
                continue
        parts.append(candidate)
    return parts


def _from_profile_paths(links: list[str]) -> list[str]:
    """Usernames from profile-style same-domain URL paths."""
    result = []
    for url in links:
        from urllib.parse import urlparse

        path = urlparse(url).path
        match = _PROFILE_PATH_RE.match(path) or _AT_PATH_RE.match(path)
        if match:
            clean = _clean(match.group(1))
            if clean and clean not in result:
                result.append(clean)
    return result


def extract_usernames(
    raw_html: str, soup: BeautifulSoup, links: list[str]
) -> list[str]:
    """Extract de-duplicated usernames from a page.

    Sources: email local parts, author/creator metadata, and profile-style
    URL path segments. Preserves first-seen order.
    """
    result = []
    for candidate in (
        _from_email_local_parts(raw_html)
        + _from_author_metadata(soup)
        + _from_profile_paths(links)
    ):
        if candidate not in result:
            result.append(candidate)
    return result

"""Email address extraction from raw HTML."""

import html
import re

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def extract_emails(html_text: str) -> list[str]:
    """Extract unique email addresses from raw HTML.

    Runs a regex sweep over the source (catches emails in scripts,
    comments, and attributes) plus a pass over ``mailto:`` hrefs.
    Addresses are lowercased and de-duplicated, preserving first-seen order.
    """
    seen: dict[str, None] = {}
    if html_text:
        for email in EMAIL_RE.findall(html_text):
            seen.setdefault(email.lower(), None)
    for m in re.finditer(r"href\s*=\s*[\"']mailto:([^\"'?]+)", html_text or ""):
        raw = html.unescape(m.group(1)).strip()
        if raw:
            seen.setdefault(raw.lower(), None)
    return list(seen)

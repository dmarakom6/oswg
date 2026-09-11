"""Netscape cookies.txt parsing for authenticated scraping."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Cookie:
    """A single cookie from a Netscape cookies.txt export."""

    domain: str
    path: str
    secure: bool
    expires: int
    name: str
    value: str


def parse_cookie_file(text: str) -> list[Cookie]:
    """Parse Netscape cookies.txt format into Cookie objects.

    Each non-comment line is tab-separated:
    ``domain  includeSubdomains  path  secure  expiry  name  value``
    """
    cookies: list[Cookie] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        fields = line.split("\t")
        if len(fields) < 7:
            fields = line.split()
        if len(fields) < 7:
            continue

        domain, _include_subdomains, path, secure, expiry, name, value = fields[:7]
        try:
            expires = int(expiry)
        except ValueError:
            expires = 0
        cookies.append(
            Cookie(
                domain=domain,
                path=path or "/",
                secure=secure.upper() == "TRUE",
                expires=expires,
                name=name,
                value=value,
            )
        )
    return cookies

"""HTTP authentication (Basic/Digest/NTLM) for the scraper."""

from __future__ import annotations

import httpx

AUTH_TYPES = ("basic", "digest", "ntlm")


class AuthError(ValueError):
    """Raised when HTTP auth configuration is invalid or unavailable."""


def build_auth(
    auth_type: str | None,
    auth_user: str | None,
    auth_pass: str | None,
) -> httpx.Auth | tuple[str, str] | None:
    """Build an httpx auth object for the given type, or None.

    ``basic`` and ``digest`` are handled by httpx itself. ``ntlm`` uses
    the optional ``httpx-ntlm`` package (extra: ``oswg[auth]``).
    """
    if not auth_type:
        return None
    if auth_type not in AUTH_TYPES:
        raise AuthError(
            f"Unknown auth type '{auth_type}' (expected one of: {', '.join(AUTH_TYPES)})"
        )
    if not auth_user or auth_pass is None:
        raise AuthError(
            f"auth type '{auth_type}' requires both --auth-user and --auth-pass"
        )

    if auth_type == "basic":
        return httpx.BasicAuth(auth_user, auth_pass)
    if auth_type == "digest":
        return httpx.DigestAuth(auth_user, auth_pass)

    # NTLM requires the optional httpx-ntlm package.
    try:
        from httpx_ntlm import HttpNtlmAuth
    except ImportError as e:
        raise AuthError(
            "NTLM authentication requires the optional dependency. "
            "Run 'oswg setup' to install it."
        ) from e
    return HttpNtlmAuth(auth_user, auth_pass)


def playwright_credentials(
    auth_type: str | None, auth_user: str | None, auth_pass: str | None
) -> dict | None:
    """Credentials for Playwright's ``http_credentials``, or None.

    Chromium handles Basic and Digest challenges itself; NTLM is only
    reliable on Windows, but passing the credentials is harmless there.
    """
    if not auth_type or not auth_user or auth_pass is None:
        return None
    return {"username": auth_user, "password": auth_pass}

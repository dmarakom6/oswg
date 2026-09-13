"""Tests for HTTP authentication (basic/digest/ntlm)."""

import base64
import hashlib
import hmac
import http.server
import socketserver
import threading
from contextlib import contextmanager

import httpx
import pytest
from pydantic import ValidationError

from oswg.core.export import sanitize_config
from oswg.core.http_auth import AuthError, build_auth, playwright_credentials
from oswg.core.scraper import Scraper
from oswg.models import GenerateRequest

USER = "alice"
PASSWORD = "s3cret"


def _md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


# --- unit: build_auth -----------------------------------------------------


def test_build_auth_basic_and_digest():
    assert isinstance(build_auth("basic", "u", "p"), httpx.BasicAuth)
    assert isinstance(build_auth("digest", "u", "p"), httpx.DigestAuth)
    assert build_auth(None, None, None) is None


def test_build_auth_missing_credentials():
    with pytest.raises(AuthError, match="requires both"):
        build_auth("basic", None, None)
    with pytest.raises(AuthError, match="requires both"):
        build_auth("digest", "u", None)


def test_build_auth_unknown_type():
    with pytest.raises(AuthError, match="Unknown auth type"):
        build_auth("kerberos", "u", "p")


def test_build_auth_ntlm_requires_extra():
    with pytest.raises(AuthError, match="oswg\\[auth\\]"):
        build_auth("ntlm", "u", "p")


def test_playwright_credentials():
    assert playwright_credentials("basic", "u", "p") == {"username": "u", "password": "p"}
    assert playwright_credentials(None, "u", "p") is None


# --- helpers --------------------------------------------------------------


class _HandlerBase(http.server.BaseHTTPRequestHandler):
    PAGE = b"<html><body><p>authenticated content secret</p></body></html>"

    def _ok(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(self.PAGE)))
        self.end_headers()
        self.wfile.write(self.PAGE)

    def log_message(self, *args):  # silence request logging
        pass


class _BasicHandler(_HandlerBase):
    def do_GET(self):
        expected = base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode()
        if self.headers.get("Authorization") != f"Basic {expected}":
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="test"')
            self.end_headers()
            return
        self._ok()


class _BasicAndCookieHandler(_HandlerBase):
    """Requires valid Basic auth AND a session cookie."""

    def do_GET(self):
        expected = base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode()
        has_basic = self.headers.get("Authorization") == f"Basic {expected}"
        has_cookie = self.headers.get("Cookie") == "session=abc123"
        if not (has_basic and has_cookie):
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="test"')
            self.end_headers()
            return
        self._ok()


_DIGEST_REALM = "test"
_DIGEST_NONCE = "deadbeef"


def _verify_digest(header: str, method: str, path: str) -> bool:
    params = {}
    for part in header[len("Digest "):].split(","):
        key, _, value = part.strip().partition("=")
        params[key] = value.strip('"')
    ha1 = _md5(f"{params['username']}:{_DIGEST_REALM}:{PASSWORD}")
    ha2 = _md5(f"{method}:{path}")
    qop = params.get("qop")
    if qop:
        expected = _md5(
            f"{ha1}:{params['nonce']}:{params['nc']}:{params['cnonce']}:{qop}:{ha2}"
        )
    else:
        expected = _md5(f"{ha1}:{params['nonce']}:{ha2}")
    return hmac.compare_digest(expected, params["response"])


class _DigestHandler(_HandlerBase):
    def do_GET(self):
        header = self.headers.get("Authorization", "")
        if not header.startswith("Digest ") or not _verify_digest(header, self.command, self.path):
            self.send_response(401)
            self.send_header(
                "WWW-Authenticate",
                f'Digest realm="{_DIGEST_REALM}", qop="auth", '
                f'nonce="{_DIGEST_NONCE}", opaque="xyz"',
            )
            self.end_headers()
            return
        self._ok()


@contextmanager
def _serving(handler_cls):
    class Server(socketserver.TCPServer):
        allow_reuse_address = True

    with Server(("127.0.0.1", 0), handler_cls) as httpd:
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{httpd.server_address[1]}/"
        finally:
            httpd.shutdown()


# --- scraper integration --------------------------------------------------


async def test_basic_auth_scrape_succeeds():
    with _serving(_BasicHandler) as base:
        scraper = Scraper(
            max_pages=1, auth_type="basic", auth_user=USER, auth_pass=PASSWORD
        )
        content = await scraper.scrape(base)
    assert "authenticated" in content.body_text


async def test_basic_auth_scrape_fails_without_credentials():
    with _serving(_BasicHandler) as base:
        scraper = Scraper(max_pages=1)
        with pytest.raises(RuntimeError, match="0 pages scraped"):
            await scraper.scrape(base)


async def test_digest_auth_scrape_succeeds():
    with _serving(_DigestHandler) as base:
        scraper = Scraper(
            max_pages=1, auth_type="digest", auth_user=USER, auth_pass=PASSWORD
        )
        content = await scraper.scrape(base)
    assert "authenticated" in content.body_text


async def test_digest_auth_scrape_fails_without_credentials():
    with _serving(_DigestHandler) as base:
        scraper = Scraper(max_pages=1)
        with pytest.raises(RuntimeError, match="0 pages scraped"):
            await scraper.scrape(base)


async def test_http_auth_composes_with_cookies():
    with _serving(_BasicAndCookieHandler) as base:
        scraper = Scraper(
            max_pages=1,
            auth_type="basic",
            auth_user=USER,
            auth_pass=PASSWORD,
            cookies={"session": "abc123"},
        )
        content = await scraper.scrape(base)
    assert "authenticated" in content.body_text


# --- security + API validation --------------------------------------------


def test_auth_pass_never_in_sanitized_config():
    out = sanitize_config(
        {
            "auth_type": "basic",
            "auth_user": USER,
            "auth_pass": PASSWORD,
            "target_size": 10,
        }
    )
    assert "auth_pass" not in out
    assert out["auth_type"] == "basic"
    assert out["auth_user"] == USER
    assert out["target_size"] == 10


def test_api_rejects_unknown_auth_type():
    with pytest.raises(ValidationError, match="must be one of: basic, digest, ntlm"):
        GenerateRequest(
            url="http://example.com", size=10, max_pages=1, auth_type="kerberos"
        )

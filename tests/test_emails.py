"""Tests for email extraction (--emails)."""

import http.server
import socketserver
import threading
from contextlib import contextmanager

from oswg.core.emails import extract_emails
from oswg.core.generator import WordlistGenerator
from oswg.core.models import GenerationConfig
from oswg.core.scraper import Scraper

PAGE = b"""<html><head>
<meta name="author" content="ceo@example.com">
</head><body>
<p>Contact us for a quote.</p>
<script>var dev = 'dev@internal.local';</script>
<a href="mailto:boss@example.com?subject=hello">Email us</a>
</body></html>"""


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(PAGE)))
        self.end_headers()
        self.wfile.write(PAGE)

    def log_message(self, *args):  # silence request logging
        pass


@contextmanager
def _serving():
    with socketserver.TCPServer(("127.0.0.1", 0), _Handler) as httpd:
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{httpd.server_address[1]}/"
        finally:
            httpd.shutdown()


# --- unit: extract_emails -------------------------------------------------


def test_extract_emails_basic_and_mailto():
    html = 'Contact <a href="mailto:boss@example.com">Boss</a> or support@example.com.'
    assert extract_emails(html) == ["boss@example.com", "support@example.com"]


def test_extract_emails_dedupes_and_lowercases():
    html = "A@Example.COM b@example.com a@example.com"
    assert extract_emails(html) == ["a@example.com", "b@example.com"]


def test_extract_emails_mailto_with_query():
    html = '<a href="mailto:ceo@example.com?subject=hello">x</a>'
    assert extract_emails(html) == ["ceo@example.com"]


def test_extract_emails_mailto_entity_unescape():
    html = '<a href="mailto:john&#64;example.com">x</a>'
    assert extract_emails(html) == ["john@example.com"]


def test_extract_emails_ignores_noise():
    html = "no email here, just example.com and foo@bar"
    assert extract_emails(html) == []


def test_extract_emails_empty():
    assert extract_emails("") == []


# --- scraper integration --------------------------------------------------


async def test_scraper_extracts_emails_when_enabled():
    with _serving() as base:
        scraper = Scraper(max_pages=1, extract_emails=True)
        content = await scraper.scrape(base)
    assert content.emails == [
        "ceo@example.com",
        "dev@internal.local",
        "boss@example.com",
    ]


async def test_scraper_skips_emails_when_disabled():
    with _serving() as base:
        scraper = Scraper(max_pages=1, extract_emails=False)
        content = await scraper.scrape(base)
    assert content.emails == []


# --- generator ------------------------------------------------------------


async def test_generator_injects_full_emails_only():
    with _serving() as base:
        config = GenerationConfig(target_size=20, min_word_length=1, extract_emails=True)
        result = await WordlistGenerator().generate(base, config)
    assert result.email_count == 3
    assert "ceo@example.com" in result.base_words
    assert "dev@internal.local" in result.base_words
    assert "boss@example.com" in result.base_words


async def test_generator_skips_emails_when_disabled():
    with _serving() as base:
        config = GenerationConfig(target_size=20, min_word_length=1, extract_emails=False)
        result = await WordlistGenerator().generate(base, config)
    assert result.email_count == 0
    assert "ceo@example.com" not in result.base_words
    assert "boss@example.com" not in result.base_words

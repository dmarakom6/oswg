"""Tests for username extraction (--username)."""

import http.server
import socketserver
import threading
from contextlib import contextmanager

from bs4 import BeautifulSoup

from oswg.core.generator import WordlistGenerator
from oswg.core.models import GenerationConfig
from oswg.core.scraper import Scraper
from oswg.core.usernames import extract_usernames

PAGE = b"""<html><head>
<meta name="author" content="Jane Doe">
<meta property="og:author" content="janedoe">
</head><body>
<p>Contact <a href="mailto:janedoe@example.com">Janedoe</a> for a quote.</p>
<script>var dev = 'dev@internal.local';</script>
<a href="/team/alice">Alice</a>
<a href="/users/bob_42">Bob</a>
<a href="/profile/charlie">Charlie</a>
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


def _extract(html: str, links: list[str] | None = None) -> list[str]:
    return extract_usernames(html, BeautifulSoup(html, "lxml"), links or [])


# --- unit: sources --------------------------------------------------------


def test_email_local_parts():
    html = "Contact support@example.com or CEO@acme.com."
    assert _extract(html) == ["support", "ceo"]


def test_author_metadata_and_rel():
    html = (
        '<meta name="author" content="Jane Doe">'
        '<meta property="article:author" content="https://example.com/users/janedoe">'
        '<a rel="author" href="/">John Smith</a>'
    )
    assert _extract(html) == ["jane", "doe", "janedoe", "john", "smith"]


def test_profile_path_segments():
    html = "<p>hi</p>"
    links = [
        "https://example.com/users/alice",
        "https://example.com/team/bob_42",
        "https://example.com/profile/charlie",
        "https://example.com/author/dave",
        "https://example.com/@erin",
        "https://example.com/members/frank",
    ]
    assert _extract(html, links) == [
        "alice",
        "bob_42",
        "charlie",
        "dave",
        "erin",
        "frank",
    ]


def test_structural_segments_denied():
    html = "<p>hi</p>"
    links = [
        "https://example.com/users/login",
        "https://example.com/team/",
        "https://example.com/profile/users",
        "https://example.com/users/register",
    ]
    assert _extract(html, links) == []


def test_normalization_and_dedup():
    html = "John@Example.COM john@example.com <meta name=author content='John.Doe'>"
    result = _extract(html)
    assert result.count("john") == 1
    assert result.count("john.doe") == 1


def test_noise_rejected():
    html = "just plain words, no usernames, admin home user"
    assert _extract(html) == []


def test_social_handles():
    html = (
        '<a href="https://instagram.com/john.doe">ig</a>'
        '<a href="https://www.x.com/jdoe">x</a>'
        '<a href="https://twitter.com/jdoe">tw</a>'
        '<a href="https://github.com/jdoe">gh</a>'
        '<a href="https://www.linkedin.com/in/jane-doe">li</a>'
        '<a href="https://t.me/jdoe">tg</a>'
        '<a href="https://www.reddit.com/user/jdoe">rd</a>'
        '<a href="https://www.youtube.com/@jdoe">yt</a>'
        '<a href="https://www.threads.net/@jane_doe">th</a>'
        '<a href="https://instagram.com/explore/tags/cats">noise</a>'
        '<a href="https://github.com/topics/python">noise2</a>'
        '<a href="https://open.spotify.com/show/abc">not social</a>'
    )
    assert _extract(html) == [
        "john.doe",
        "jdoe",
        "jane-doe",
        "jane_doe",
    ]


# --- scraper integration --------------------------------------------------


async def test_scraper_extracts_usernames_when_enabled():
    with _serving() as base:
        scraper = Scraper(max_pages=1, extract_usernames=True)
        content = await scraper.scrape(base)
    assert "jane" in content.usernames
    assert "doe" in content.usernames
    assert "janedoe" in content.usernames
    assert "alice" in content.usernames
    assert "bob_42" in content.usernames
    assert "charlie" in content.usernames
    assert "dev" in content.usernames  # email local part from the script source


async def test_scraper_usernames_only_does_not_populate_emails():
    with _serving() as base:
        scraper = Scraper(max_pages=1, extract_usernames=True, extract_emails=False)
        content = await scraper.scrape(base)
    assert content.usernames
    assert content.emails == []


async def test_scraper_skips_usernames_when_disabled():
    with _serving() as base:
        scraper = Scraper(max_pages=1, extract_usernames=False)
        content = await scraper.scrape(base)
    assert content.usernames == []


# --- generator ------------------------------------------------------------


async def test_generator_separates_usernames_from_wordlist():
    with _serving() as base:
        config = GenerationConfig(
            target_size=30, min_word_length=1, extract_usernames=True
        )
        result = await WordlistGenerator().generate(base, config)
    assert "janedoe" in result.usernames
    assert "alice" in result.usernames
    for u in result.usernames:
        assert u not in result.base_words
        assert u not in result.words


async def test_generator_no_usernames_when_disabled():
    with _serving() as base:
        config = GenerationConfig(
            target_size=30, min_word_length=1, extract_usernames=False
        )
        result = await WordlistGenerator().generate(base, config)
    assert result.usernames == []

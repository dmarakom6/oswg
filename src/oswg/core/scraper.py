"""Website scraper for extracting keywords."""

import asyncio
import inspect
import random
import re
from collections import Counter
from typing import Callable
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from protego import Protego

from oswg.core.models import ScrapedContent

ProgressCallback = Callable[[str], None]

ROBOTS_USER_AGENT = "oswg"

SKIP_EXTENSIONS = frozenset({
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
    ".css", ".js", ".mjs", ".woff", ".woff2", ".ttf", ".eot",
    ".zip", ".tar", ".gz", ".rar",
    ".mp4", ".mp3", ".wav", ".avi", ".mov",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
})

SKIP_PATH_SEGMENTS = frozenset({
    "login", "logout", "signin", "signup", "sign-in", "sign-up",
    "admin", "administrator", "auth", "authentication",
    "cart", "checkout", "register", "registration",
    "password", "forgot", "reset", "recover",
    "terms", "privacy", "policy", "cookie",
    "contact", "about", "careers", "jobs",
})

SKIP_SCHEMES = frozenset({"mailto", "tel", "javascript", "data", "ftp"})


class Scraper:
    """Scrapes websites and extracts relevant keywords."""

    def __init__(
        self,
        max_pages: int = 10,
        timeout: float = 30.0,
        min_word_length: int = 3,
        max_word_length: int = 32,
        respect_robots: bool = False,
        user_agent: str | None = None,
        rate_limit: float = 0.0,
        jitter: bool = False,
    ):
        self.max_pages = max_pages
        self.timeout = timeout
        self.min_word_length = min_word_length
        self.max_word_length = max_word_length
        self.respect_robots = respect_robots
        self.user_agent = user_agent
        self.rate_limit = rate_limit
        self.jitter = jitter
        self.visited_urls: set[str] = set()
        self.page_word_sets: list[set[str]] = []
        self.failed_pages: list[tuple[str, str]] = []
        self._robots_cache: dict[str, Protego | None] = {}

    @property
    def _headers(self) -> dict[str, str] | None:
        """Request headers, derived from the current user_agent (dynamic)."""
        if self.user_agent:
            return {"User-Agent": self.user_agent}
        return None

    async def _emit_progress(self, callback: ProgressCallback | None, message: str) -> None:
        """Call a progress callback, awaiting it if it's a coroutine function."""
        if callback is None:
            return
        result = callback(message)
        if inspect.isawaitable(result):
            await result

    async def _rate_limit_sleep(
        self, first_request: bool, on_progress: ProgressCallback | None
    ) -> None:
        """Sleep between requests to respect a rate limit (skips the first request)."""
        if self.rate_limit <= 0 or first_request:
            return
        delay = self.rate_limit
        if self.jitter:
            delay = self.rate_limit * random.uniform(0.5, 1.5)
        if on_progress:
            await self._emit_progress(
                on_progress, f"Rate limit: waiting {delay:.1f}s..."
            )
        await asyncio.sleep(delay)

    async def _load_robots(self, netloc: str, scheme: str = "https") -> Protego | None:
        """Fetch and cache the robots.txt parser for a domain. None means allow-all."""
        if netloc in self._robots_cache:
            return self._robots_cache[netloc]

        robots_url = f"{scheme}://{netloc}/robots.txt"
        try:
            async with httpx.AsyncClient(
                timeout=min(self.timeout, 10.0),
                follow_redirects=True,
                headers=self._headers,
            ) as client:
                response = await client.get(robots_url)
                response.raise_for_status()
                parser = Protego.parse(response.text)
        except Exception:
            parser = None

        self._robots_cache[netloc] = parser
        return parser

    def _can_fetch(self, url: str) -> bool:
        """Check a URL against robots.txt rules for this domain."""
        if not self.respect_robots:
            return True
        parsed = urlparse(url)
        parser = self._robots_cache.get(parsed.netloc, None)
        if parser is None:
            return True
        return parser.can_fetch(url, self.user_agent or ROBOTS_USER_AGENT)

    async def scrape(
        self, url: str, sitemap: bool = False, on_progress: ProgressCallback | None = None
    ) -> ScrapedContent:
        """Scrape a website and extract keywords."""
        self.page_word_sets = []
        self.failed_pages = []
        urls_to_scrape = [url]

        if sitemap:
            sitemap_urls = await self._fetch_sitemap(url)
            if sitemap_urls:
                urls_to_scrape = [url] + [
                    u for u in sitemap_urls if u != url
                ]

        content = ScrapedContent(url=url)
        queue = list(urls_to_scrape)

        async with httpx.AsyncClient(
            timeout=self.timeout, follow_redirects=True, headers=self._headers
        ) as client:
            first_request = True
            while queue and len(self.visited_urls) < self.max_pages:
                current_url = queue.pop(0)
                if current_url in self.visited_urls:
                    continue

                if self.respect_robots:
                    parsed_url = urlparse(current_url)
                    await self._load_robots(parsed_url.netloc, parsed_url.scheme)
                    if not self._can_fetch(current_url):
                        self.failed_pages.append((current_url, "disallowed by robots.txt"))
                        if on_progress:
                            await self._emit_progress(
                                on_progress,
                                f"Skipped page: {current_url} (disallowed by robots.txt)",
                            )
                        continue

                await self._rate_limit_sleep(first_request, on_progress)
                first_request = False

                try:
                    page_content, discovered_links, page_words = await self._scrape_page(
                        client, current_url
                    )
                    content.keywords.extend(page_content.keywords)
                    content.body_text.extend(page_content.body_text)
                    content.links_text.extend(page_content.links_text)
                    self.page_word_sets.append(page_words)
                    if not content.title and page_content.title:
                        content.title = page_content.title
                    if not content.meta_description and page_content.meta_description:
                        content.meta_description = page_content.meta_description

                    if on_progress:
                        scraped_count = len(self.visited_urls)
                        total_count = max(len(self.visited_urls) + len(queue), len(self.visited_urls))
                        await self._emit_progress(
                            on_progress,
                            f"Scraped page {scraped_count}/{total_count}: "
                            f"{current_url} ({len(page_words)} words)",
                        )

                    for link in discovered_links:
                        if (
                            link not in self.visited_urls
                            and link not in queue
                            and len(self.visited_urls) + len(queue) < self.max_pages
                        ):
                            queue.append(link)
                except Exception as e:
                    self.failed_pages.append((current_url, str(e)))
                    if on_progress:
                        await self._emit_progress(
                            on_progress,
                            f"Skipped page: {current_url} ({str(e)})",
                        )
                    continue

        content.keywords = self._deduplicate_and_rank(content.keywords)
        if on_progress:
            await self._emit_progress(
                on_progress,
                f"Scraping complete: {len(self.page_word_sets)} pages, "
                f"{len(content.keywords)} unique words",
            )

        if not self.page_word_sets and self.failed_pages:
            url_failed, reason = self.failed_pages[0]
            raise RuntimeError(
                f"Failed to scrape {url_failed}: {reason} (0 pages scraped)"
            )

        return content

    async def scrape_urls(
        self, urls: list[str], sitemap: bool = False, on_progress: ProgressCallback | None = None
    ) -> ScrapedContent:
        """Scrape multiple seed URLs and merge results."""
        self.page_word_sets = []
        self.failed_pages = []
        all_content = ScrapedContent(url=urls[0] if urls else "")
        queue = list(urls)

        async with httpx.AsyncClient(
            timeout=self.timeout, follow_redirects=True, headers=self._headers
        ) as client:
            first_request = True
            while queue and len(self.visited_urls) < self.max_pages:
                current_url = queue.pop(0)
                if current_url in self.visited_urls:
                    continue

                if self.respect_robots:
                    parsed_url = urlparse(current_url)
                    await self._load_robots(parsed_url.netloc, parsed_url.scheme)
                    if not self._can_fetch(current_url):
                        self.failed_pages.append((current_url, "disallowed by robots.txt"))
                        if on_progress:
                            await self._emit_progress(
                                on_progress,
                                f"Skipped page: {current_url} (disallowed by robots.txt)",
                            )
                        continue

                await self._rate_limit_sleep(first_request, on_progress)
                first_request = False

                try:
                    page_content, discovered_links, page_words = await self._scrape_page(
                        client, current_url
                    )
                    all_content.keywords.extend(page_content.keywords)
                    all_content.body_text.extend(page_content.body_text)
                    all_content.links_text.extend(page_content.links_text)
                    self.page_word_sets.append(page_words)
                    if not all_content.title and page_content.title:
                        all_content.title = page_content.title
                    if not all_content.meta_description and page_content.meta_description:
                        all_content.meta_description = page_content.meta_description

                    if on_progress:
                        scraped_count = len(self.visited_urls)
                        total_count = max(len(self.visited_urls) + len(queue), len(self.visited_urls))
                        await self._emit_progress(
                            on_progress,
                            f"Scraped page {scraped_count}/{total_count}: "
                            f"{current_url} ({len(page_words)} words)",
                        )

                    for link in discovered_links:
                        if (
                            link not in self.visited_urls
                            and link not in queue
                            and len(self.visited_urls) + len(queue) < self.max_pages
                        ):
                            queue.append(link)
                except Exception as e:
                    self.failed_pages.append((current_url, str(e)))
                    if on_progress:
                        await self._emit_progress(
                            on_progress,
                            f"Skipped page: {current_url} ({str(e)})",
                        )
                    continue

        all_content.keywords = self._deduplicate_and_rank(all_content.keywords)
        if on_progress:
            await self._emit_progress(
                on_progress,
                f"Scraping complete: {len(self.page_word_sets)} pages, "
                f"{len(all_content.keywords)} unique words",
            )

        if not self.page_word_sets and self.failed_pages:
            url_failed, reason = self.failed_pages[0]
            raise RuntimeError(
                f"Failed to scrape {url_failed}: {reason} (0 pages scraped)"
            )

        return all_content

    async def _scrape_page(
        self, client: httpx.AsyncClient, url: str
    ) -> tuple[ScrapedContent, list[str], set[str]]:
        """Scrape a single page. Returns (content, discovered_links, page_words)."""
        self.visited_urls.add(url)
        response = await client.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        content = ScrapedContent(url=url)
        page_words: set[str] = set()

        title_tag = soup.find("title")
        if title_tag:
            content.title = title_tag.get_text(strip=True)

        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            content.meta_description = meta_desc.get("content", "")

        meta_keywords = soup.find("meta", attrs={"name": "keywords"})
        if meta_keywords:
            keywords_str = meta_keywords.get("content", "")
            content.keywords = [
                kw.strip() for kw in keywords_str.split(",") if kw.strip()
            ]

        for heading in soup.find_all(["h1", "h2", "h3"]):
            text = heading.get_text(strip=True)
            if text:
                content.headings.append(text)
                words = self._extract_words(text)
                content.keywords.extend(words)
                page_words.update(w.lower() for w in words)

        body = soup.find("body")
        if body:
            for script in body.find_all(["script", "style", "nav", "footer"]):
                script.decompose()

            text = body.get_text(separator=" ", strip=True)
            words = self._extract_words(text)
            content.body_text.extend(words)
            page_words.update(w.lower() for w in words)

        for link in soup.find_all("a"):
            link_text = link.get_text(strip=True)
            if link_text:
                words = self._extract_words(link_text)
                content.links_text.extend(words)
                page_words.update(w.lower() for w in words)

        discovered_links = self._extract_links(soup, url)

        return content, discovered_links, page_words

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        """Extract same-domain links from a parsed page, with filtering."""
        domain = urlparse(base_url).netloc
        links = []
        seen_paths: set[str] = set()

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            if not href or href.startswith("#"):
                continue

            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)

            if parsed.scheme in SKIP_SCHEMES:
                continue
            if parsed.netloc != domain:
                continue

            path_lower = parsed.path.lower()
            path_ext = "." + path_lower.rsplit(".", 1)[-1] if "." in path_lower else ""
            if path_ext in SKIP_EXTENSIONS:
                continue

            path_parts = set(path_lower.strip("/").split("/"))
            if path_parts & SKIP_PATH_SEGMENTS:
                continue

            normalized_path = parsed.path.rstrip("/") or "/"
            if normalized_path in seen_paths:
                continue
            seen_paths.add(normalized_path)

            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if clean_url not in self.visited_urls and self._can_fetch(clean_url):
                links.append(clean_url)

        return links

    async def _fetch_sitemap(self, base_url: str) -> list[str]:
        """Fetch and parse sitemap.xml for URLs."""
        parsed = urlparse(base_url)
        sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"

        if self.respect_robots:
            await self._load_robots(parsed.netloc, parsed.scheme)
            if not self._can_fetch(sitemap_url):
                return []

        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self._headers) as client:
                response = await client.get(sitemap_url)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "xml")
                urls = []
                for loc in soup.find_all("loc"):
                    url_text = loc.get_text(strip=True)
                    if url_text:
                        urls.append(url_text)
                return urls
        except Exception:
            return []

    def _extract_words(self, text: str) -> list[str]:
        """Extract meaningful words from text."""
        min_len = self.min_word_length
        max_len = self.max_word_length
        return re.findall(rf"[a-zA-Z]{{{min_len},{max_len}}}", text)

    def _deduplicate_and_rank(self, words: list[str]) -> list[str]:
        """Deduplicate and rank words by frequency."""
        counter = Counter(word.lower() for word in words)
        return [word for word, _ in counter.most_common()]

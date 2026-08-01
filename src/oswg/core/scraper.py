"""Website scraper for extracting keywords."""

import re
from collections import Counter
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from oswg.core.models import ScrapedContent

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
    ):
        self.max_pages = max_pages
        self.timeout = timeout
        self.min_word_length = min_word_length
        self.max_word_length = max_word_length
        self.visited_urls: set[str] = set()

    async def scrape(self, url: str, sitemap: bool = False) -> ScrapedContent:
        """Scrape a website and extract keywords."""
        urls_to_scrape = [url]

        if sitemap:
            sitemap_urls = await self._fetch_sitemap(url)
            if sitemap_urls:
                urls_to_scrape = [url] + [
                    u for u in sitemap_urls if u != url
                ]

        content = ScrapedContent(url=url)
        queue = list(urls_to_scrape)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while queue and len(self.visited_urls) < self.max_pages:
                current_url = queue.pop(0)
                if current_url in self.visited_urls:
                    continue

                try:
                    page_content, discovered_links = await self._scrape_page(
                        client, current_url
                    )
                    content.keywords.extend(page_content.keywords)
                    content.body_text.extend(page_content.body_text)
                    content.links_text.extend(page_content.links_text)
                    if not content.title and page_content.title:
                        content.title = page_content.title
                    if not content.meta_description and page_content.meta_description:
                        content.meta_description = page_content.meta_description

                    for link in discovered_links:
                        if (
                            link not in self.visited_urls
                            and link not in queue
                            and len(self.visited_urls) + len(queue) < self.max_pages
                        ):
                            queue.append(link)
                except Exception:
                    continue

        content.keywords = self._deduplicate_and_rank(content.keywords)
        return content

    async def scrape_urls(self, urls: list[str], sitemap: bool = False) -> ScrapedContent:
        """Scrape multiple seed URLs and merge results."""
        all_content = ScrapedContent(url=urls[0] if urls else "")
        queue = list(urls)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while queue and len(self.visited_urls) < self.max_pages:
                current_url = queue.pop(0)
                if current_url in self.visited_urls:
                    continue

                try:
                    page_content, discovered_links = await self._scrape_page(
                        client, current_url
                    )
                    all_content.keywords.extend(page_content.keywords)
                    all_content.body_text.extend(page_content.body_text)
                    all_content.links_text.extend(page_content.links_text)
                    if not all_content.title and page_content.title:
                        all_content.title = page_content.title
                    if not all_content.meta_description and page_content.meta_description:
                        all_content.meta_description = page_content.meta_description

                    for link in discovered_links:
                        if (
                            link not in self.visited_urls
                            and link not in queue
                            and len(self.visited_urls) + len(queue) < self.max_pages
                        ):
                            queue.append(link)
                except Exception:
                    continue

        all_content.keywords = self._deduplicate_and_rank(all_content.keywords)
        return all_content

    async def _scrape_page(
        self, client: httpx.AsyncClient, url: str
    ) -> tuple[ScrapedContent, list[str]]:
        """Scrape a single page. Returns (content, discovered_links)."""
        self.visited_urls.add(url)
        response = await client.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        content = ScrapedContent(url=url)

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
                content.keywords.extend(self._extract_words(text))

        body = soup.find("body")
        if body:
            for script in body.find_all(["script", "style", "nav", "footer"]):
                script.decompose()

            text = body.get_text(separator=" ", strip=True)
            words = self._extract_words(text)
            content.body_text.extend(words)

        for link in soup.find_all("a"):
            link_text = link.get_text(strip=True)
            if link_text:
                content.links_text.extend(self._extract_words(link_text))

        discovered_links = self._extract_links(soup, url)

        return content, discovered_links

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
            if clean_url not in self.visited_urls:
                links.append(clean_url)

        return links

    async def _fetch_sitemap(self, base_url: str) -> list[str]:
        """Fetch and parse sitemap.xml for URLs."""
        parsed = urlparse(base_url)
        sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
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

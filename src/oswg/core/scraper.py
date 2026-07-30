"""Website scraper for extracting keywords."""

import re
from collections import Counter
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from oswg.core.models import ScrapedContent


class Scraper:
    """Scrapes websites and extracts relevant keywords."""

    def __init__(self, max_pages: int = 10, timeout: float = 30.0):
        self.max_pages = max_pages
        self.timeout = timeout
        self.visited_urls: set[str] = set()

    async def scrape(self, url: str) -> ScrapedContent:
        """Scrape a website and extract keywords."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            content = await self._scrape_page(client, url)

            if self.max_pages > 1:
                links = self._extract_links(content.url)
                for link in links[: self.max_pages - 1]:
                    if link not in self.visited_urls:
                        try:
                            page_content = await self._scrape_page(client, link)
                            content.keywords.extend(page_content.keywords)
                            content.body_text.extend(page_content.body_text)
                            content.links_text.extend(page_content.links_text)
                        except Exception:
                            continue

        content.keywords = self._deduplicate_and_rank(content.keywords)
        return content

    async def _scrape_page(self, client: httpx.AsyncClient, url: str) -> ScrapedContent:
        """Scrape a single page."""
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

        return content

    def _extract_links(self, base_url: str) -> list[str]:
        """Extract links from current page."""
        domain = urlparse(base_url).netloc
        links = []

        async def get_page_links():
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(base_url)
                soup = BeautifulSoup(response.text, "lxml")
                for a_tag in soup.find_all("a", href=True):
                    href = a_tag["href"]
                    full_url = urljoin(base_url, href)
                    parsed = urlparse(full_url)
                    if parsed.netloc == domain and full_url not in self.visited_urls:
                        links.append(full_url)

        return links

    def _extract_words(self, text: str) -> list[str]:
        """Extract meaningful words from text."""
        words = re.findall(r"[a-zA-Z]{3,}", text)
        return [w for w in words if len(w) >= 3]

    def _deduplicate_and_rank(self, words: list[str]) -> list[str]:
        """Deduplicate and rank words by frequency."""
        counter = Counter(word.lower() for word in words)
        return [word for word, _ in counter.most_common()]

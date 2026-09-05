"""AI completions for wordlist generation (OpenAI-compatible API + Ollama).

Supports any OpenAI-compatible ``/chat/completions`` endpoint — OpenAI
itself and a local Ollama server (``http://localhost:11434/v1``). Ollama
runs fully offline, so it is the recommended provider and is auto-detected
when the provider is ``auto``.
"""

from __future__ import annotations

import asyncio
import math
import os
import re
from dataclasses import dataclass

import httpx

DEFAULT_OLLAMA_SERVER_URL = "http://localhost:11434"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = (
    "You are a wordlist generator for password security testing. "
    "Given a list of words, produce words with similar meaning or closely "
    "associated with them that people plausibly choose for passwords. "
    "Respond ONLY with lowercase words, one word per line. "
    "No numbering, bullets, punctuation, explanation, or duplicates."
)


class AIError(RuntimeError):
    """Raised when an AI provider cannot be used or a request fails."""


@dataclass(frozen=True)
class AIClientConfig:
    """Resolved provider settings for an AI client."""

    provider: str
    model: str
    base_url: str
    api_key: str = ""

    @property
    def display_name(self) -> str:
        return f"{self.provider} ({self.model})"


async def detect_ollama(
    server_url: str = DEFAULT_OLLAMA_SERVER_URL,
    timeout: float = 2.0,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict | None:
    """Detect a local Ollama server and return ``{"base_url", "model"}``.

    Returns ``None`` when the server is unreachable; ``model`` is ``None``
    (with the server URL) when it responds but has no usable models.
    Embedding models (e.g. ``nomic-embed-text``) are ignored.
    """
    try:
        async with httpx.AsyncClient(transport=transport, timeout=timeout) as client:
            response = await client.get(f"{server_url.rstrip('/')}/api/tags")
            response.raise_for_status()
            tags = response.json().get("models", [])
    except (httpx.HTTPError, ValueError, KeyError):
        return None

    names = [tag.get("name", "") for tag in tags if tag.get("name")]
    if not names:
        return {"base_url": f"{server_url.rstrip('/')}/v1", "model": None}
    usable = [n for n in names if not any(s in n.lower() for s in ("embed", "nomic"))]
    return {"base_url": f"{server_url.rstrip('/')}/v1", "model": (usable or names)[0]}


async def resolve_ai_config(
    provider: str = "auto",
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    *,
    detection_timeout: float = 2.0,
    transport: httpx.AsyncBaseTransport | None = None,
) -> AIClientConfig:
    """Resolve a provider choice into a concrete ``AIClientConfig``.

    ``auto`` (recommended) detects a local Ollama server first — fully
    offline generation — and falls back to OpenAI when ``OPENAI_API_KEY``
    is set. For explicit providers the same detection is used to fill in
    an unset model (Ollama) or to fail with a helpful message.
    """
    provider = (provider or "auto").lower()
    api_key = api_key or os.environ.get("OPENAI_API_KEY", "")

    if provider == "auto":
        detected = await detect_ollama(timeout=detection_timeout, transport=transport)
        if detected is not None:
            if not detected["model"]:
                raise AIError(
                    f"Ollama is running at {DEFAULT_OLLAMA_SERVER_URL} but has no "
                    "models installed. Install one with `ollama pull llama3.2`."
                )
            return AIClientConfig(
                provider="ollama",
                model=model or detected["model"],
                base_url=base_url or detected["base_url"],
            )
        if api_key:
            return AIClientConfig(
                provider="openai",
                model=model or DEFAULT_OPENAI_MODEL,
                base_url=base_url or DEFAULT_OPENAI_BASE_URL,
                api_key=api_key,
            )
        raise AIError(
            "No AI provider available: no local Ollama server at "
            f"{DEFAULT_OLLAMA_SERVER_URL} and OPENAI_API_KEY is not set. "
            "Start Ollama for fully offline generation (recommended), or export OPENAI_API_KEY."
        )

    if provider == "ollama":
        if model:
            return AIClientConfig(
                provider="ollama",
                model=model,
                base_url=base_url or f"{DEFAULT_OLLAMA_SERVER_URL}/v1",
            )
        detected = await detect_ollama(
            base_url or DEFAULT_OLLAMA_SERVER_URL,
            timeout=detection_timeout,
            transport=transport,
        )
        if detected is None:
            raise AIError(
                f"Ollama not detected at {base_url or DEFAULT_OLLAMA_SERVER_URL}. "
                "Start it with `ollama serve` and install a model "
                "(e.g. `ollama pull llama3.2`), or pass --ai-base-url."
            )
        if not detected["model"]:
            raise AIError(
                f"Ollama is running at {base_url or DEFAULT_OLLAMA_SERVER_URL} but has "
                "no models installed. Install one with `ollama pull llama3.2`."
            )
        return AIClientConfig(provider="ollama", model=detected["model"], base_url=detected["base_url"])

    if provider == "openai":
        if not api_key and not base_url:
            raise AIError(
                "OpenAI provider requires OPENAI_API_KEY (export it) or an "
                "--ai-base-url pointing at a local OpenAI-compatible server."
            )
        return AIClientConfig(
            provider="openai",
            model=model or DEFAULT_OPENAI_MODEL,
            base_url=base_url or DEFAULT_OPENAI_BASE_URL,
            api_key=api_key,
        )

    raise AIError(f"Unknown AI provider {provider!r} (expected auto, ollama or openai).")


class AICompleter:
    """Async OpenAI-compatible client: batching, concurrency, retries.

    All randomness is disabled (``temperature=0``) and input words are
    sorted before batching, so results are as deterministic as the model
    allows. A simple cost guard caps both the number of requests (one per
    batch) and the total words collected.
    """

    def __init__(
        self,
        config: AIClientConfig,
        *,
        max_concurrency: int = 2,
        batch_size: int = 10,
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff: float = 1.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.config = config
        self.max_concurrency = max_concurrency
        self.batch_size = batch_size
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff
        headers = {"Authorization": f"Bearer {config.api_key}"} if config.api_key else {}
        self._client = httpx.AsyncClient(transport=transport, timeout=timeout, headers=headers)
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def complete_many(
        self,
        words: list[str],
        *,
        k: int = 3,
        min_length: int = 3,
        max_length: int = 32,
        max_words: int = 1000,
        blocked: set[str] | None = None,
    ) -> list[str]:
        """Return up to ``max_words`` related words for ``words``.

        Words are deduplicated, lowercased and sorted for a stable prompt;
        requests are fanned out under a semaphore and results are collected
        in batch order, so the pass is deterministic given the model.
        """
        blocked = set(blocked or [])
        ordered = sorted({w.strip().lower() for w in words if w.strip()})
        if not ordered or max_words <= 0 or k <= 0:
            return []

        # Cost guard: at most ceil(max_words / (batch * k)) requests.
        max_requests = max(1, math.ceil(max_words / (self.batch_size * k)))
        batches = [
            ordered[i : i + self.batch_size]
            for i in range(0, len(ordered), self.batch_size)
        ][:max_requests]

        async def run(batch: list[str]) -> list[str]:
            async with self._semaphore:
                return await self._complete_batch(batch, k, min_length, max_length, blocked)

        results = await asyncio.gather(*(run(batch) for batch in batches))

        collected: list[str] = []
        for batch_words in results:
            for word in batch_words:
                if len(collected) >= max_words:
                    break
                collected.append(word)
        return collected

    async def _complete_batch(
        self,
        batch: list[str],
        k: int,
        min_length: int,
        max_length: int,
        blocked: set[str],
    ) -> list[str]:
        payload = {
            "model": self.config.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": self._build_user_prompt(batch, k)},
            ],
        }
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.post(url, json=payload)
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                return self._parse(content, batch, k, min_length, max_length, blocked)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    await asyncio.sleep(self.backoff * (2**attempt))
                    continue
                raise AIError(
                    f"{self.config.display_name} request failed: HTTP {exc.response.status_code}"
                ) from exc
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                if attempt < self.max_retries:
                    await asyncio.sleep(self.backoff * (2**attempt))
                    continue
                raise AIError(f"{self.config.display_name} request failed: {exc}") from exc

        return []  # unreachable; kept for the type checker

    @staticmethod
    def _build_user_prompt(words: list[str], k: int) -> str:
        numbered = "\n".join(f"{i + 1}. {w}" for i, w in enumerate(words))
        return (
            f"For each of the {len(words)} words below, list {k} words with similar "
            f"meaning or closely associated with it that people might use in passwords:\n"
            f"{numbered}\n"
            f"Output exactly the related words, one per line, {len(words) * k} lines total."
        )

    def _parse(
        self,
        content: str,
        batch: list[str],
        k: int,
        min_length: int,
        max_length: int,
        blocked: set[str],
    ) -> list[str]:
        """Extract valid words from a model response (never trust the model)."""
        found: list[str] = []
        for line in content.splitlines():
            token = self._clean_token(line)
            if not token:
                continue
            if len(token) < min_length or len(token) > max_length:
                continue
            if not token.isalpha():
                continue
            if token in blocked:
                continue
            if token in found:
                continue
            found.append(token)
            if len(found) >= len(batch) * k:
                break
        return found

    @staticmethod
    def _clean_token(line: str) -> str:
        """Strip bullets/numbering/punctuation from a model output line."""
        token = line.strip().lower()
        if not token:
            return ""
        token = re.sub(r"^[\s\d]*[.)\]\-•*]+\s*", "", token)
        return token.strip(" .,;:'\"()[]{}")

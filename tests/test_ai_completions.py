"""Tests for --ai-completions (OpenAI-compatible / Ollama expansion)."""

import asyncio
import json
import re

import httpx
import pytest

from oswg.core.ai import (
    AIClientConfig,
    AICompleter,
    AIError,
    detect_ollama,
    resolve_ai_config,
)
from oswg.core.generator import WordlistGenerator
from oswg.core.models import GenerationConfig


def _completion_response(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def _derived_handler(k: int = 2, extra: str = ""):
    """Return a transport handler deriving "<word>ish" lines from the prompt."""

    def handler(request: httpx.Request) -> httpx.Response:
        data = json.loads(request.content)
        assert data["temperature"] == 0, "requests must be deterministic (temperature 0)"
        user = data["messages"][1]["content"]
        words = re.findall(r"^\d+\.\s*(\w+)$", user, flags=re.M)
        lines = [f"{i + 1}. {w}ish" for w in words for i in range(k)]
        return _completion_response("\n".join(lines) + extra)

    return handler


def _down_handler(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("connection refused")


def _ollama_tags_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={"models": [{"name": "nomic-embed-text"}, {"name": "llama3.2"}]},
    )


def _completer(config: AIClientConfig, handler, **kwargs) -> AICompleter:
    return AICompleter(
        config,
        transport=httpx.MockTransport(handler),
        max_retries=0,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Ollama detection & provider resolution
# ---------------------------------------------------------------------------


async def test_detect_ollama_found():
    found = await detect_ollama(transport=httpx.MockTransport(_ollama_tags_handler))
    assert found is not None
    assert found["base_url"] == "http://localhost:11434/v1"
    assert found["model"] == "llama3.2"  # embedding model filtered out


async def test_detect_ollama_unreachable_returns_none():
    found = await detect_ollama(transport=httpx.MockTransport(_down_handler))
    assert found is None


async def test_resolve_auto_prefers_ollama():
    resolved = await resolve_ai_config(transport=httpx.MockTransport(_ollama_tags_handler))
    assert resolved.provider == "ollama"
    assert resolved.model == "llama3.2"
    assert resolved.base_url == "http://localhost:11434/v1"


async def test_resolve_auto_falls_back_to_openai(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    resolved = await resolve_ai_config(transport=httpx.MockTransport(_down_handler))
    assert resolved.provider == "openai"
    assert resolved.model == "gpt-4o-mini"
    assert resolved.api_key == "sk-test"


async def test_resolve_auto_raises_when_unavailable(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(AIError, match="No AI provider available"):
        await resolve_ai_config(transport=httpx.MockTransport(_down_handler))


async def test_resolve_ollama_without_model_errors_when_down():
    with pytest.raises(AIError, match="Ollama not detected"):
        await resolve_ai_config(
            provider="ollama", transport=httpx.MockTransport(_down_handler)
        )


async def test_resolve_ollama_with_model_skips_detection():
    resolved = await resolve_ai_config(
        provider="ollama", model="llama3.2", transport=httpx.MockTransport(_down_handler)
    )
    assert resolved.base_url == "http://localhost:11434/v1"


async def test_resolve_openai_requires_key_or_base_url(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(AIError, match="OPENAI_API_KEY"):
        await resolve_ai_config(provider="openai")


async def test_resolve_unknown_provider_raises():
    with pytest.raises(AIError, match="Unknown AI provider"):
        await resolve_ai_config(provider="deepseek")


# ---------------------------------------------------------------------------
# Batch completion behavior
# ---------------------------------------------------------------------------


async def test_complete_many_parses_and_filters():
    config = AIClientConfig("ollama", "llama3.2", "http://localhost:11434/v1")
    handler = _derived_handler(k=2, extra="\n# comment\n- garbage-word\n123\nx\n")
    completer = _completer(config, handler)
    # Input words are sorted before batching ("cream" < "nutella") and
    # duplicates within a response are deduplicated.
    result = await completer.complete_many(["nutella", "cream"], k=2)
    assert result == ["creamish", "nutellaish"]
    await completer.aclose()


async def test_complete_many_respects_blocked_and_length():
    config = AIClientConfig("openai", "gpt-4o-mini", "https://api.openai.com/v1", "sk-test")
    handler = _derived_handler(k=2, extra="\nblockedword\n")
    completer = _completer(config, handler)
    result = await completer.complete_many(
        ["alpha"],
        k=2,
        min_length=3,
        max_length=20,
        blocked={"blockedword"},
    )
    assert "blockedword" not in result
    assert "alphaish" in result
    await completer.aclose()


async def test_complete_many_is_deterministic():
    config = AIClientConfig("ollama", "llama3.2", "http://localhost:11434/v1")
    words = ["zeta", "alpha", "beta", "delta"]
    a = _completer(config, _derived_handler(k=2))
    b = _completer(config, _derived_handler(k=2))
    try:
        first = await a.complete_many(words, k=2)
        second = await b.complete_many(words, k=2)
    finally:
        await a.aclose()
        await b.aclose()
    assert first == second


async def test_complete_many_cost_guard_caps_words_and_requests():
    config = AIClientConfig("ollama", "llama3.2", "http://localhost:11434/v1")
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        data = json.loads(request.content)
        user = data["messages"][1]["content"]
        words = re.findall(r"^\d+\.\s*(\w+)$", user, flags=re.M)
        lines = [f"{w}variant{chr(97 + i)}" for w in words for i in range(4)]
        return _completion_response("\n".join(lines))

    completer = _completer(config, handler)
    words = [f"w{chr(97 + i)}" for i in range(20)]  # 20 alpha words, 2 batches of 10
    result = await completer.complete_many(words, k=4, max_words=5, max_length=32)
    assert len(result) == 5
    assert len(calls) == 1  # ceil(5 / (10 * 4)) = 1 request
    await completer.aclose()


async def test_complete_many_bounds_concurrency():
    config = AIClientConfig("ollama", "llama3.2", "http://localhost:11434/v1")
    state = {"active": 0, "peak": 0}
    lock = asyncio.Lock()

    async def handler(request: httpx.Request) -> httpx.Response:
        async with lock:
            state["active"] += 1
            state["peak"] = max(state["peak"], state["active"])
        await asyncio.sleep(0.02)
        async with lock:
            state["active"] -= 1
        data = json.loads(request.content)
        user = data["messages"][1]["content"]
        words = re.findall(r"^\d+\.\s*(\w+)$", user, flags=re.M)
        return _completion_response("\n".join(f"{w}-r" for w in words))

    completer = _completer(config, handler, max_concurrency=2)
    words = [f"word{i}" for i in range(30)]  # 3 batches
    await completer.complete_many(words, k=1, max_words=100)
    assert state["peak"] <= 2
    await completer.aclose()


async def test_complete_many_retries_on_transient_errors():
    config = AIClientConfig("ollama", "llama3.2", "http://localhost:11434/v1")
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503, json={"error": "busy"})
        return _completion_response("cream\nchocolate")

    completer = AICompleter(
        config,
        transport=httpx.MockTransport(handler),
        max_retries=3,
        backoff=0.01,
    )
    result = await completer.complete_many(["nutella"], k=2)
    assert result == ["cream", "chocolate"]
    assert calls["n"] == 3
    await completer.aclose()


async def test_complete_many_fails_after_retries():
    config = AIClientConfig("ollama", "llama3.2", "http://localhost:11434/v1")
    completer = AICompleter(
        config,
        transport=httpx.MockTransport(lambda r: httpx.Response(500, json={})),
        max_retries=2,
        backoff=0.01,
    )
    with pytest.raises(AIError, match="ollama .* request failed: HTTP 500"):
        await completer.complete_many(["nutella"], k=2)
    await completer.aclose()


# ---------------------------------------------------------------------------
# Generator integration
# ---------------------------------------------------------------------------


class FakeCompleter:
    def __init__(self, words: list[str]):
        self.words = words
        self.config = AIClientConfig("ollama", "fake-model", "http://localhost:11434/v1")

    async def complete_many(self, words, **kwargs):
        return list(self.words)

    async def aclose(self):
        pass


async def test_generator_ai_expand_appends_words():
    generator = WordlistGenerator(ai_completer=FakeCompleter(["cream", "chocolate"]))
    base_words = ["nutella"]
    config = GenerationConfig(
        ai_enabled=True, filter_stopwords=False, min_word_length=3, max_word_length=32
    )
    progress = []

    async def on_progress(message: str):
        progress.append(message)

    added = await generator._ai_expand_base_words(base_words, config, on_progress=on_progress)
    assert added == 2
    assert base_words == ["nutella", "cream", "chocolate"]
    assert any("AI completions" in m for m in progress)


async def test_generator_ai_expand_dedupes_and_filters_stopwords():
    generator = WordlistGenerator(ai_completer=FakeCompleter(["cream", "the", "nutella"]))
    base_words = ["nutella"]
    config = GenerationConfig(
        ai_enabled=True, filter_stopwords=True, min_word_length=3, max_word_length=32
    )
    added = await generator._ai_expand_base_words(base_words, config)
    assert added == 1  # "the" is a stopword, "nutella" already a base word
    assert base_words == ["nutella", "cream"]


def test_cli_help_lists_ai_flags():
    from typer.testing import CliRunner

    from oswg.cli import app

    result = CliRunner().invoke(app, ["generate", "--help"])
    assert result.exit_code == 0, result.output
    assert "--ai-completions" in result.output
    assert "--ai-provider" in result.output
    assert "--ai-max-words" in result.output
    assert "--ai-words-per-word" in result.output


def test_generate_request_validates_ai_provider():
    from pydantic import ValidationError

    from oswg.models import GenerateRequest

    request = GenerateRequest(
        url="https://example.com",
        ai_enabled=True,
        ai_provider="ollama",
        ai_model="llama3.2",
        ai_max_words=50,
    )
    assert request.ai_provider == "ollama"
    with pytest.raises(ValidationError):
        GenerateRequest(url="https://example.com", ai_provider="bogus")

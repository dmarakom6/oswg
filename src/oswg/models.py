"""Pydantic models for OSWG API."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class JobType(str, Enum):
    GENERATE = "generate"
    SCRAPE = "scrape"
    MUTATE = "mutate"


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class BaseRequest(BaseModel):
    retention_seconds: Optional[int] = Field(
        None,
        description="How long to keep the result (seconds).",
        ge=60,
        le=86400,
    )


class GenerateRequest(BaseRequest):
    url: str = Field(..., description="Target URL to scrape.")
    urls: list[str] = Field(default=[], description="Additional URLs to scrape.", max_length=50)
    sitemap: bool = Field(False, description="Use sitemap.xml for page discovery.")
    size: int = Field(10000, description="Target wordlist size.", ge=1, le=1000000)
    max_pages: int = Field(10, description="Maximum pages to scrape.", ge=1, le=100)
    min_length: int = Field(3, description="Minimum word length.", ge=1, le=32)
    max_length: int = Field(32, description="Maximum word length.", ge=1, le=128)
    enable_leet: bool = Field(True, description="Enable l33t speak mutations.")
    enable_uppercase: bool = Field(True, description="Enable uppercase/case mutations.")
    enable_reverse_leet: bool = Field(False, description="Convert l33t chars back to letters.")
    enable_numbers: bool = Field(True, description="Enable number suffix mutations.")
    enable_special: bool = Field(False, description="Enable special character mutations.")
    leet_level: int = Field(1, description="L33t speak intensity (1=basic, 2=advanced).", ge=1, le=2)
    deduplicate: bool = Field(True, description="Remove duplicate words from output.")
    filter_stopwords: bool = Field(
        True, description="Filter common English and web boilerplate words."
    )
    stopword_threshold: float = Field(
        0.5,
        description="Exclude words appearing on >this fraction of pages.",
        ge=0.0,
        le=1.0,
    )
    extra_stopwords: list[str] = Field(
        default=[],
        description="Additional stopwords to exclude.",
        max_length=10000,
    )
    common_years: list[int] = Field(
        default=[],
        description="Custom years for number suffix mutations. Empty = current year + previous 5.",
        max_length=20,
    )
    special_chars: list[str] = Field(
        default=[],
        description="Custom special characters for mutations. Empty = ! @ # $.",
        max_length=10,
    )
    timeout: float = Field(30.0, description="HTTP request timeout in seconds.", ge=1.0, le=300.0)
    respect_robots: bool = Field(False, description="Respect robots.txt rules.")
    user_agent: Optional[str] = Field(None, description="Custom User-Agent header for requests.", max_length=200)
    rate_limit: float = Field(0.0, description="Delay between requests in seconds.", ge=0.0, le=60.0)
    jitter: bool = Field(False, description="Randomize delay by ±50% (with rate_limit).")
    headers: dict[str, str] = Field(default={}, description="Custom request headers.")
    cookies: dict[str, str] = Field(default={}, description="Custom request cookies.")
    proxy: Optional[str] = Field(None, description="Proxy for requests (http/https/socks5).", max_length=200)
    merge_words: list[str] = Field(default=[], description="External words to merge and mutate.", max_length=100000)
    merge_max: int = Field(5000, description="Total cap on merged words.", ge=1, le=1000000)
    merge_builtin: bool = Field(False, description="Merge bundled bundled common passwords.")
    merge_rockyou: bool = Field(False, description="Merge /usr/share/wordlists/rockyou.txt if present.")
    enable_random_combine: bool = Field(
        False, description="Bind random pairs of base words in random case/l33t forms."
    )
    random_combine_count: int = Field(
        1000, description="Number of random pair combinations to generate.", ge=1, le=1000000
    )
    random_combine_seed: Optional[int] = Field(
        None, description="Seed for reproducible random combinations. Empty = random each run."
    )
    ai_enabled: bool = Field(
        False, description="Expand base words with AI-generated related words (Ollama or OpenAI)."
    )
    ai_provider: str = Field(
        "auto",
        description="AI provider: auto (recommended, detects local Ollama first), ollama, openai.",
    )
    ai_model: Optional[str] = Field(
        None, description="AI model (e.g. llama3.2, gpt-4o-mini). Empty = auto-detect.", max_length=100
    )
    ai_base_url: Optional[str] = Field(
        None,
        description="OpenAI-compatible base URL override (e.g. a custom Ollama address).",
        max_length=300,
    )
    ai_max_words: int = Field(
        1000, description="Cap on total AI-generated words (cost guard).", ge=1, le=100000
    )
    ai_words_per_word: int = Field(
        3, description="Related words requested per base word.", ge=1, le=20
    )
    ai_max_concurrency: int = Field(
        2, description="Max concurrent AI requests.", ge=1, le=16
    )
    ai_timeout: float = Field(
        30.0, description="AI request timeout in seconds.", ge=1.0, le=300.0
    )
    rule_format: Optional[str] = Field(
        None,
        description="Emit cracker rules (jtr|hashcat) + base words instead of an expanded wordlist.",
    )

    @field_validator("rule_format")
    @classmethod
    def _validate_rule_format(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in ("jtr", "hashcat"):
            raise ValueError("must be one of: jtr, hashcat")
        return value

    @field_validator("ai_provider")
    @classmethod
    def _validate_ai_provider(cls, value: str) -> str:
        if value not in ("auto", "ollama", "openai"):
            raise ValueError("must be one of: auto, ollama, openai")
        return value

    @field_validator("special_chars")
    @classmethod
    def _validate_special_chars(cls, values: list[str]) -> list[str]:
        for value in values:
            if len(value) != 1 or value.isalnum() or value.isspace():
                raise ValueError(
                    f"'{value}' is not a special character "
                    "(must be a single non-alphanumeric character)"
                )
        return values


class ScrapeRequest(BaseRequest):
    url: str = Field(..., description="Target URL to scrape.")
    urls: list[str] = Field(default=[], description="Additional URLs to scrape.", max_length=50)
    sitemap: bool = Field(False, description="Use sitemap.xml for page discovery.")
    max_pages: int = Field(10, description="Maximum pages to scrape.", ge=1, le=100)
    timeout: float = Field(30.0, description="HTTP request timeout in seconds.", ge=1.0, le=300.0)
    respect_robots: bool = Field(False, description="Respect robots.txt rules.")
    user_agent: Optional[str] = Field(None, description="Custom User-Agent header for requests.", max_length=200)
    rate_limit: float = Field(0.0, description="Delay between requests in seconds.", ge=0.0, le=60.0)
    jitter: bool = Field(False, description="Randomize delay by ±50% (with rate_limit).")
    headers: dict[str, str] = Field(default={}, description="Custom request headers.")
    cookies: dict[str, str] = Field(default={}, description="Custom request cookies.")
    proxy: Optional[str] = Field(None, description="Proxy for requests (http/https/socks5).", max_length=200)


class MutateRequest(BaseModel):
    words: list[str] = Field(..., description="Words to mutate.", min_length=1)
    enable_leet: bool = Field(True, description="Enable l33t speak mutations.")
    enable_uppercase: bool = Field(True, description="Enable uppercase/case mutations.")
    enable_reverse_leet: bool = Field(False, description="Convert l33t chars back to letters.")
    enable_common_subs: bool = Field(False, description="Substitute common aliases (e.g. password -> passwd).")
    enable_numbers: bool = Field(True, description="Enable number suffix mutations.")
    enable_special: bool = Field(False, description="Enable special character mutations.")
    leet_level: int = Field(1, description="L33t speak intensity (1=basic, 2=advanced).", ge=1, le=2)
    prepend: Optional[str] = Field(None, description="Prepend this string to every word.", max_length=50)
    append: Optional[str] = Field(None, description="Append this string to every word.", max_length=50)
    enable_case_perms: bool = Field(False, description="Generate all case permutations of each word.")
    case_perm_max: int = Field(8, description="Max word length for case permutations (2^n variants).", ge=2, le=16)
    enable_random_combine: bool = Field(
        False, description="Bind random pairs of words in random case/l33t forms."
    )
    random_combine_count: int = Field(
        1000, description="Number of random pair combinations to generate.", ge=1, le=1000000
    )
    random_combine_seed: Optional[int] = Field(
        None, description="Seed for reproducible random combinations. Empty = random each run."
    )


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    type: JobType
    status: JobStatus
    progress: float = Field(ge=0.0, le=100.0)
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result_file: Optional[str] = None
    words_count: Optional[int] = None
    source_keywords: Optional[int] = None
    truncated_count: Optional[int] = None
    rule_format: Optional[str] = None


class JobListItem(BaseModel):
    job_id: str
    type: JobType
    status: JobStatus
    progress: float = Field(ge=0.0, le=100.0)
    created_at: datetime
    expires_at: datetime
    ttl_seconds: int
    file_size_bytes: Optional[int] = None


class MutateResponse(BaseModel):
    words: list[str]
    count: int
    source_count: int


class ErrorResponse(BaseModel):
    error: str
    code: str
    details: Optional[dict] = None


class WebSocketMessage(BaseModel):
    job_id: str
    status: JobStatus
    progress: float
    message: Optional[str] = None

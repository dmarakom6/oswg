"""Pydantic models for OSWG API."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


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
    enable_numbers: bool = Field(True, description="Enable number suffix mutations.")
    enable_special: bool = Field(False, description="Enable special character mutations.")
    leet_level: int = Field(1, description="L33t speak intensity (1=basic, 2=advanced).", ge=1, le=2)


class ScrapeRequest(BaseRequest):
    url: str = Field(..., description="Target URL to scrape.")
    urls: list[str] = Field(default=[], description="Additional URLs to scrape.", max_length=50)
    sitemap: bool = Field(False, description="Use sitemap.xml for page discovery.")
    max_pages: int = Field(10, description="Maximum pages to scrape.", ge=1, le=100)


class MutateRequest(BaseModel):
    words: list[str] = Field(..., description="Words to mutate.", min_length=1)
    enable_leet: bool = Field(True, description="Enable l33t speak mutations.")
    enable_numbers: bool = Field(True, description="Enable number suffix mutations.")
    enable_special: bool = Field(False, description="Enable special character mutations.")
    leet_level: int = Field(1, description="L33t speak intensity (1=basic, 2=advanced).", ge=1, le=2)


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

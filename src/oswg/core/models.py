"""Data models for OSWG Core."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class MutationType(Enum):
    """Types of word mutations."""
    LOWERCASE = "lowercase"
    UPPERCASE = "uppercase"
    CAPITALIZE = "capitalize"
    TITLE_CASE = "title_case"
    LEET_SPEAK = "leet_speak"
    REVERSE_LEET = "reverse_leet"
    ADD_NUMBERS = "add_numbers"
    ADD_SPECIAL = "add_special"
    COMMON_SUBSTITUTIONS = "common_substitutions"


@dataclass
class ScrapedContent:
    """Content extracted from a website."""
    url: str
    title: Optional[str] = None
    keywords: list[str] = field(default_factory=list)
    meta_description: Optional[str] = None
    headings: list[str] = field(default_factory=list)
    body_text: list[str] = field(default_factory=list)
    links_text: list[str] = field(default_factory=list)

    @property
    def all_words(self) -> list[str]:
        """Get all words from all sources."""
        words = []
        words.extend(self.keywords)
        if self.title:
            words.extend(self.title.split())
        if self.meta_description:
            words.extend(self.meta_description.split())
        words.extend(self.headings)
        words.extend(self.body_text)
        words.extend(self.links_text)
        return words


@dataclass
class GenerationConfig:
    """Configuration for wordlist generation."""
    target_size: int = 10000
    min_word_length: int = 3
    max_word_length: int = 32
    enable_leet: bool = True
    enable_uppercase: bool = True
    enable_numbers: bool = True
    enable_special: bool = False
    leet_level: int = 1
    common_years: list[int] = field(default_factory=lambda: [2023, 2024, 2025, 2026])
    special_chars: list[str] = field(default_factory=lambda: ["!", "@", "#", "$"])
    deduplicate: bool = True


@dataclass
class GenerationResult:
    """Result of wordlist generation."""
    words: list[str]
    source_keywords: int
    total_mutations: int
    unique_words: int
    config: GenerationConfig

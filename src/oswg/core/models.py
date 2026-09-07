"""Data models for OSWG Core."""

from dataclasses import dataclass, field
from datetime import date
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
    PREPEND = "prepend"
    APPEND = "append"
    CASE_PERMUTATIONS = "case_permutations"
    RANDOM_COMBINE = "random_combine"


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
        for heading in self.headings:
            words.extend(heading.split())
        words.extend(self.body_text)
        words.extend(self.links_text)
        return words


def default_years() -> list[int]:
    """Current year and the five years before it, most recent first."""
    year = date.today().year
    return [year - i for i in range(6)]


@dataclass
class GenerationConfig:
    """Configuration for wordlist generation."""
    target_size: int = 10000
    min_word_length: int = 3
    max_word_length: int = 32
    enable_leet: bool = True
    enable_uppercase: bool = True
    enable_reverse_leet: bool = False
    enable_numbers: bool = True
    enable_special: bool = False
    leet_level: int = 1
    common_years: list[int] = field(default_factory=default_years)
    special_chars: list[str] = field(default_factory=lambda: ["!", "@", "#", "$"])
    deduplicate: bool = True
    filter_stopwords: bool = True
    stopword_threshold: float = 0.5
    extra_stopwords: list[str] = field(default_factory=list)
    merge_words: list[str] = field(default_factory=list)
    merge_max: int = 5000
    enable_random_combine: bool = False
    random_combine_count: int = 1000
    random_combine_seed: Optional[int] = None
    ai_enabled: bool = False
    ai_provider: str = "auto"
    ai_model: Optional[str] = None
    ai_base_url: Optional[str] = None
    ai_max_words: int = 1000
    ai_words_per_word: int = 3
    ai_max_concurrency: int = 2
    ai_batch_size: int = 10
    ai_timeout: float = 30.0
    ai_detection_timeout: float = 2.0


@dataclass
class GenerationResult:
    """Result of wordlist generation."""
    words: list[str]
    source_keywords: int
    total_mutations: int
    unique_words: int
    config: GenerationConfig
    truncated_count: int = 0
    base_words: list[str] = field(default_factory=list)

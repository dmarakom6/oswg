"""OSWG Core - Oddly Specific Wordlist Generator Core Library."""

from oswg.core.generator import WordlistGenerator
from oswg.core.mutations import MutationEngine
from oswg.core.scraper import Scraper

__all__ = ["Scraper", "MutationEngine", "WordlistGenerator"]

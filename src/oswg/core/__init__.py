"""OSWG Core - Oddly Specific Wordlist Generator Core Library."""

from oswg.core.generator import WordlistGenerator
from oswg.core.mutations import MutationEngine
from oswg.core.scraper import Scraper
from oswg.core.stopwords import STOPWORDS, filter_stopwords, is_stopword

__all__ = ["Scraper", "MutationEngine", "WordlistGenerator", "STOPWORDS", "filter_stopwords", "is_stopword"]

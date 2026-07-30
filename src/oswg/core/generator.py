"""Wordlist generator that combines scraping and mutations."""

from oswg.core.models import GenerationConfig, GenerationResult, ScrapedContent
from oswg.core.mutations import MutationEngine
from oswg.core.scraper import Scraper


class WordlistGenerator:
    """Generates targeted wordlists from website content."""

    def __init__(self):
        self.scraper = Scraper()
        self.mutation_engine = MutationEngine()

    async def generate(
        self,
        url: str,
        config: GenerationConfig | None = None,
    ) -> GenerationResult:
        """Generate a wordlist from a URL."""
        if config is None:
            config = GenerationConfig()

        scraped = await self.scraper.scrape(url)
        words = self._filter_words(scraped, config)
        mutations = self.mutation_engine.generate_all_mutations(
            words,
            config={
                "enable_leet": config.enable_leet,
                "enable_uppercase": config.enable_uppercase,
                "enable_numbers": config.enable_numbers,
                "enable_special": config.enable_special,
                "leet_level": config.leet_level,
                "common_years": config.common_years,
                "special_chars": config.special_chars,
            },
        )

        if config.deduplicate:
            mutations = list(dict.fromkeys(mutations))

        mutations = mutations[: config.target_size]

        return GenerationResult(
            words=mutations,
            source_keywords=len(words),
            total_mutations=len(mutations),
            unique_words=len(set(mutations)),
            config=config,
        )

    def _filter_words(
        self, scraped: ScrapedContent, config: GenerationConfig
    ) -> list[str]:
        """Filter words based on configuration."""
        words = []
        for word in scraped.all_words:
            word_clean = word.lower().strip()
            if (
                len(word_clean) >= config.min_word_length
                and len(word_clean) <= config.max_word_length
                and word_clean.isalpha()
            ):
                words.append(word_clean)

        seen = set()
        unique_words = []
        for word in words:
            if word not in seen:
                seen.add(word)
                unique_words.append(word)

        return unique_words

    def estimate_size(self, keywords: list[str], config: GenerationConfig) -> int:
        """Estimate wordlist size before generation."""
        mutations_per_word = 1

        if config.enable_uppercase:
            mutations_per_word += 2

        if config.enable_leet:
            mutations_per_word += 2 ** config.leet_level

        if config.enable_numbers:
            mutations_per_word += len(config.common_years) * 2

        if config.enable_special:
            mutations_per_word += len(config.special_chars) * 3

        return min(len(keywords) * mutations_per_word, config.target_size)

    def export_to_file(self, result: GenerationResult, filepath: str) -> None:
        """Export wordlist to a text file."""
        with open(filepath, "w", encoding="utf-8") as f:
            for word in result.words:
                f.write(f"{word}\n")

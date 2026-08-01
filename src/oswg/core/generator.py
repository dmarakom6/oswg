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
        urls: list[str] | None = None,
        sitemap: bool = False,
    ) -> GenerationResult:
        """Generate a wordlist from a URL."""
        if config is None:
            config = GenerationConfig()

        self.scraper.min_word_length = config.min_word_length
        self.scraper.max_word_length = config.max_word_length

        if urls:
            scraped = await self.scraper.scrape_urls(urls, sitemap=sitemap)
        else:
            scraped = await self.scraper.scrape(url, sitemap=sitemap)

        words = self._filter_words(scraped, config)
        base_words = list(words)

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
                "deduplicate": config.deduplicate,
            },
        )

        if config.deduplicate:
            mutations = list(dict.fromkeys(mutations))

        if len(mutations) < config.target_size and base_words:
            mutations = self._expand_to_target(mutations, base_words, config)

        mutations = mutations[: config.target_size]

        if len(mutations) < config.target_size:
            import sys
            print(
                f"Warning: produced {len(mutations)} words (target was {config.target_size}). "
                f"Try increasing --max-pages or using --sitemap.",
                file=sys.stderr,
            )

        return GenerationResult(
            words=mutations,
            source_keywords=len(words),
            total_mutations=len(mutations),
            unique_words=len(set(mutations)),
            config=config,
        )

    def _expand_to_target(
        self,
        mutations: list[str],
        base_words: list[str],
        config: GenerationConfig,
    ) -> list[str]:
        """Apply additional mutation passes to reach target_size."""
        seen = set(mutations)
        expanded = list(mutations)
        target = config.target_size
        years = config.common_years
        special = config.special_chars

        if len(expanded) >= target:
            return expanded

        for word in base_words:
            if len(expanded) >= target:
                break

            cap_year = f"{word.title()}{years[0]}"
            if cap_year not in seen:
                seen.add(cap_year)
                expanded.append(cap_year)

            low_year = f"{word.lower()}{years[0]}"
            if low_year not in seen:
                seen.add(low_year)
                expanded.append(low_year)

            cap = f"{word.title()}{special[0]}"
            if cap not in seen:
                seen.add(cap)
                expanded.append(cap)

            low_s = f"{word.lower()}{special[0]}"
            if low_s not in seen:
                seen.add(low_s)
                expanded.append(low_s)

        if len(expanded) >= target:
            return expanded

        for word in base_words:
            if len(expanded) >= target:
                break
            leet_variations = self.mutation_engine._leet_speak(word, level=2)
            for lv in leet_variations:
                if lv not in seen and len(expanded) < target:
                    seen.add(lv)
                    expanded.append(lv)

        if len(expanded) >= target:
            return expanded

        for i, w1 in enumerate(base_words):
            if len(expanded) >= target:
                break
            for w2 in base_words[i + 1:]:
                if len(expanded) >= target:
                    break
                combo = f"{w1}{w2}"
                if combo not in seen and len(combo) <= config.max_word_length:
                    seen.add(combo)
                    expanded.append(combo)

        return expanded

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

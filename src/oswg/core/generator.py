"""Wordlist generator that combines scraping and mutations."""

import inspect
from typing import Callable

from oswg.core.models import GenerationConfig, GenerationResult, ScrapedContent
from oswg.core.mutations import MutationEngine
from oswg.core.scraper import Scraper
from oswg.core.stopwords import STOPWORDS, filter_by_frequency

ProgressCallback = Callable[[str], None]


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
        on_progress: ProgressCallback | None = None,
    ) -> GenerationResult:
        """Generate a wordlist from a URL."""
        if config is None:
            config = GenerationConfig()

        self.scraper.min_word_length = config.min_word_length
        self.scraper.max_word_length = config.max_word_length

        if urls:
            scraped = await self.scraper.scrape_urls(
                urls, sitemap=sitemap, on_progress=on_progress
            )
        else:
            scraped = await self.scraper.scrape(
                url, sitemap=sitemap, on_progress=on_progress
            )

        words, filter_stats = self._filter_words(
            scraped, config, self.scraper.page_word_sets
        )
        base_words = list(words)

        if on_progress:
            result = on_progress(
                f"Extracted {filter_stats['raw']} words; "
                f"removed {filter_stats['stopwords']} stopwords, "
                f"{filter_stats['freq']} high-frequency, "
                f"{filter_stats['length']} length/format; "
                f"{filter_stats['unique']} base words remaining"
            )
            if inspect.isawaitable(result):
                await result

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
        self,
        scraped: ScrapedContent,
        config: GenerationConfig,
        page_word_sets: list[set[str]] | None = None,
    ) -> tuple[list[str], dict[str, int]]:
        """Filter words based on configuration. Returns (words, stats)."""
        raw_count = 0
        length_filtered = 0
        words = []
        for word in scraped.all_words:
            word_clean = word.lower().strip()
            raw_count += 1
            if (
                len(word_clean) >= config.min_word_length
                and len(word_clean) <= config.max_word_length
                and word_clean.isalpha()
            ):
                words.append(word_clean)
            else:
                length_filtered += 1

        stopword_filtered = 0
        if config.filter_stopwords:
            stopwords = STOPWORDS | {w.lower() for w in config.extra_stopwords}
            filtered = []
            for w in words:
                if w in stopwords:
                    stopword_filtered += 1
                else:
                    filtered.append(w)
            words = filtered

        freq_filtered = 0
        if page_word_sets and config.stopword_threshold < 1.0:
            freq_excluded = filter_by_frequency(
                words, page_word_sets, threshold=config.stopword_threshold
            )
            filtered = []
            for w in words:
                if w in freq_excluded:
                    freq_filtered += 1
                else:
                    filtered.append(w)
            words = filtered

        seen = set()
        unique_words = []
        for word in words:
            if word not in seen:
                seen.add(word)
                unique_words.append(word)

        stats = {
            "raw": raw_count,
            "length": length_filtered,
            "stopwords": stopword_filtered,
            "freq": freq_filtered,
            "unique": len(unique_words),
        }

        return unique_words, stats

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

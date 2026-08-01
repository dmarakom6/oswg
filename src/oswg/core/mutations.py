"""Mutation engine for word transformations."""

from itertools import product

from oswg.core.models import MutationType


class MutationEngine:
    """Generates mutations of words using various transformation rules."""

    LEET_MAP = {
        "a": ["4", "@"],
        "e": ["3"],
        "i": ["1", "!"],
        "o": ["0"],
        "s": ["5", "$"],
        "t": ["7"],
        "l": ["1"],
        "g": ["9"],
        "b": ["8"],
    }

    def __init__(self):
        self.mutations = {
            MutationType.LOWERCASE: self._lowercase,
            MutationType.UPPERCASE: self._uppercase,
            MutationType.CAPITALIZE: self._capitalize,
            MutationType.TITLE_CASE: self._title_case,
            MutationType.LEET_SPEAK: self._leet_speak,
            MutationType.ADD_NUMBERS: self._add_numbers,
            MutationType.ADD_SPECIAL: self._add_special,
        }

    def mutate(
        self,
        word: str,
        mutation_types: list[MutationType] | None = None,
        numbers: list[int] | None = None,
        special_chars: list[str] | None = None,
        leet_level: int = 1,
        deduplicate: bool = True,
    ) -> list[str]:
        """Generate mutations for a word."""
        if mutation_types is None:
            mutation_types = list(self.mutations.keys())

        if numbers is None:
            numbers = [123, 2023, 2024, 2025, 2026]

        if special_chars is None:
            special_chars = ["!", "@", "#", "$"]

        results = []
        for mut_type in mutation_types:
            if mut_type in self.mutations:
                mutator = self.mutations[mut_type]
                if mut_type == MutationType.ADD_NUMBERS:
                    results.extend(mutator(word, numbers))
                elif mut_type == MutationType.ADD_SPECIAL:
                    results.extend(mutator(word, special_chars))
                elif mut_type == MutationType.LEET_SPEAK:
                    results.extend(mutator(word, leet_level))
                else:
                    results.append(mutator(word))

        if deduplicate:
            return list(set(results))
        return results

    def _lowercase(self, word: str) -> str:
        return word.lower()

    def _uppercase(self, word: str) -> str:
        return word.upper()

    def _capitalize(self, word: str) -> str:
        return word.capitalize()

    def _title_case(self, word: str) -> str:
        return word.title()

    def _leet_speak(self, word: str, level: int = 1) -> list[str]:
        """Generate leet speak variations."""
        word_lower = word.lower()
        variations = [word_lower]

        if level >= 1:
            simple_leet = word_lower
            for char, replacements in self.LEET_MAP.items():
                if char in simple_leet:
                    simple_leet = simple_leet.replace(char, replacements[0], 1)
            if simple_leet != word_lower:
                variations.append(simple_leet)

        if level >= 2:
            full_replacements = []
            for char, replacements in self.LEET_MAP.items():
                if char in word_lower:
                    for replacement in replacements:
                        full_replacements.append((char, replacement))

            if full_replacements:
                for chars_to_replace in product(full_replacements, repeat=1):
                    leet_word = word_lower
                    for char, replacement in chars_to_replace:
                        leet_word = leet_word.replace(char, replacement)
                    if leet_word != word_lower:
                        variations.append(leet_word)

        return variations

    def _add_numbers(self, word: str, numbers: list[int]) -> list[str]:
        """Add numbers to word."""
        variations = []
        for num in numbers:
            variations.append(f"{word}{num}")
            variations.append(f"{word.title()}{num}")
        return variations

    def _add_special(self, word: str, special_chars: list[str]) -> list[str]:
        """Add special characters to word."""
        variations = []
        for char in special_chars:
            variations.append(f"{word}{char}")
            variations.append(f"{char}{word}")
            variations.append(f"{word.title()}{char}")
        return variations

    def generate_all_mutations(
        self,
        words: list[str],
        config: dict | None = None,
    ) -> list[str]:
        """Generate all mutations for a list of words."""
        if config is None:
            config = {}

        all_mutations = []
        mutation_types = []

        if config.get("enable_uppercase", True):
            mutation_types.extend([
                MutationType.LOWERCASE,
                MutationType.UPPERCASE,
                MutationType.CAPITALIZE,
            ])

        if config.get("enable_leet", True):
            mutation_types.append(MutationType.LEET_SPEAK)

        if config.get("enable_numbers", True):
            mutation_types.append(MutationType.ADD_NUMBERS)

        if config.get("enable_special", False):
            mutation_types.append(MutationType.ADD_SPECIAL)

        for word in words:
            mutations = self.mutate(
                word,
                mutation_types=mutation_types,
                numbers=config.get("common_years", [2023, 2024, 2025, 2026]),
                special_chars=config.get("special_chars", ["!", "@", "#", "$"]),
                leet_level=config.get("leet_level", 1),
                deduplicate=config.get("deduplicate", True),
            )
            all_mutations.extend(mutations)

        return all_mutations

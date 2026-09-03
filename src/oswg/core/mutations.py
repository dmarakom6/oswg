"""Mutation engine for word transformations."""

from itertools import product

from oswg.core.models import MutationType, default_years


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

    REVERSE_LEET_MAP = {
        "4": "a", "@": "a", "3": "e", "1": "i", "!": "i",
        "0": "o", "5": "s", "$": "s", "7": "t", "9": "g", "8": "b",
    }

    COMMON_SUBS_MAP = {
        "password": ["passwd", "pwd"],
        "admin": ["adm", "root"],
        "administrator": ["admin"],
        "user": ["usr"],
        "username": ["uname", "user"],
        "account": ["acct"],
        "login": ["logon", "signin"],
        "authentication": ["auth"],
        "application": ["app"],
        "information": ["info"],
        "configuration": ["config"],
        "documentation": ["docs"],
        "welcome": ["wlcm"],
        "access": ["acc"],
        "network": ["net"],
        "computer": ["comp"],
    }

    def __init__(self):
        self.mutations = {
            MutationType.LOWERCASE: self._lowercase,
            MutationType.UPPERCASE: self._uppercase,
            MutationType.CAPITALIZE: self._capitalize,
            MutationType.TITLE_CASE: self._title_case,
            MutationType.LEET_SPEAK: self._leet_speak,
            MutationType.REVERSE_LEET: self._reverse_leet,
            MutationType.COMMON_SUBSTITUTIONS: self._common_substitutions,
            MutationType.ADD_NUMBERS: self._add_numbers,
            MutationType.ADD_SPECIAL: self._add_special,
            MutationType.PREPEND: self._prepend,
            MutationType.APPEND: self._append,
        }

    def mutate(
        self,
        word: str,
        mutation_types: list[MutationType] | None = None,
        numbers: list[int] | None = None,
        special_chars: list[str] | None = None,
        leet_level: int = 1,
        deduplicate: bool = True,
        enable_uppercase: bool = True,
        prefix: str = "",
        suffix: str = "",
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
                    results.extend(mutator(word, numbers, enable_uppercase))
                elif mut_type == MutationType.ADD_SPECIAL:
                    results.extend(mutator(word, special_chars, enable_uppercase))
                elif mut_type == MutationType.PREPEND:
                    results.append(mutator(word, prefix))
                elif mut_type == MutationType.APPEND:
                    results.append(mutator(word, suffix))
                elif mut_type in (
                    MutationType.LEET_SPEAK,
                    MutationType.REVERSE_LEET,
                    MutationType.COMMON_SUBSTITUTIONS,
                ):
                    results.extend(mutator(word))
                else:
                    results.append(mutator(word))

        if deduplicate:
            return list(dict.fromkeys(results))
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

    def _reverse_leet(self, word: str) -> list[str]:
        """Convert l33t characters back to letters (e.g. p@ssw0rd -> password)."""
        word_lower = word.lower()
        reversed_word = word_lower
        for leet_char, letter in self.REVERSE_LEET_MAP.items():
            reversed_word = reversed_word.replace(leet_char, letter)
        variations = [word_lower]
        if reversed_word != word_lower:
            variations.append(reversed_word)
        return variations

    def _common_substitutions(self, word: str) -> list[str]:
        """Substitute whole-word aliases (e.g. password -> passwd, pwd)."""
        word_lower = word.lower()
        variations = [word_lower]
        aliases = self.COMMON_SUBS_MAP.get(word_lower)
        if aliases:
            for alias in aliases:
                variations.append(alias)
                variations.append(alias.title())
        return variations

    def _prepend(self, word: str, prefix: str) -> str:
        """Prepend a string to a word."""
        if not prefix:
            return word
        return f"{prefix}{word}"

    def _append(self, word: str, suffix: str) -> str:
        """Append a string to a word."""
        if not suffix:
            return word
        return f"{word}{suffix}"

    def _add_numbers(
        self, word: str, numbers: list[int], enable_uppercase: bool = True
    ) -> list[str]:
        """Add numbers to word."""
        variations = []
        for num in numbers:
            variations.append(f"{word}{num}")
            if enable_uppercase:
                variations.append(f"{word.title()}{num}")
        return variations

    def _add_special(
        self, word: str, special_chars: list[str], enable_uppercase: bool = True
    ) -> list[str]:
        """Add special characters to word."""
        variations = []
        for char in special_chars:
            variations.append(f"{word}{char}")
            variations.append(f"{char}{word}")
            if enable_uppercase:
                variations.append(f"{word.title()}{char}")
        return variations

    def generate_all_mutations(
        self,
        words: list[str],
        config: dict | None = None,
        grouped: bool = False,
    ) -> list[str] | list[list[str]]:
        """Generate all mutations for a list of words.

        Returns a flat list by default, or per-word groups when
        ``grouped=True`` (each inner list is one word's mutations).
        """
        if config is None:
            config = {}

        all_mutations = []
        groups: list[list[str]] = []
        mutation_types = []

        if config.get("enable_uppercase", True):
            mutation_types.extend([
                MutationType.LOWERCASE,
                MutationType.UPPERCASE,
                MutationType.CAPITALIZE,
            ])

        if config.get("enable_leet", True):
            mutation_types.append(MutationType.LEET_SPEAK)

        if config.get("enable_reverse_leet", False):
            mutation_types.append(MutationType.REVERSE_LEET)

        if config.get("enable_common_subs", False):
            mutation_types.append(MutationType.COMMON_SUBSTITUTIONS)

        if config.get("enable_numbers", True):
            mutation_types.append(MutationType.ADD_NUMBERS)

        if config.get("enable_special", False):
            mutation_types.append(MutationType.ADD_SPECIAL)

        prefix = config.get("prefix", "")
        suffix = config.get("suffix", "")
        if prefix:
            mutation_types.append(MutationType.PREPEND)
        if suffix:
            mutation_types.append(MutationType.APPEND)

        for word in words:
            mutations = self.mutate(
                word,
                mutation_types=mutation_types,
                numbers=config.get("common_years", default_years()),
                special_chars=config.get("special_chars", ["!", "@", "#", "$"]),
                leet_level=config.get("leet_level", 1),
                deduplicate=config.get("deduplicate", True),
                enable_uppercase=config.get("enable_uppercase", True),
                prefix=prefix,
                suffix=suffix,
            )
            all_mutations.extend(mutations)
            if grouped:
                groups.append(mutations)

        return groups if grouped else all_mutations

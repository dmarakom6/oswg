"""Rule-file generator - converts a GenerationConfig into cracker rules.

Emits John the Ripper / Hashcat wordlist rules that describe the same
transformations the OSWG mutation engine would apply. For the operations
OSWG produces (case, leet, number/special suffixes) the JtR and Hashcat
command sets are 100% compatible, so a single set of lines serves both
formats - ``format`` only validates and names the output.

Each rule line is a command pipeline applied to every base word at crack
time, which is why a ~100-line rule file can generate far more candidates
than an expanded wordlist capped at ``target_size``.
"""

from __future__ import annotations

from oswg.core.models import GenerationConfig
from oswg.core.mutations import MutationEngine

VALID_FORMATS = ("jtr", "hashcat")


class RuleGenerator:
    """Convert a GenerationConfig into cracker rule lines."""

    def __init__(self, config: GenerationConfig, format: str = "jtr"):
        if format not in VALID_FORMATS:
            raise ValueError(f"Unknown rule format '{format}' (expected {VALID_FORMATS})")
        self.config = config
        self.format = format

    def generate(self) -> list[str]:
        """Return the rule lines encoding this config's mutations."""
        cfg = self.config
        rules: list[str] = []

        # Case variants
        if cfg.enable_uppercase:
            rules.extend(["l", "u", "c"])

        # L33t speak (basic and advanced)
        if cfg.enable_leet:
            rules.extend(self._leet_rules(cfg.leet_level))

        # Reverse leet
        if cfg.enable_reverse_leet:
            rules.extend(self._reverse_leet_rules())

        # Number suffixes
        if cfg.enable_numbers:
            for year in cfg.common_years:
                rules.append(self._append_digits(year))

        # Special characters
        if cfg.enable_special:
            for char in cfg.special_chars:
                rules.append(f"${char}")
                rules.append(f"^{char}")

        return rules

    def _leet_rules(self, level: int) -> list[str]:
        """Rules for l33t substitutions (each char replaced once per rule)."""
        map_ = MutationEngine.LEET_MAP
        rules = []
        # Basic: one substitution per rule (first replacement for each letter)
        for letter, replacements in map_.items():
            rules.append(f"s{letter}{replacements[0]}")
        if level >= 2:
            # Advanced: also use the secondary replacement
            for letter, replacements in map_.items():
                if len(replacements) > 1:
                    rules.append(f"s{letter}{replacements[1]}")
        return rules

    def _reverse_leet_rules(self) -> list[str]:
        """Rules to convert l33t chars back to letters."""
        return [f"s{leet}{letter}" for leet, letter in MutationEngine.REVERSE_LEET_MAP.items()]

    def _append_digits(self, number: int) -> str:
        """Append a multi-digit number via per-character $ commands."""
        return "".join(f"${d}" for d in str(number))


def generate_rules(config: GenerationConfig, format: str = "jtr") -> list[str]:
    """Convenience wrapper."""
    return RuleGenerator(config, format=format).generate()

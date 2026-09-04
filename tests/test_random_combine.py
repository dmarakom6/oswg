"""Tests for the --random-combine feature (random word-pair combinations)."""

from oswg.core.models import GenerationConfig
from oswg.core.mutations import MutationEngine

_JOINERS = {"-", "_", ".", " "}
_LEET_ALPHABET = {"4", "@", "3", "1", "!", "0", "5", "$", "7", "9", "8"}


def _core(combo: str) -> str:
    """Lowercase combo with joiners removed (keeps l33t digits/symbols)."""
    return "".join(c for c in combo.lower() if c not in _JOINERS)


def _matches_pair(pair: str, combo: str) -> bool:
    """True if combo is pair with optional l33t per char (positional 1:1)."""
    core = _core(combo)
    if len(core) < len(pair):
        return False
    i = 0
    for pc in pair:
        while i < len(core):
            c = core[i]
            i += 1
            if c == pc:
                break
            if c in MutationEngine.LEET_MAP.get(pc, []):
                break
            if c in _LEET_ALPHABET:
                continue  # l33t replacement for a later pair char
            return False
        else:
            return False
    return all(c in _LEET_ALPHABET for c in core[i:])


def _pairs_of(words: list[str]) -> set[str]:
    from itertools import permutations

    return {"".join(p) for p in permutations(words, 2)}


def test_random_combine_returns_requested_count():
    engine = MutationEngine()
    words = ["nutella", "cream", "chocolate", "hazelnut", "sugar"]
    combos = engine.random_combine(words, count=60, years=[2024], seed=7)
    assert len(combos) == 60


def test_random_combine_pairs_are_made_of_base_words():
    engine = MutationEngine()
    words = ["nutella", "cream", "chocolate", "hazelnut"]
    combos = engine.random_combine(words, count=40, seed=3)
    ordered_pairs = _pairs_of(words)
    for combo in combos:
        # combo must be a (possibly l33t-ed) form of exactly one ordered pair
        assert any(_matches_pair(pair, combo) for pair in ordered_pairs)


def test_random_combine_orders_vary():
    engine = MutationEngine()
    words = ["alice", "bob", "carol", "dave", "erin", "frank"]
    combos = engine.random_combine(words, count=300, seed=11)
    matched: set[str] = set()
    for combo in combos:
        for pair in _pairs_of(words):
            if _matches_pair(pair, combo):
                matched.add(pair)
                break
    assert "alicebob" in matched
    assert "bobalice" in matched


def test_random_combine_honors_max_word_length():
    engine = MutationEngine()
    words = ["nutella", "cream", "toast"]
    combos = engine.random_combine(words, count=8, max_word_length=14, seed=5)
    assert len(combos) == 8
    assert all(len(c) <= 14 for c in combos)
    # with a tight cap, pairs that can never fit are skipped entirely
    empty = engine.random_combine(
        ["supercalifragilistic", "antidisestablishmentarianism"],
        count=50,
        max_word_length=12,
        seed=5,
    )
    assert empty == []


def test_random_combine_deduplicates_by_default():
    engine = MutationEngine()
    words = ["nutella", "cream", "chocolate"]
    combos = engine.random_combine(words, count=500, seed=9)
    assert len(combos) == len(set(combos))


def test_random_combine_seed_is_reproducible():
    engine = MutationEngine()
    words = ["nutella", "cream", "chocolate", "hazelnut", "sugar", "toast"]
    first = engine.random_combine(words, count=200, years=[2024], seed=42)
    second = engine.random_combine(words, count=200, years=[2024], seed=42)
    assert first == second


def test_random_combine_different_seeds_differ():
    engine = MutationEngine()
    words = [
        "alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf",
        "hotel", "india", "juliet", "kilo", "lima", "mike", "november",
    ]
    first = engine.random_combine(words, count=1000, seed=1)
    second = engine.random_combine(words, count=1000, seed=2)
    assert first != second


def test_random_combine_requires_two_words():
    engine = MutationEngine()
    assert engine.random_combine(["solo"], count=10) == []
    assert engine.random_combine([], count=10) == []


def test_generation_config_defaults():
    config = GenerationConfig()
    assert config.enable_random_combine is False
    assert config.random_combine_count == 1000
    assert config.random_combine_seed is None


def test_random_combine_handles_user_cased_words():
    engine = MutationEngine()
    combos = engine.random_combine(["Nutella", "Cream"], count=10, seed=4)
    assert combos  # no crash; all lowercased internally
    for combo in combos:
        assert _matches_pair("nutellacream", combo) or _matches_pair(
            "creamnutella", combo
        )


def test_cli_mutate_random_combine():
    from typer.testing import CliRunner

    from oswg.cli import app

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "mutate",
            "nutella",
            "cream",
            "--random-combine",
            "--combine-count",
            "5",
            "--combine-seed",
            "42",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "unique mutations" in result.output


def test_cli_help_lists_random_combine():
    from typer.testing import CliRunner

    from oswg.cli import app

    runner = CliRunner()
    for command in ("generate", "mutate"):
        result = runner.invoke(app, [command, "--help"])
        assert result.exit_code == 0, result.output
        assert "--random-combine" in result.output
        assert "--combine-count" in result.output
        assert "--combine-seed" in result.output

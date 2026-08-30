"""Loading helpers for builtin and system wordlists."""

from __future__ import annotations

import gzip
from importlib.resources import files
from pathlib import Path
from typing import Iterator

BUILTIN_WORDLIST = "common-passwords.txt"

ROCKYOU_PATHS = (
    Path("/usr/share/wordlists/rockyou.txt"),
    Path("/usr/share/wordlists/rockyou.txt.gz"),
)


def iter_builtin() -> Iterator[str]:
    """Yield words from the bundled common-passwords list."""
    text = files("oswg").joinpath(f"data/{BUILTIN_WORDLIST}").read_text(encoding="utf-8")
    yield from (line.strip() for line in text.splitlines() if line.strip())


def detect_rockyou() -> Path | None:
    """Return the rockyou wordlist path if present on the system, else None."""
    for path in ROCKYOU_PATHS:
        if path.exists():
            return path
    return None


def iter_wordlist(path: Path) -> Iterator[str]:
    """Yield one word per line from a plain or gzipped text wordlist."""
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            word = line.strip()
            if word:
                yield word

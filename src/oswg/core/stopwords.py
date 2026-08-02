"""Stopword filtering for common English and web boilerplate words."""

from __future__ import annotations

from pathlib import Path

STOPWORDS: frozenset[str] = frozenset({
    # --- Pronouns ---
    "i", "me", "my", "myself", "we", "us", "our", "ours", "ourselves",
    "you", "your", "yours", "yourself", "yourselves",
    "he", "him", "his", "himself", "she", "her", "hers", "herself",
    "it", "its", "itself", "they", "them", "their", "theirs", "themselves",
    "what", "which", "who", "whom", "this", "that", "these", "those",

    # --- Articles / determiners ---
    "a", "an", "the", "all", "any", "both", "each", "every", "few",
    "more", "most", "much", "many", "some", "such", "no", "nor", "not",
    "only", "own", "same", "than", "too", "very",

    # --- Prepositions ---
    "about", "above", "across", "after", "against", "along", "among",
    "around", "at", "before", "behind", "below", "beneath", "beside",
    "between", "beyond", "by", "down", "during", "except", "for",
    "from", "in", "inside", "into", "near", "of", "off", "on",
    "onto", "out", "outside", "over", "past", "through", "throughout",
    "to", "toward", "under", "underneath", "until", "up", "upon",
    "with", "within", "without",

    # --- Conjunctions ---
    "and", "but", "or", "nor", "so", "yet", "because", "if", "when",
    "while", "although", "since", "unless", "whether",

    # --- Verbs (common) ---
    "am", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having", "do", "does", "did", "doing",
    "will", "would", "shall", "should", "can", "could", "may", "might",
    "must", "ought", "need", "dare", "used",

    # --- Adverbs / misc ---
    "again", "also", "always", "ever", "never", "now", "once",
    "here", "there", "then", "still", "even", "just", "well",

    # --- Common short words ---
    "s", "t", "don", "ain", "aren", "couldn", "didn", "doesn", "hadn",
    "hasn", "haven", "isn", "ma", "mightn", "mustn", "needn", "shan",
    "shouldn", "wasn", "weren", "won", "wouldn",

    # --- Web UI terms ---
    "page", "home", "menu", "search", "login", "logout", "signin", "signup",
    "click", "here", "there", "back", "next", "prev", "previous",
    "read", "more", "less", "close", "open", "show", "hide", "toggle",
    "submit", "cancel", "ok", "yes", "skip", "select",
    "content", "main", "sidebar", "footer", "header", "nav", "navigation",
    "loading", "error", "success", "warning", "info", "alert",
    "button", "checkbox", "radio", "input", "form", "text", "icon",
    "image", "img", "logo", "map", "media",

    # --- Common boilerplate ---
    "account", "admin", "api", "blog", "cart", "careers", "checkout",
    "contact", "cookie", "cookies", "copyright", "dashboard", "day",
    "delete", "dev", "developer", "disclaimer", "docs", "documentation",
    "download", "edit", "faq", "faqs", "feedback", "file", "first",
    "footer", "for", "form", "get", "go", "goes", "going", "good", "got",
    "had", "has", "have", "having", "header", "help", "home", "how",
    "info", "information", "into", "is", "it", "item", "jobs",
    "just", "knew", "know", "last", "legal", "like", "link", "login",
    "logo", "made", "main", "make", "makes", "making", "many", "may",
    "me", "menu", "might", "more", "most", "much", "must", "my",
    "nav", "navigation", "new", "news", "next", "no", "nor", "not",
    "notice", "now", "of", "off", "old", "on", "once", "one", "only",
    "open", "or", "other", "our", "ours", "ourselves", "out", "over",
    "own", "page", "people", "policy", "press", "prev", "previous",
    "privacy", "product", "profile", "quite", "radio", "really",
    "reserved", "reset", "rights", "same", "save", "saw", "search",
    "see", "seen", "select", "service", "services", "settings", "shall",
    "share", "she", "shop", "should", "show", "site", "sitemap", "skip",
    "so", "some", "status", "still", "store", "submit", "such", "support",
    "take", "takes", "taking", "terms", "text", "than", "that", "the",
    "their", "theirs", "them", "themselves", "then", "there", "these",
    "they", "thing", "things", "this", "those", "three", "through", "time",
    "to", "too", "took", "two", "under", "until", "up", "update", "upload",
    "us", "user", "very", "view", "was", "way", "we", "website", "well",
    "went", "were", "what", "when", "where", "which", "while", "who",
    "whom", "why", "will", "with", "would", "year", "you", "your",
    "yours", "yourself", "yourselves",
})


def is_stopword(word: str) -> bool:
    """Check if a word is a stopword."""
    return word.lower() in STOPWORDS


def filter_stopwords(words: list[str]) -> list[str]:
    """Remove stopwords from a list of words."""
    return [w for w in words if w.lower() not in STOPWORDS]


def load_stopwords_file(path: str | Path) -> frozenset[str]:
    """Load additional stopwords from a text file (one word per line)."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Stopwords file not found: {p}")

    extra: set[str] = set()
    with open(p, encoding="utf-8") as f:
        for line in f:
            word = line.strip().lower()
            if word and not word.startswith("#"):
                extra.add(word)

    return STOPWORDS | frozenset(extra)


def filter_by_frequency(
    words: list[str],
    page_word_sets: list[set[str]],
    threshold: float = 0.5,
) -> set[str]:
    """Return words that appear on more than threshold fraction of pages."""
    total = len(page_word_sets)
    if total <= 1 or threshold >= 1.0:
        return set()

    excluded: set[str] = set()
    for word in set(words):
        pages_with = sum(1 for ps in page_word_sets if word in ps)
        if pages_with / total > threshold:
            excluded.add(word)

    return excluded

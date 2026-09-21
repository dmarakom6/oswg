"""Built-in generate presets (lightweight -> extreme).

Each preset is a partial config (request-field names) merged over the
form's current values; empty fields fall back to the app defaults.
"""

PRESETS: dict[str, dict] = {
    "quick": {
        "size": 1000,
        "max_pages": 3,
        "min_length": 4,
        "enable_leet": False,
        "enable_uppercase": False,
        "enable_numbers": False,
        "enable_special": False,
        "enable_random_combine": False,
        "merge_builtin": False,
    },
    "standard": {},
    "aggressive": {
        "size": 50000,
        "max_pages": 20,
        "leet_level": 2,
        "enable_special": True,
        "enable_random_combine": True,
        "random_combine_count": 5000,
        "merge_builtin": True,
    },
    "extreme": {
        "size": 200000,
        "max_pages": 50,
        "leet_level": 2,
        "enable_special": True,
        "enable_random_combine": True,
        "random_combine_count": 20000,
        "merge_builtin": True,
        "merge_rockyou": True,
        "stopword_threshold": 0.6,
    },
}

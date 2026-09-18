"""OSWG CLI - Unified entry point for CLI and web dashboard."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.markup import escape

from oswg import __version__
from oswg.cli_utils import (
    console,
    make_verbose_callback,
    print_banner,
    print_error,
    print_info,
    print_keywords_preview,
    print_mutations_preview,
    print_result_summary,
    print_screenshots_summary,
    print_success,
    print_warning,
    save_screenshots,
)
from oswg.core import MutationEngine, WordlistGenerator
from oswg.core.export import build_metadata, infer_export, render_bytes, with_gzip_suffix, write_export
from oswg.core.models import GenerationConfig, default_years
from oswg.core.stopwords import load_stopwords_file

app = typer.Typer(
    name="oswg",
    help="Oddly Specific Wordlist Generator - Generate targeted wordlists from website content.",
    no_args_is_help=True,
    add_completion=False,
)


def version_callback(value: bool) -> None:
    if value:
        print_banner()
        typer.echo(f"oswg {__version__}")
        raise typer.Exit()


def validate_special_chars(values: list[str] | None) -> list[str] | None:
    """Validate --special-chars values: each must be a single non-alphanumeric char."""
    if values is None:
        return None
    for value in values:
        if len(value) != 1 or value.isalnum() or value.isspace():
            raise typer.BadParameter(
                f"'{value}' is not a special character "
                "(must be a single non-alphanumeric character)"
            )
    return values


def validate_ai_provider(value: str) -> str:
    """Validate --ai-provider value."""
    if value not in ("auto", "ollama", "openai"):
        raise typer.BadParameter("must be one of: auto, ollama, openai")
    return value


def parse_headers(values: list[str] | None) -> dict[str, str] | None:
    """Parse repeatable 'Name: value' flags into a headers dict."""
    if not values:
        return None
    headers: dict[str, str] = {}
    for value in values:
        if ":" not in value:
            raise typer.BadParameter(
                f"Invalid header '{value}' (expected 'Name: value')"
            )
        name, header_value = value.split(":", 1)
        headers[name.strip()] = header_value.strip()
    return headers


def validate_rule_format(value: str | None) -> str | None:
    """Validate --rule-format value."""
    if value is not None and value.lower() not in ("jtr", "hashcat"):
        raise typer.BadParameter(
            f"Unknown rule format '{value}' (expected 'jtr' or 'hashcat')"
        )
    return value.lower() if value else None


def validate_export_format(value: str | None) -> str | None:
    """Validate --format value."""
    if value is None:
        return None
    normalized = value.lower().lstrip(".")
    if normalized not in ("txt", "json", "csv"):
        raise typer.BadParameter(
            f"Unknown format '{value}' (expected txt, json, or csv)"
        )
    return normalized


def validate_crawl_strategy(value: str) -> str:
    """Validate --crawl-strategy value."""
    if value.lower() not in ("bfs", "dfs"):
        raise typer.BadParameter(
            f"Unknown crawl strategy '{value}' (expected 'bfs' or 'dfs')"
        )
    return value.lower()


def validate_auth_type(value: str | None) -> str | None:
    """Validate --auth-type value."""
    if value is None:
        return None
    normalized = value.lower()
    if normalized not in ("basic", "digest", "ntlm"):
        raise typer.BadParameter(
            f"Unknown auth type '{value}' (expected basic, digest, or ntlm)"
        )
    return normalized


def parse_cookies(values: list[str] | None) -> dict[str, str] | None:
    """Parse repeatable 'name=value' flags into a cookies dict."""
    if not values:
        return None
    cookies: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise typer.BadParameter(
                f"Invalid cookie '{value}' (expected 'name=value')"
            )
        name, cookie_value = value.split("=", 1)
        cookies[name.strip()] = cookie_value.strip()
    return cookies


def _read_cookie_file(path: Path | None) -> list:
    """Read a Netscape cookies.txt file into parsed Cookie objects."""
    if path is None:
        return []
    if not path.exists():
        raise typer.BadParameter(f"Cookie file not found: {path}")
    from oswg.core.cookie_file import parse_cookie_file

    return parse_cookie_file(path.read_text(encoding="utf-8", errors="replace"))


def _load_session_file(path: Path | None) -> dict | None:
    """Load a Playwright storage_state JSON session file."""
    if path is None:
        return None
    if not path.exists():
        raise typer.BadParameter(f"Session file not found: {path}")
    from oswg.core.session import load_session

    try:
        return load_session(path)
    except (ValueError, OSError) as e:
        raise typer.BadParameter(f"Invalid session file: {e}") from e


def _interactive_login(
    url: str,
    timeout: float,
    user_agent: str | None,
    headers: dict[str, str] | None,
    proxy: str | None,
) -> dict:
    """Run a headed interactive login and return the captured storage state."""
    import asyncio

    from oswg.core.session import interactive_login

    try:
        return asyncio.run(
            interactive_login(
                url,
                timeout=timeout,
                user_agent=user_agent,
                headers=headers,
                proxy=proxy,
                on_prompt=print_info,
            )
        )
    except RuntimeError as e:
        print_error(str(e))
        raise typer.Exit(code=1) from e


def _resolve_session(
    session_file: Path | None,
    do_login: bool,
    url: str,
    timeout: float,
    user_agent: str | None,
    headers: dict[str, str] | None,
    proxy: str | None,
) -> dict | None:
    """Resolve a session from --login (interactive) or --session-file."""
    if do_login:
        return _interactive_login(url, timeout, user_agent, headers, proxy)
    return _load_session_file(session_file)


def _rule_output_paths(output_path: Path) -> tuple[Path, Path]:
    """Derive <stem>.rules and <stem>.base.txt from the -o path."""
    name = output_path.name
    if name.endswith(".gz"):
        name = name[:-3]
    for suffix in (".txt", ".json", ".csv"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    base = output_path.with_name(name)
    return base.with_name(base.name + ".rules"), base.with_name(base.name + ".base.txt")


def _sidecar_output_path(output_path: Path, label: str) -> Path:
    """Derive <stem>.<label>.txt from the -o path."""
    name = output_path.name
    if name.endswith(".gz"):
        name = name[:-3]
    for suffix in (".txt", ".json", ".csv"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    base = output_path.with_name(name)
    return base.with_name(f"{base.name}.{label}.txt")


def collect_merge_words(
    merge_files: list[Path] | None,
    merge_builtin: bool,
    merge_rockyou: bool,
) -> list[str]:
    """Collect external words from --merge files, builtin, and rockyou."""
    from oswg.core.wordlists import detect_rockyou, iter_builtin, iter_wordlist

    words: list[str] = []

    if merge_builtin:
        words.extend(iter_builtin())

    for path in merge_files or []:
        if not path.exists():
            print_error(f"Merge file not found: {path}")
            raise typer.Exit(code=1)
        words.extend(iter_wordlist(path))

    if merge_rockyou:
        rockyou = detect_rockyou()
        if rockyou is None:
            print_error("rockyou.txt not found (looked in /usr/share/wordlists/).")
            raise typer.Exit(code=1)
        words.extend(iter_wordlist(rockyou))

    return words


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-V",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """Oddly Specific Wordlist Generator."""


@app.command()
def generate(
    url: list[str] = typer.Argument(..., help="Target URL(s) to scrape."),
    output: Path = typer.Option("wordlist.txt", "--output", "-o", help="Output file path."),
    format: str = typer.Option(
        None, "--format",
        help="Output format: txt (default), json, csv. Inferred from the --output extension.",
        callback=validate_export_format,
    ),
    gzip_output: bool = typer.Option(
        None, "--gzip/--no-gzip",
        help="Gzip-compress the output. Inferred from a .gz --output extension.",
    ),
    size: int = typer.Option(10000, "--size", "-s", help="Target wordlist size.", min=1),
    max_pages: int = typer.Option(10, "--max-pages", "-p", help="Maximum pages to scrape.", min=1),
    min_length: int = typer.Option(3, "--min-length", help="Minimum word length.", min=1),
    max_length: int = typer.Option(32, "--max-length", help="Maximum word length.", min=1),
    no_leet: bool = typer.Option(False, "--no-leet", help="Disable l33t speak mutations."),
    reverse_leet: bool = typer.Option(False, "--reverse-leet", help="Convert l33t chars back to letters."),
    no_uppercase: bool = typer.Option(False, "--no-uppercase", help="Disable uppercase/case mutations."),
    no_numbers: bool = typer.Option(False, "--no-numbers", help="Disable number suffix mutations."),
    no_deduplicate: bool = typer.Option(False, "--no-deduplicate", help="Disable deduplication of words."),
    special: bool = typer.Option(False, "--special", help="Enable special character mutations."),
    special_chars: list[str] = typer.Option(
        None, "--special-chars",
        help="Custom special characters for mutations (default: ! @ # $). "
        "Each value must be a single special character.",
        callback=validate_special_chars,
    ),
    leet_level: int = typer.Option(1, "--leet-level", help="L33t speak intensity (1=basic, 2=advanced).", min=1, max=2),
    sitemap: bool = typer.Option(False, "--sitemap", help="Use sitemap.xml for page discovery."),
    allow_subdomains: bool = typer.Option(
        False, "--allow-subdomains",
        help="Crawl sibling subdomains of the seed (default: stay on the exact host).",
    ),
    include_path: list[str] = typer.Option(
        None, "--include-path",
        help="Only crawl paths starting with this prefix, repeatable.",
    ),
    exclude: list[str] = typer.Option(
        None, "--exclude",
        help="Skip URLs whose path contains this substring, repeatable.",
    ),
    crawl_strategy: str = typer.Option(
        "bfs", "--crawl-strategy",
        help="Link discovery order: bfs (breadth-first, default) or dfs (depth-first).",
        callback=validate_crawl_strategy,
    ),
    js_render: bool = typer.Option(
        False, "--js-render",
        help="Render pages with a real browser (JS) instead of plain HTTP. Requires 'pip install oswg[js]'.",
    ),
    emails: bool = typer.Option(
        False, "--emails",
        help="Extract email addresses found on the target and include them in the wordlist.",
    ),
    usernames: bool = typer.Option(
        False, "--username",
        help="Extract usernames found on the target to a separate sidecar list (not merged into the wordlist).",
    ),
    no_filter_stopwords: bool = typer.Option(False, "--no-filter-stopwords", help="Disable common word filtering."),
    stopword_threshold: float = typer.Option(
        0.5, "--stopword-threshold",
        help="Exclude words appearing on >N fraction of pages.",
        min=0.0, max=1.0,
    ),
    stopwords_file: Path = typer.Option(
        None, "--stopwords-file",
        help="Extra stopwords file (one per line, merged with built-in list).",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed scraping and filtering progress."),
    years: list[int] = typer.Option(
        None, "--years",
        help="Custom years for number suffix mutations (default: current year + previous 5).",
    ),
    timeout: float = typer.Option(30.0, "--timeout", help="HTTP request timeout in seconds.", min=1.0),
    respect_robots: bool = typer.Option(False, "--respect-robots", help="Respect robots.txt rules."),
    user_agent: str = typer.Option(None, "--user-agent", help="Custom User-Agent header for requests."),
    rate_limit: float = typer.Option(0.0, "--rate-limit", help="Delay between requests in seconds.", min=0.0),
    jitter: bool = typer.Option(False, "--jitter", help="Randomize delay by ±50%% (with --rate-limit)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview the generated wordlist without writing a file."),
    rule_format: str = typer.Option(
        None, "--rule-format",
        help="Emit cracker rules instead of an expanded wordlist (jtr or hashcat). "
        "Writes <output>.rules + <output>.base.txt and bypasses wordlist expansion.",
        callback=validate_rule_format,
    ),
    header: list[str] = typer.Option(None, "--header", help="Custom header, repeatable (e.g. --header 'X-Foo: bar')."),
    cookie: list[str] = typer.Option(None, "--cookie", help="Custom cookie, repeatable (e.g. --cookie 'session=abc')."),
    cookie_file: Path = typer.Option(
        None, "--cookie-file",
        help="Read session cookies from a cookies.txt file (curl -b compatible).",
    ),
    session_file: Path = typer.Option(
        None, "--session-file",
        help="Reuse a saved session (storage_state JSON) from 'oswg login'.",
    ),
    do_login: bool = typer.Option(
        False, "--login",
        help="Log in interactively in a browser before scraping. Requires 'pip install oswg[js]'.",
    ),
    proxy: str = typer.Option(None, "--proxy", help="Proxy for requests (e.g. http://127.0.0.1:8080 or socks5://127.0.0.1:9050)."),
    auth_type: str = typer.Option(
        None, "--auth-type",
        help="HTTP authentication type: basic, digest, or ntlm (ntlm requires 'pip install oswg[auth]').",
        callback=validate_auth_type,
    ),
    auth_user: str = typer.Option(None, "--auth-user", help="Username for HTTP authentication."),
    auth_pass: str = typer.Option(None, "--auth-pass", help="Password for HTTP authentication."),
    merge: list[Path] = typer.Option(
        None, "--merge",
        help="Wordlist file(s) to merge, repeatable (one word per line).",
    ),
    merge_max: int = typer.Option(5000, "--merge-max", help="Total cap on merged words.", min=1),
    merge_builtin: bool = typer.Option(False, "--merge-builtin", help="Merge bundled bundled common passwords."),
    merge_rockyou: bool = typer.Option(
        False, "--merge-rockyou",
        help="Merge /usr/share/wordlists/rockyou.txt(.gz) if present.",
    ),
    random_combine: bool = typer.Option(
        False, "--random-combine",
        help="Bind random pairs of base words in random case/l33t forms "
        "(e.g. nutella + cream -> NutellaCream2024, cr4amnut3ll4).",
    ),
    combine_count: int = typer.Option(
        1000, "--combine-count",
        help="Number of random pair combinations to generate.",
        min=1,
    ),
    combine_seed: int = typer.Option(
        None, "--combine-seed",
        help="Seed for reproducible random combinations (same seed = same output).",
    ),
    ai_completions: bool = typer.Option(
        False, "--ai-completions",
        help="Expand base words with AI-generated related words "
        "(Ollama locally, or OpenAI with OPENAI_API_KEY).",
    ),
    ai_provider: str = typer.Option(
        "auto", "--ai-provider",
        help="AI provider: auto (detect local Ollama first — recommended), ollama, openai.",
        callback=validate_ai_provider,
    ),
    ai_model: str = typer.Option(
        None, "--ai-model",
        help="AI model (e.g. llama3.2, gpt-4o-mini). Empty = auto-detect.",
    ),
    ai_base_url: str = typer.Option(
        None, "--ai-base-url",
        help="OpenAI-compatible base URL override (e.g. a custom Ollama address).",
    ),
    ai_max_words: int = typer.Option(
        1000, "--ai-max-words",
        help="Cap on total AI-generated words (cost guard).",
        min=1,
    ),
    ai_words_per_word: int = typer.Option(
        3, "--ai-words-per-word",
        help="Related words requested per base word.",
        min=1, max=20,
    ),
    ai_concurrency: int = typer.Option(
        2, "--ai-concurrency",
        help="Max concurrent AI requests.",
        min=1, max=16,
    ),
    ai_timeout: float = typer.Option(
        30.0, "--ai-timeout",
        help="AI request timeout in seconds.",
        min=1.0,
    ),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output except errors."),
) -> None:
    """Generate a targeted wordlist from a website URL."""
    import asyncio

    extra_stopwords: list[str] = []
    if stopwords_file:
        loaded = load_stopwords_file(stopwords_file)
        extra_stopwords = sorted(loaded)

    config = GenerationConfig(
        target_size=size,
        min_word_length=min_length,
        max_word_length=max_length,
        enable_leet=not no_leet,
        enable_uppercase=not no_uppercase,
        enable_reverse_leet=reverse_leet,
        enable_numbers=not no_numbers,
        enable_special=special,
        leet_level=leet_level,
        common_years=years or default_years(),
        special_chars=special_chars or ["!", "@", "#", "$"],
        deduplicate=not no_deduplicate,
        filter_stopwords=not no_filter_stopwords,
        stopword_threshold=stopword_threshold,
        extra_stopwords=extra_stopwords,
        extract_emails=emails,
        extract_usernames=usernames,
        merge_words=collect_merge_words(merge, merge_builtin, merge_rockyou),
        merge_max=merge_max,
        enable_random_combine=random_combine,
        random_combine_count=combine_count,
        random_combine_seed=combine_seed,
        ai_enabled=ai_completions,
        ai_provider=ai_provider,
        ai_model=ai_model,
        ai_base_url=ai_base_url,
        ai_max_words=ai_max_words,
        ai_words_per_word=ai_words_per_word,
        ai_max_concurrency=ai_concurrency,
        ai_timeout=ai_timeout,
    )

    if ai_completions:
        if not quiet:
            print_warning(
                "AI completions send scraped base words to an AI provider. "
                "OpenAI is a paid online API — words leave your machine and you may be charged. "
                "For fully offline generation, use --ai-provider ollama (local)."
            )

        from oswg.core.ai import AIError, resolve_ai_config

        try:
            resolved = asyncio.run(
                resolve_ai_config(
                    provider=ai_provider, model=ai_model, base_url=ai_base_url
                )
            )
        except AIError as e:
            print_error(f"AI provider unavailable: {e}")
            raise typer.Exit(code=1) from e

        config.ai_provider = resolved.provider
        config.ai_model = resolved.model
        config.ai_base_url = resolved.base_url
        if not quiet:
            if resolved.provider == "ollama":
                print_info(
                    f"Detected local Ollama — fully offline generation (model: {resolved.model})."
                )
            else:
                print_info(
                    f"AI provider: OpenAI ({resolved.model}). Base words are sent to a third-party API."
                )

    generator = WordlistGenerator()
    generator.scraper.max_pages = max_pages
    generator.scraper.timeout = timeout
    generator.scraper.respect_robots = respect_robots
    generator.scraper.user_agent = user_agent
    generator.scraper.rate_limit = rate_limit
    generator.scraper.jitter = jitter
    generator.scraper.headers = parse_headers(header)
    generator.scraper.cookies = parse_cookies(cookie)
    generator.scraper.cookie_jar = _read_cookie_file(cookie_file)
    generator.scraper.allow_subdomains = allow_subdomains
    generator.scraper.include_paths = include_path
    generator.scraper.exclude_patterns = exclude
    generator.scraper.crawl_strategy = crawl_strategy
    generator.scraper.js_render = js_render
    generator.scraper.proxy = proxy

    if auth_type:
        from oswg.core.http_auth import build_auth

        generator.scraper.auth_type = auth_type
        generator.scraper.auth_user = auth_user
        generator.scraper.auth_pass = auth_pass
        generator.scraper._auth = build_auth(auth_type, auth_user, auth_pass)

    primary_url = url[0]
    extra_urls = url[1:] if len(url) > 1 else []

    session = _resolve_session(
        session_file, do_login, primary_url, timeout, user_agent,
        parse_headers(header), proxy,
    )
    if session:
        from oswg.core.session import cookies_from_session
        generator.scraper.storage_state = session
        generator.scraper.cookie_jar.extend(cookies_from_session(session))

    on_progress = make_verbose_callback() if verbose else None

    try:
        result = asyncio.run(
            generator.generate(
                primary_url,
                config,
                urls=[primary_url] + extra_urls if extra_urls else None,
                sitemap=sitemap,
                on_progress=on_progress,
            )
        )
    except Exception as e:
        print_error(str(e))
        raise typer.Exit(code=1) from e

    if not dry_run:
        screenshot_paths = save_screenshots(generator.scraper.screenshots, output.resolve())
        print_screenshots_summary(screenshot_paths, quiet=quiet)

        if result.usernames:
            usr_path = _sidecar_output_path(output.resolve(), "usernames")
            _, compress_usr = infer_export(output.resolve(), None, gzip_output)
            usr_path = with_gzip_suffix(usr_path, compress_usr)
            usr_path.parent.mkdir(parents=True, exist_ok=True)
            usr_path.write_bytes(
                render_bytes(result.usernames, "txt", compress=compress_usr)
            )
            if not quiet:
                print_success(
                    f"Saved {len(result.usernames)} usernames to {usr_path}"
                )

    if rule_format:
        output_path = output.resolve()
        _, compress_rules = infer_export(output_path, None, gzip_output)
        rules_path, base_path = _rule_output_paths(output_path)
        rules_path = with_gzip_suffix(rules_path, compress_rules)
        base_path = with_gzip_suffix(base_path, compress_rules)

        from oswg.core.rulegen import generate_rules

        rules = generate_rules(config, format=rule_format)
        base_words = result.base_words

        rules_path.parent.mkdir(parents=True, exist_ok=True)
        rules_path.write_bytes(render_bytes(rules, "txt", compress=compress_rules))
        base_path.write_bytes(render_bytes(base_words, "txt", compress=compress_rules))

        if not quiet:
            print_info(
                f"Rule mode ({rule_format}): {len(rules)} rules, "
                f"{len(base_words)} base words — wordlist expansion bypassed."
            )
            print_success(f"Rules written to {rules_path}")
            print_success(f"Base words written to {base_path}")
            hint = (
                "hashcat -a 0 <hashes> BASE_WORDS -r RULES"
                if rule_format == "hashcat"
                else "john --wordlist=BASE_WORDS --rules=RULES <hashfile>"
            )
            print_info(f"Usage hint: {hint}")
        return

    if dry_run:
        if not quiet:
            print_mutations_preview(result.words, limit=len(result.words))
            print_result_summary(
                source_keywords=result.source_keywords,
                total_mutations=result.total_mutations,
                unique_words=result.unique_words,
                output_file="(dry run — no file written)",
            )
            if result.truncated_count > 0:
                print_warning(
                    f"Truncated {result.truncated_count} mutations to reach target size ({size})."
                )
            print_info("Dry run — no file written")
        return

    output_path = output.resolve()
    metadata = build_metadata(
        version=__version__,
        source={"url": primary_url, "urls": extra_urls or None},
        stats={
            "words_count": result.unique_words,
            "source_keywords": result.source_keywords,
            "total_mutations": result.total_mutations,
            "truncated_count": result.truncated_count,
            **({"email_count": result.email_count} if result.email_count else {}),
            **({"username_count": len(result.usernames)} if result.usernames else {}),
        },
        config=config,
    )
    written_path = write_export(
        result.words, output_path, fmt=format, compress=gzip_output, metadata=metadata
    )

    if not quiet:
        print_result_summary(
            source_keywords=result.source_keywords,
            total_mutations=result.total_mutations,
            unique_words=result.unique_words,
            output_file=str(written_path),
        )
        if result.truncated_count > 0:
            print_warning(
                f"Truncated {result.truncated_count} mutations to reach target size ({size})."
            )
        print_success(f"Wordlist saved to {written_path}")


@app.command()
def scrape(
    url: list[str] = typer.Argument(..., help="Target URL(s) to scrape."),
    max_pages: int = typer.Option(10, "--max-pages", "-p", help="Maximum pages to scrape.", min=1),
    sitemap: bool = typer.Option(False, "--sitemap", help="Use sitemap.xml for page discovery."),
    allow_subdomains: bool = typer.Option(
        False, "--allow-subdomains",
        help="Crawl sibling subdomains of the seed (default: stay on the exact host).",
    ),
    include_path: list[str] = typer.Option(
        None, "--include-path",
        help="Only crawl paths starting with this prefix, repeatable.",
    ),
    exclude: list[str] = typer.Option(
        None, "--exclude",
        help="Skip URLs whose path contains this substring, repeatable.",
    ),
    crawl_strategy: str = typer.Option(
        "bfs", "--crawl-strategy",
        help="Link discovery order: bfs (breadth-first, default) or dfs (depth-first).",
        callback=validate_crawl_strategy,
    ),
    js_render: bool = typer.Option(
        False, "--js-render",
        help="Render pages with a real browser (JS) instead of plain HTTP. Requires 'pip install oswg[js]'.",
    ),
    emails: bool = typer.Option(
        False, "--emails",
        help="Extract email addresses found on the target and include them in the output.",
    ),
    usernames: bool = typer.Option(
        False, "--username",
        help="Extract usernames found on the target to a separate sidecar list.",
    ),
    output: Path = typer.Option(None, "--output", "-o", help="Save keywords to file."),
    format: str = typer.Option(
        None, "--format",
        help="Output format: txt (default), json, csv. Inferred from the --output extension.",
        callback=validate_export_format,
    ),
    gzip_output: bool = typer.Option(
        None, "--gzip/--no-gzip",
        help="Gzip-compress the output. Inferred from a .gz --output extension.",
    ),
    show_all: bool = typer.Option(False, "--all", "-a", help="Show all keywords (not just preview)."),
    timeout: float = typer.Option(30.0, "--timeout", help="HTTP request timeout in seconds.", min=1.0),
    respect_robots: bool = typer.Option(False, "--respect-robots", help="Respect robots.txt rules."),
    user_agent: str = typer.Option(None, "--user-agent", help="Custom User-Agent header for requests."),
    rate_limit: float = typer.Option(0.0, "--rate-limit", help="Delay between requests in seconds.", min=0.0),
    jitter: bool = typer.Option(False, "--jitter", help="Randomize delay by ±50%% (with --rate-limit)."),
    header: list[str] = typer.Option(None, "--header", help="Custom header, repeatable (e.g. --header 'X-Foo: bar')."),
    cookie: list[str] = typer.Option(None, "--cookie", help="Custom cookie, repeatable (e.g. --cookie 'session=abc')."),
    cookie_file: Path = typer.Option(
        None, "--cookie-file",
        help="Read session cookies from a cookies.txt file (curl -b compatible).",
    ),
    session_file: Path = typer.Option(
        None, "--session-file",
        help="Reuse a saved session (storage_state JSON) from 'oswg login'.",
    ),
    do_login: bool = typer.Option(
        False, "--login",
        help="Log in interactively in a browser before scraping. Requires 'pip install oswg[js]'.",
    ),
    proxy: str = typer.Option(None, "--proxy", help="Proxy for requests (e.g. http://127.0.0.1:8080 or socks5://127.0.0.1:9050)."),
    auth_type: str = typer.Option(
        None, "--auth-type",
        help="HTTP authentication type: basic, digest, or ntlm (ntlm requires 'pip install oswg[auth]').",
        callback=validate_auth_type,
    ),
    auth_user: str = typer.Option(None, "--auth-user", help="Username for HTTP authentication."),
    auth_pass: str = typer.Option(None, "--auth-pass", help="Password for HTTP authentication."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed scraping progress."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output except errors."),
) -> None:
    """Scrape keywords from a website URL."""
    import asyncio

    from oswg.core.scraper import Scraper

    session = _resolve_session(
        session_file, do_login, url[0], timeout, user_agent,
        parse_headers(header), proxy,
    )

    scraper = Scraper(
        max_pages=max_pages,
        timeout=timeout,
        respect_robots=respect_robots,
        user_agent=user_agent,
        rate_limit=rate_limit,
        jitter=jitter,
        headers=parse_headers(header),
        cookies=parse_cookies(cookie),
        proxy=proxy,
        allow_subdomains=allow_subdomains,
        include_paths=include_path,
        exclude_patterns=exclude,
        crawl_strategy=crawl_strategy,
        js_render=js_render,
        extract_emails=emails,
        extract_usernames=usernames,
        auth_type=auth_type,
        auth_user=auth_user,
        auth_pass=auth_pass,
        storage_state=session,
    )
    scraper.cookie_jar = _read_cookie_file(cookie_file) + scraper.cookie_jar
    on_progress = make_verbose_callback() if verbose else None

    try:
        if len(url) > 1:
            content = asyncio.run(scraper.scrape_urls(url, sitemap=sitemap, on_progress=on_progress))
        else:
            content = asyncio.run(scraper.scrape(url[0], sitemap=sitemap, on_progress=on_progress))
    except Exception as e:
        print_error(str(e))
        raise typer.Exit(code=1) from e

    keywords = content.keywords
    if emails and content.emails:
        existing = {kw.lower() for kw in keywords}
        keywords = keywords + [e for e in content.emails if e.lower() not in existing]

    seed_host = url[0].split("//")[-1].split("/")[0]
    screenshot_paths = save_screenshots(scraper.screenshots, output if output else None, stem=seed_host)
    print_screenshots_summary(screenshot_paths, quiet=quiet)

    if output:
        output_path = output.resolve()

        if content.usernames:
            usr_path = _sidecar_output_path(output_path, "usernames")
            _, compress_usr = infer_export(output_path, None, gzip_output)
            usr_path = with_gzip_suffix(usr_path, compress_usr)
            usr_path.parent.mkdir(parents=True, exist_ok=True)
            usr_path.write_bytes(
                render_bytes(content.usernames, "txt", compress=compress_usr)
            )
            if not quiet:
                print_success(
                    f"Saved {len(content.usernames)} usernames to {usr_path}"
                )

        metadata = build_metadata(
            version=__version__,
            source={
                "url": url[0],
                "urls": url[1:] or None,
                "title": content.title,
                "meta_description": content.meta_description,
            },
            stats={"keywords_count": len(keywords), "crawl_strategy": crawl_strategy,
                   **({"email_count": len(content.emails)} if content.emails else {}),
                   **({"username_count": len(content.usernames)} if content.usernames else {})},
            config={
                "max_pages": max_pages,
                "sitemap": sitemap,
                "crawl_strategy": crawl_strategy,
                "js_render": js_render,
                "respect_robots": respect_robots,
                "allow_subdomains": allow_subdomains,
                "include_paths": include_path,
                "exclude_patterns": exclude,
            },
        )
        written_path = write_export(
            keywords, output_path, fmt=format, compress=gzip_output, metadata=metadata
        )
        if not quiet:
            print_success(f"Saved {len(keywords)} keywords to {written_path}")
    else:
        if not quiet:
            if show_all:
                for kw in keywords:
                    console.print(kw)
            else:
                print_keywords_preview(keywords)
            print_info(f"Total: {len(keywords)} unique keywords extracted")
            if content.usernames:
                console.print("")
                print_info(f"Usernames ({len(content.usernames)}):")
                for u in content.usernames:
                    console.print(u)


@app.command()
def login(
    url: str = typer.Argument(..., help="URL to open for interactive login."),
    save: Path = typer.Option(
        None, "--save", "-o",
        help="Save the captured session (storage_state JSON). Prints to stdout if omitted.",
    ),
    timeout: float = typer.Option(300.0, "--timeout", help="Max seconds to wait for login.", min=1.0),
    user_agent: str = typer.Option(None, "--user-agent", help="Custom User-Agent header for the login browser."),
    header: list[str] = typer.Option(None, "--header", help="Custom header, repeatable (e.g. --header 'X-Foo: bar')."),
    proxy: str = typer.Option(None, "--proxy", help="Proxy for the login browser (http/https/socks5)."),
) -> None:
    """Open a browser to log in, then capture the authenticated session.

    Requires Playwright ('pip install oswg[js]'). Reuse the saved session with
    --session-file on generate/scrape, or paste the printed JSON into the web UI.
    """
    import asyncio
    import json

    from oswg.core.session import interactive_login, save_session

    try:
        state = asyncio.run(
            interactive_login(
                url,
                timeout=timeout,
                user_agent=user_agent,
                headers=parse_headers(header),
                proxy=proxy,
                on_prompt=print_info,
            )
        )
    except RuntimeError as e:
        print_error(str(e))
        raise typer.Exit(code=1) from e

    if save:
        path = save_session(state, save)
        print_success(f"Session saved to {path}")
        print_info("Reuse it with: --session-file " + str(save))
    else:
        console.print(json.dumps(state, indent=2))


@app.command()
def mutate(
    words: list[str] = typer.Argument(None, help="Words to mutate."),
    output: Path = typer.Option(None, "--output", "-o", help="Save mutations to file."),
    format: str = typer.Option(
        None, "--format",
        help="Output format: txt (default), json, csv. Inferred from the --output extension.",
        callback=validate_export_format,
    ),
    gzip_output: bool = typer.Option(
        None, "--gzip/--no-gzip",
        help="Gzip-compress the output. Inferred from a .gz --output extension.",
    ),
    no_leet: bool = typer.Option(False, "--no-leet", help="Disable l33t speak mutations."),
    reverse_leet: bool = typer.Option(False, "--reverse-leet", help="Convert l33t chars back to letters."),
    common_subs: bool = typer.Option(
        False, "--common-subs",
        help="Substitute common aliases (e.g. password -> passwd).",
    ),
    no_uppercase: bool = typer.Option(False, "--no-uppercase", help="Disable uppercase/case mutations."),
    no_numbers: bool = typer.Option(False, "--no-numbers", help="Disable number suffix mutations."),
    special: bool = typer.Option(False, "--special", help="Enable special character mutations."),
    leet_level: int = typer.Option(1, "--leet-level", help="L33t speak intensity (1=basic, 2=advanced).", min=1, max=2),
    prepend: str = typer.Option(None, "--prepend", help="Prepend this string to every word."),
    append: str = typer.Option(None, "--append", help="Append this string to every word."),
    case_permutations: bool = typer.Option(
        False, "--case-permutations",
        help="Generate all case permutations of each word.",
    ),
    case_perm_max: int = typer.Option(
        8, "--case-perm-max",
        help="Max word length for case permutations (2^n variants).",
        min=2, max=16,
    ),
    random_combine: bool = typer.Option(
        False, "--random-combine",
        help="Bind random pairs of words in random case/l33t forms "
        "(e.g. nutella + cream -> NutellaCream2024, cr4amnut3ll4).",
    ),
    combine_count: int = typer.Option(
        1000, "--combine-count",
        help="Number of random pair combinations to generate.",
        min=1,
    ),
    combine_seed: int = typer.Option(
        None, "--combine-seed",
        help="Seed for reproducible random combinations (same seed = same output).",
    ),
    show_all: bool = typer.Option(False, "--all", "-a", help="Show all mutations (not just preview)."),
    from_file: Path = typer.Option(None, "--file", "-f", help="Read words from a file (one per line)."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output except errors."),
) -> None:
    """Apply mutations to words."""
    input_words = list(words) if words else []

    if from_file:
        if not from_file.exists():
            print_error(f"File not found: {from_file}")
            raise typer.Exit(code=1)
        with open(from_file, encoding="utf-8") as f:
            input_words.extend(line.strip() for line in f if line.strip())

    if not input_words:
        print_error("No words provided. Pass words as arguments or use --file.")
        raise typer.Exit(code=1)

    engine = MutationEngine()
    config = {
        "enable_leet": not no_leet,
        "enable_uppercase": not no_uppercase,
        "enable_reverse_leet": reverse_leet,
        "enable_common_subs": common_subs,
        "enable_numbers": not no_numbers,
        "enable_special": special,
        "leet_level": leet_level,
        "prefix": prepend or "",
        "suffix": append or "",
        "enable_case_perms": case_permutations,
        "case_perm_max": case_perm_max,
    }

    mutations = engine.generate_all_mutations(input_words, config=config)
    mutations = list(dict.fromkeys(mutations))

    if random_combine:
        combos = engine.random_combine(
            input_words,
            count=combine_count,
            seed=combine_seed,
            deduplicate=True,
        )
        mutations = list(dict.fromkeys([*mutations, *combos]))

    if output:
        output_path = output.resolve()
        metadata = build_metadata(
            version=__version__,
            stats={"mutations_count": len(mutations), "source_count": len(input_words)},
            config={
                "enable_leet": not no_leet,
                "enable_uppercase": not no_uppercase,
                "enable_reverse_leet": reverse_leet,
                "enable_common_subs": common_subs,
                "enable_numbers": not no_numbers,
                "enable_special": special,
                "leet_level": leet_level,
                "prepend": prepend,
                "append": append,
                "case_permutations": case_permutations,
            },
        )
        written_path = write_export(
            mutations, output_path, fmt=format, compress=gzip_output, metadata=metadata
        )
        if not quiet:
            print_success(f"Saved {len(mutations)} mutations to {written_path}")
    else:
        if not quiet:
            if show_all:
                for word in mutations:
                    console.print(word)
            else:
                print_mutations_preview(mutations)
            print_info(f"{len(input_words)} words -> {len(mutations)} unique mutations")


@app.command(name="ui")
def launch_ui(
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind the server to."),
    port: int = typer.Option(8000, "--port", help="Base port for the server (auto-increments if busy)."),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't open the browser automatically."),
) -> None:
    """Launch the OSWG web dashboard."""
    from oswg.launcher import start_server

    print_info("Starting OSWG dashboard...")
    start_server(host=host, port=port, open_browser=not no_browser)


def _setup_row(label: str, spec: str, ok: bool, size_mb: int) -> None:
    mark = "[green]✓[/green]" if ok else "[red]✗[/red]"
    console.print(f"  {mark} {label}  [dim]({escape(spec)}, ~{size_mb} MB)[/dim]")


@app.command(name="setup")
def setup_cmd(
    check: bool = typer.Option(False, "--check", help="Only report status; install nothing."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Install all missing extras without prompting."),
) -> None:
    """Install optional extras (JS rendering, HTTP auth) and check test tools."""
    from oswg import setup as setup_mod

    status = setup_mod.detect()

    console.print("[bold]OSWG optional extras[/bold]")
    _setup_row("JS rendering", "oswg[js]", status["js"], setup_mod.SIZE_MB["js"])
    if status["js"]:
        _setup_row("Chromium browser", "playwright install chromium", status["chromium"], setup_mod.SIZE_MB["chromium"])
    _setup_row("HTTP auth (NTLM)", "oswg[auth]", status["auth"], setup_mod.SIZE_MB["auth"])
    console.print("")

    missing = []
    if not status["js"]:
        missing.append("js")
    elif not status["chromium"]:
        missing.append("chromium")
    if not status["auth"]:
        missing.append("auth")
    missing_mb = sum(setup_mod.SIZE_MB[k] for k in missing)

    console.print(f"[dim]Missing extras: {len(missing)} · estimated {missing_mb} MB on disk[/dim]")
    console.print(
        f"[dim]Environment: {'venv' if status['venv'] else 'system'} · "
        f"{'frozen build (pip installs unavailable)' if status['frozen'] else 'pip installs available'}[/dim]"
    )
    console.print(
        f"[dim]Test tools: hashcat {'✓' if status['hashcat'] else '✗'} · "
        f"john {'✓' if status['john'] else '✗'}[/dim]"
    )
    if not status["hashcat"]:
        console.print(f"[dim]  install with: {setup_mod.hashcat_hint()}[/dim]")

    if check:
        raise typer.Exit(code=1 if missing else 0)

    if status["frozen"]:
        print_warning("Frozen build — extras must be included at build time, not installed with pip.")
        return

    if not status["js"]:
        if yes or typer.confirm(
            f"Install 'oswg[js]' (JS rendering, ~{setup_mod.SIZE_MB['js']} MB package)?", default=False
        ):
            if setup_mod.install_js():
                status = setup_mod.detect()
    if status["js"] and not status["chromium"]:
        if yes or typer.confirm(
            f"Install the Playwright Chromium browser (~{setup_mod.SIZE_MB['chromium']} MB on disk)?",
            default=False,
        ):
            if setup_mod.install_chromium():
                status = setup_mod.detect()
    if not status["auth"]:
        if yes or typer.confirm(
            f"Install 'oswg[auth]' (NTLM support, ~{setup_mod.SIZE_MB['auth']} MB)?", default=False
        ):
            if setup_mod.install_auth():
                status = setup_mod.detect()

    console.print("")
    console.print("[bold]Result[/bold]")
    _setup_row("JS rendering", "oswg[js]", status["js"], setup_mod.SIZE_MB["js"])
    if status["js"]:
        _setup_row("Chromium browser", "playwright install chromium", status["chromium"], setup_mod.SIZE_MB["chromium"])
    _setup_row("HTTP auth (NTLM)", "oswg[auth]", status["auth"], setup_mod.SIZE_MB["auth"])


def _print_test_result(result: dict) -> None:
    from rich.table import Table

    console.print("")
    table = Table(title=f"oswg test ({result['tool']})")
    kind = result["kind"]
    if kind == "hash":
        table.add_column("Hash", style="dim")
        table.add_column("Password", style="green")
        for entry in result["entries"]:
            table.add_row(entry.get("hash", ""), entry["password"])
    elif kind == "login":
        table.add_column("User", style="cyan")
        table.add_column("Password", style="green")
        for entry in result["entries"]:
            table.add_row(entry["user"], entry["password"])
    elif kind == "path":
        table.add_column("Path", style="cyan")
        table.add_column("Status", style="yellow")
        for entry in result["entries"]:
            table.add_row(entry["path"], entry["status"])
    elif kind == "key":
        table.add_column("Key", style="green")
        for entry in result["entries"]:
            table.add_row(entry["key"])
    console.print(table)
    print_info(f"Found {result['found']}")


@app.command(name="test")
def test_cmd(
    wordlist: Path = typer.Argument(..., help="Wordlist to test (or the .base.txt from --rule-format)."),
    tool: str = typer.Option(
        ...,
        "--tool",
        help="Tool to run: hashcat, john, hydra, medusa, ncrack, gobuster, aircrack-ng.",
    ),
    hashes: Path = typer.Option(None, "--hashes", help="Hash file (hashcat/john)."),
    mode: int = typer.Option(None, "--mode", help="Hashcat hash mode (e.g. 0=MD5, 1000=NTLM)."),
    rules: Path = typer.Option(None, "--rules", help="Cracker rules file (from --rule-format)."),
    users: Path = typer.Option(None, "--users", help="Usernames file (hydra/medusa/ncrack)."),
    host: str = typer.Option(None, "--host", help="Target host (hydra/medusa/ncrack)."),
    service: str = typer.Option(None, "--service", help="Service, e.g. ssh (hydra/medusa/ncrack)."),
    url: str = typer.Option(None, "--url", help="Base URL (gobuster)."),
    capture: Path = typer.Option(None, "--capture", help="PCAP capture file (aircrack-ng)."),
) -> None:
    """Test a wordlist against a target with an external cracking tool."""
    from oswg.core.test_runner import TestToolError, run

    inputs = {
        "wordlist": wordlist,
        "hashes": hashes,
        "mode": mode,
        "rules": rules,
        "users": users,
        "host": host,
        "service": service,
        "url": url,
        "capture": capture,
    }
    try:
        result = run(tool, inputs, on_line=lambda line: console.print(line, end=""))
    except TestToolError as e:
        print_error(str(e))
        raise typer.Exit(code=1) from e
    _print_test_result(result)


if __name__ == "__main__":
    app()

"""OSWG CLI - Unified entry point for CLI and web dashboard."""

from __future__ import annotations

from pathlib import Path

import typer

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
    print_success,
    print_warning,
)
from oswg.core import MutationEngine, WordlistGenerator
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
    header: list[str] = typer.Option(None, "--header", help="Custom header, repeatable (e.g. --header 'X-Foo: bar')."),
    cookie: list[str] = typer.Option(None, "--cookie", help="Custom cookie, repeatable (e.g. --cookie 'session=abc')."),
    proxy: str = typer.Option(None, "--proxy", help="Proxy for requests (e.g. http://127.0.0.1:8080 or socks5://127.0.0.1:9050)."),
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
        merge_words=collect_merge_words(merge, merge_builtin, merge_rockyou),
        merge_max=merge_max,
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
    generator.scraper.proxy = proxy

    primary_url = url[0]
    extra_urls = url[1:] if len(url) > 1 else []

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

    if not quiet:
        if dry_run:
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
        generator.export_to_file(result, str(output_path))

        print_result_summary(
            source_keywords=result.source_keywords,
            total_mutations=result.total_mutations,
            unique_words=result.unique_words,
            output_file=str(output_path),
        )
        if result.truncated_count > 0:
            print_warning(
                f"Truncated {result.truncated_count} mutations to reach target size ({size})."
            )
        print_success(f"Wordlist saved to {output_path}")


@app.command()
def scrape(
    url: list[str] = typer.Argument(..., help="Target URL(s) to scrape."),
    max_pages: int = typer.Option(10, "--max-pages", "-p", help="Maximum pages to scrape.", min=1),
    sitemap: bool = typer.Option(False, "--sitemap", help="Use sitemap.xml for page discovery."),
    output: Path = typer.Option(None, "--output", "-o", help="Save keywords to file."),
    show_all: bool = typer.Option(False, "--all", "-a", help="Show all keywords (not just preview)."),
    timeout: float = typer.Option(30.0, "--timeout", help="HTTP request timeout in seconds.", min=1.0),
    respect_robots: bool = typer.Option(False, "--respect-robots", help="Respect robots.txt rules."),
    user_agent: str = typer.Option(None, "--user-agent", help="Custom User-Agent header for requests."),
    rate_limit: float = typer.Option(0.0, "--rate-limit", help="Delay between requests in seconds.", min=0.0),
    jitter: bool = typer.Option(False, "--jitter", help="Randomize delay by ±50%% (with --rate-limit)."),
    header: list[str] = typer.Option(None, "--header", help="Custom header, repeatable (e.g. --header 'X-Foo: bar')."),
    cookie: list[str] = typer.Option(None, "--cookie", help="Custom cookie, repeatable (e.g. --cookie 'session=abc')."),
    proxy: str = typer.Option(None, "--proxy", help="Proxy for requests (e.g. http://127.0.0.1:8080 or socks5://127.0.0.1:9050)."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed scraping progress."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output except errors."),
) -> None:
    """Scrape keywords from a website URL."""
    import asyncio

    from oswg.core.scraper import Scraper

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
    )
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

    if output:
        output_path = output.resolve()
        with open(output_path, "w", encoding="utf-8") as f:
            for kw in keywords:
                f.write(f"{kw}\n")
        if not quiet:
            print_success(f"Saved {len(keywords)} keywords to {output_path}")
    else:
        if not quiet:
            if show_all:
                for kw in keywords:
                    console.print(kw)
            else:
                print_keywords_preview(keywords)
            print_info(f"Total: {len(keywords)} unique keywords extracted")


@app.command()
def mutate(
    words: list[str] = typer.Argument(None, help="Words to mutate."),
    output: Path = typer.Option(None, "--output", "-o", help="Save mutations to file."),
    no_leet: bool = typer.Option(False, "--no-leet", help="Disable l33t speak mutations."),
    reverse_leet: bool = typer.Option(False, "--reverse-leet", help="Convert l33t chars back to letters."),
    no_uppercase: bool = typer.Option(False, "--no-uppercase", help="Disable uppercase/case mutations."),
    no_numbers: bool = typer.Option(False, "--no-numbers", help="Disable number suffix mutations."),
    special: bool = typer.Option(False, "--special", help="Enable special character mutations."),
    leet_level: int = typer.Option(1, "--leet-level", help="L33t speak intensity (1=basic, 2=advanced).", min=1, max=2),
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
        "enable_numbers": not no_numbers,
        "enable_special": special,
        "leet_level": leet_level,
    }

    mutations = engine.generate_all_mutations(input_words, config=config)
    mutations = list(dict.fromkeys(mutations))

    if output:
        output_path = output.resolve()
        with open(output_path, "w", encoding="utf-8") as f:
            for word in mutations:
                f.write(f"{word}\n")
        if not quiet:
            print_success(f"Saved {len(mutations)} mutations to {output_path}")
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


if __name__ == "__main__":
    app()

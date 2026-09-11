"""CLI output utilities - shared between CLI and UI launcher."""

from pathlib import Path
from typing import Callable

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

console = Console()
error_console = Console(stderr=True)


def get_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    )


def make_verbose_callback() -> Callable[[str], None]:
    """Return a callback that prints detailed progress messages."""
    def _on_progress(message: str) -> None:
        console.print(f"[dim]▸[/dim] {message}")

    return _on_progress


def print_banner() -> None:
    """Print the OSWG banner."""
    banner = r"""[bold cyan]
    ▗▄▖  ▗▄▄▖ ▗▄▄▖▗▖ ▗▖
   ▐▌ ▐▌▐▌   ▐▌   ▐▌ ▐▌
   ▐▌ ▐▌ ▝▀▚▖▐▌▝▜▌▐▌ ▐▌
   ▝▚▄▞▘▗▄▄▞▘▝▚▄▞▘▐▙█▟▌
[/bold cyan]"""
    console.print(banner)


def print_result_summary(source_keywords: int, total_mutations: int, unique_words: int, output_file: str) -> None:
    table = Table(title="Generation Results", show_header=False)
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value", style="bold white")
    table.add_row("Source keywords", str(source_keywords))
    table.add_row("Total mutations", str(total_mutations))
    table.add_row("Unique words", str(unique_words))
    table.add_row("Output file", output_file)
    console.print(table)


def print_keywords_preview(keywords: list[str], limit: int = 20) -> None:
    preview = keywords[:limit]
    table = Table(title=f"Extracted Keywords (showing {len(preview)}/{len(keywords)})")
    table.add_column("#", style="dim", width=4)
    table.add_column("Keyword", style="green")
    for i, kw in enumerate(preview, 1):
        table.add_row(str(i), kw)
    console.print(table)


def print_mutations_preview(words: list[str], limit: int = 30) -> None:
    preview = words[:limit]
    table = Table(title=f"Mutations (showing {len(preview)}/{len(words)})")
    table.add_column("#", style="dim", width=4)
    table.add_column("Word", style="yellow")
    for i, word in enumerate(preview, 1):
        table.add_row(str(i), word)
    console.print(table)


def print_error(message: str) -> None:
    error_console.print(f"[bold red]Error:[/bold red] {message}")


def print_warning(message: str) -> None:
    console.print(f"[bold yellow]Warning:[/bold yellow] {message}")


def print_success(message: str) -> None:
    console.print(f"[bold green]OK[/bold green] {message}")


def print_info(message: str) -> None:
    console.print(f"[bold cyan]--[/bold cyan] {message}")


def save_screenshots(
    screenshots: list[bytes | None],
    base_path: Path | None,
    stem: str = "page",
) -> list[Path]:
    """Save rendered-page screenshots next to ``base_path`` (or ./screenshots).

    Returns the list of written file paths.
    """
    if not screenshots:
        return []

    if base_path is not None:
        target_dir = base_path.parent / "screenshots"
        file_stem = base_path.stem
    else:
        target_dir = Path("screenshots")
        file_stem = stem
    target_dir.mkdir(parents=True, exist_ok=True)

    paths: list[Path] = []
    for i, png in enumerate(screenshots):
        if png is None:
            continue
        path = target_dir / f"{file_stem}.shot-{i}.png"
        path.write_bytes(png)
        paths.append(path)
    return paths


def print_screenshots_summary(paths: list[Path], quiet: bool = False) -> None:
    """Report saved screenshot locations."""
    if not paths or quiet:
        return
    print_success(f"Saved {len(paths)} rendered-page screenshot{'s' if len(paths) != 1 else ''} to {paths[0].parent}/")
    for path in paths:
        print_info(str(path))

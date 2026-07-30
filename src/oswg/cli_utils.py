"""CLI output utilities - shared between CLI and UI launcher."""

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


def print_success(message: str) -> None:
    console.print(f"[bold green]OK[/bold green] {message}")


def print_info(message: str) -> None:
    console.print(f"[bold cyan]--[/bold cyan] {message}")

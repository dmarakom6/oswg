"""File manager service - handles file storage and cleanup."""

from pathlib import Path

from oswg.config import settings


class FileManager:
    """Manages file storage and automatic cleanup."""

    def __init__(self, storage_path: Path | None = None):
        self.storage_path = storage_path or settings.file_storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def get_file_path(self, job_id: str, extension: str = ".txt") -> Path:
        """Get the file path for a job."""
        return self.storage_path / f"{job_id}{extension}"

    def save_words(self, job_id: str, words: list[str]) -> Path:
        """Save a wordlist to file."""
        file_path = self.get_file_path(job_id)
        with open(file_path, "w", encoding="utf-8") as f:
            for word in words:
                f.write(f"{word}\n")
        return file_path

    def save_rules(self, job_id: str, rules: list[str], base_words: list[str]) -> Path:
        """Save a cracker rules file plus its companion base-words file.

        Writes <job_id>.rules and <job_id>.base.txt; returns the rules path.
        """
        rules_path = self.get_file_path(job_id, ".rules")
        base_path = self.get_file_path(job_id, ".base.txt")
        with open(rules_path, "w", encoding="utf-8") as f:
            f.write("\n".join(rules) + "\n")
        with open(base_path, "w", encoding="utf-8") as f:
            f.write("\n".join(base_words) + "\n")
        return rules_path

    def save_usernames(self, job_id: str, usernames: list[str]) -> Path:
        """Save extracted usernames to <job_id>.usernames.txt."""
        file_path = self.get_file_path(job_id, ".usernames.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(usernames) + ("\n" if usernames else ""))
        return file_path

    def save_word_counts(self, job_id: str, counts: dict[str, int]) -> Path:
        """Save a word -> count mapping to <job_id>.word-counts.json."""
        import json

        file_path = self.get_file_path(job_id, ".word-counts.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(counts, f)
        return file_path

    def save_mutation_tree(self, job_id: str, tree: dict[str, list[str]]) -> Path:
        """Save a base-word -> variants mapping to <job_id>.mutation-tree.json."""
        import json

        file_path = self.get_file_path(job_id, ".mutation-tree.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(tree, f)
        return file_path

    def save_json(self, job_id: str, data: dict) -> Path:
        """Save JSON data to file."""
        import json

        file_path = self.get_file_path(job_id, ".json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return file_path

    def save_graph(self, job_id: str, link_graph: dict[str, list[str]]) -> Path:
        """Save a crawl graph (url -> children) as JSON."""
        return self.save_json(job_id, {"link_graph": link_graph})

    def save_screenshot(self, job_id: str, page_index: int, png_bytes: bytes) -> Path:
        """Save a rendered-page screenshot as PNG."""
        file_path = self.get_file_path(job_id, f".shot-{page_index}.png")
        with open(file_path, "wb") as f:
            f.write(png_bytes)
        return file_path

    def screenshot_count(self, job_id: str) -> int:
        """Count saved screenshots for a job."""
        count = 0
        while self.get_file_path(job_id, f".shot-{count}.png").exists():
            count += 1
        return count

    def get_screenshot_path(self, job_id: str, page_index: int) -> Path | None:
        """Return the path for a job's page screenshot, or None."""
        path = self.get_file_path(job_id, f".shot-{page_index}.png")
        return path if path.exists() else None

    def file_exists(self, job_id: str, extension: str = ".txt") -> bool:
        """Check if a file exists."""
        return self.get_file_path(job_id, extension).exists()

    def delete_file(self, job_id: str, extension: str = ".txt") -> bool:
        """Delete a file."""
        file_path = self.get_file_path(job_id, extension)
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def get_file_size(self, job_id: str, extension: str = ".txt") -> int:
        """Get file size in bytes."""
        file_path = self.get_file_path(job_id, extension)
        if file_path.exists():
            return file_path.stat().st_size
        return 0

    def cleanup_all(self) -> int:
        """Delete all files in storage."""
        count = 0
        for file_path in self.storage_path.iterdir():
            if file_path.is_file():
                file_path.unlink()
                count += 1
        return count

    def get_storage_stats(self) -> dict:
        """Get storage statistics."""
        total_files = 0
        total_size = 0

        for file_path in self.storage_path.iterdir():
            if file_path.is_file():
                total_files += 1
                total_size += file_path.stat().st_size

        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "storage_path": str(self.storage_path),
        }


file_manager = FileManager()

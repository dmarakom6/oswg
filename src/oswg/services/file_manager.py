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

    def save_json(self, job_id: str, data: dict) -> Path:
        """Save JSON data to file."""
        import json

        file_path = self.get_file_path(job_id, ".json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return file_path

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

"""Wordlist export rendering: txt, json (with metadata), csv, optional gzip."""

from __future__ import annotations

import csv
import gzip
import io
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path

FORMATS = ("txt", "json", "csv")

# Config keys that must never leak into exported metadata.
SECRET_KEYS = frozenset(
    {"storage_state", "cookie_file", "cookies", "headers", "proxy", "auth_pass"}
)

# Large list keys reduced to a count so exports stay small.
LIST_COUNT_KEYS = frozenset({"merge_words"})

MEDIA_TYPES = {
    "txt": "text/plain; charset=utf-8",
    "json": "application/json",
    "csv": "text/csv; charset=utf-8",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sanitize_config(config: dict | None) -> dict:
    """Drop auth secrets; replace large lists with counts."""
    if not config:
        return {}
    out: dict = {}
    for key, value in config.items():
        if key in SECRET_KEYS:
            continue
        if key in LIST_COUNT_KEYS:
            base = key[:-6] if key.endswith("_words") else key
            out[f"{base}_count"] = len(value or [])
            continue
        out[key] = value
    return out


def build_metadata(
    *,
    version: str,
    created_at: str | None = None,
    completed_at: str | None = None,
    job_id: str | None = None,
    job_type: str | None = None,
    source: dict | None = None,
    stats: dict | None = None,
    config: dict | None = None,
) -> dict:
    """Assemble the metadata block embedded in JSON exports."""
    metadata: dict = {
        "generator": "oswg",
        "version": version,
        "created_at": created_at or _now_iso(),
    }
    if completed_at:
        metadata["completed_at"] = completed_at
    if job_id:
        metadata["job_id"] = job_id
    if job_type:
        metadata["job_type"] = job_type
    if source:
        metadata["source"] = source
    metadata["stats"] = stats or {}
    if config is not None:
        if is_dataclass(config):
            config = asdict(config)
        metadata["options"] = sanitize_config(config)
    return metadata


def compress_bytes(data: bytes) -> bytes:
    """Gzip-compress bytes deterministically (mtime=0)."""
    return gzip.compress(data, mtime=0)


def render_bytes(
    words: list[str],
    fmt: str = "txt",
    metadata: dict | None = None,
    compress: bool = False,
    extra: dict | None = None,
) -> bytes:
    """Render words to bytes in the requested format, optionally gzipped.

    ``extra`` (dict) is merged into the top level of JSON exports only.
    """
    if fmt not in FORMATS:
        raise ValueError(f"Unknown export format '{fmt}' (expected one of: {', '.join(FORMATS)})")

    if fmt == "json":
        payload = {"metadata": metadata or {}, "words": list(words)}
        if extra:
            payload.update(extra)
        text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    elif fmt == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(["word"])
        for word in words:
            writer.writerow([word])
        text = buffer.getvalue()
    else:
        text = "".join(f"{word}\n" for word in words)

    data = text.encode("utf-8")
    if compress:
        data = compress_bytes(data)
    return data


def infer_export(
    path: Path,
    fmt: str | None = None,
    compress: bool | None = None,
) -> tuple[str, bool]:
    """Infer (format, gzip) from a filename, with explicit args as overrides."""
    name = Path(path).name.lower()
    inferred_gzip = name.endswith(".gz")
    if inferred_gzip:
        name = name[:-3]

    if fmt is None:
        if name.endswith(".json"):
            fmt = "json"
        elif name.endswith(".csv"):
            fmt = "csv"
        else:
            fmt = "txt"
    if compress is None:
        compress = inferred_gzip
    return fmt, compress


def write_export(
    words: list[str],
    path: Path,
    fmt: str | None = None,
    compress: bool | None = None,
    metadata: dict | None = None,
) -> Path:
    """Write an export to disk, inferring format/compression from the path.

    Returns the path actually written (adds a .gz suffix when compressing).
    """
    path = Path(path)
    resolved_fmt, resolved_gzip = infer_export(path, fmt, compress)
    data = render_bytes(words, resolved_fmt, metadata, resolved_gzip)
    final_path = with_gzip_suffix(path, resolved_gzip)
    final_path.parent.mkdir(parents=True, exist_ok=True)
    final_path.write_bytes(data)
    return final_path


def with_gzip_suffix(path: Path, compress: bool) -> Path:
    """Append .gz when compressing, unless already present."""
    if compress and not path.name.endswith(".gz"):
        return path.with_name(path.name + ".gz")
    return path

"""Save/load user job templates (a JSON file in the data dir)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from oswg.config import settings

# Session-specific secrets that must not be persisted in templates.
SECRET_KEYS = frozenset({"auth_pass", "cookies", "cookie_file", "storage_state"})


class TemplateStore:
    def __init__(self, path: Optional[Path] = None):
        self.path = path or (settings.data_dir / "templates.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text())
        except (ValueError, OSError):
            return {}

    def _save(self, data: dict) -> None:
        self.path.write_text(json.dumps(data, indent=2))

    def list(self) -> list[dict]:
        data = self._load()
        return [
            {
                "name": name,
                "type": record.get("type"),
                "created_at": record.get("created_at"),
            }
            for name, record in data.items()
        ]

    def get(self, name: str) -> Optional[dict]:
        return self._load().get(name)

    def save(self, name: str, type_: str, config: dict) -> dict:
        """Persist a template, dropping session secrets from the config."""
        clean = {k: v for k, v in config.items() if k not in SECRET_KEYS}
        created_at = datetime.utcnow().isoformat()
        data = self._load()
        data[name] = {"type": type_, "created_at": created_at, "config": clean}
        self._save(data)
        return {"name": name, "type": type_, "created_at": created_at}

    def delete(self, name: str) -> bool:
        data = self._load()
        if name not in data:
            return False
        del data[name]
        self._save(data)
        return True


template_store = TemplateStore()

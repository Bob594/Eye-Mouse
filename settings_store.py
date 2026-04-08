from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SettingsStore:
    def __init__(self, path: str = "settings/user_settings.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self, defaults: dict[str, Any]) -> dict[str, Any]:
        if not self.path.exists():
            return dict(defaults)
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            merged = dict(defaults)
            merged.update(data)
            return merged
        except Exception:
            return dict(defaults)

    def save(self, settings: dict[str, Any]) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)

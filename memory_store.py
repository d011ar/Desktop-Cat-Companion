import json
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parent / "data"


class MemoryStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or DATA_DIR / "memory.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, Any] = self._load()

    def get_context(self) -> str:
        if not self._data:
            return ""

        lines = []
        for key, value in sorted(self._data.items()):
            lines.append(f"- {key}: {value}")
        return "Known user memories:\n" + "\n".join(lines)

    def remember(self, key: str, value: str) -> None:
        key = key.strip()
        value = value.strip()
        if not key or not value:
            return

        self._data[key] = value
        self._save()

    def all_memories(self) -> dict[str, Any]:
        return dict(self._data)

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (OSError, json.JSONDecodeError):
            pass
        return {}

    def _save(self) -> None:
        self.path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

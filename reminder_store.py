import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from memory_store import DATA_DIR


@dataclass
class Reminder:
    id: str
    text: str
    kind: str
    created_at: str
    trigger_at: str | None = None
    completed: bool = False
    notified: bool = False

    @property
    def is_reminder(self) -> bool:
        return self.kind == "reminder"

    @property
    def trigger_datetime(self) -> datetime | None:
        if not self.trigger_at:
            return None
        try:
            return datetime.fromisoformat(self.trigger_at)
        except ValueError:
            return None


class ReminderStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or DATA_DIR / "reminders.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._items: list[Reminder] = self._load()

    def add_reminder(self, text: str, trigger_at: datetime) -> Reminder:
        item = Reminder(
            id=self._new_id(),
            text=text.strip(),
            kind="reminder",
            created_at=datetime.now().isoformat(timespec="seconds"),
            trigger_at=trigger_at.isoformat(timespec="seconds"),
        )
        self._items.append(item)
        self._save()
        return item

    def add_todo(self, text: str) -> Reminder:
        item = Reminder(
            id=self._new_id(),
            text=text.strip(),
            kind="todo",
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._items.append(item)
        self._save()
        return item

    def due_reminders(self, now: datetime) -> list[Reminder]:
        due = []
        for item in self._items:
            trigger_at = item.trigger_datetime
            if (
                item.is_reminder
                and trigger_at is not None
                and trigger_at <= now
                and not item.completed
                and not item.notified
            ):
                item.notified = True
                due.append(item)
        if due:
            self._save()
        return due

    def list_open(self) -> list[Reminder]:
        return [item for item in self._items if not item.completed]

    def list_all(self) -> list[Reminder]:
        return list(self._items)

    def complete(self, id: str) -> None:
        for item in self._items:
            if item.id == id:
                item.completed = True
                self._save()
                return

    def delete(self, id: str) -> None:
        before = len(self._items)
        self._items = [item for item in self._items if item.id != id]
        if len(self._items) != before:
            self._save()

    def clear_completed(self) -> None:
        before = len(self._items)
        self._items = [item for item in self._items if not item.completed]
        if len(self._items) != before:
            self._save()

    def _load(self) -> list[Reminder]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                return []
            return [Reminder(**item) for item in raw if isinstance(item, dict)]
        except (OSError, TypeError, json.JSONDecodeError):
            return []

    def _save(self) -> None:
        data = [asdict(item) for item in self._items]
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _new_id() -> str:
        return uuid.uuid4().hex[:10]

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from llm_client import CatLLMClient
from memory_store import MemoryStore
from reminder_store import Reminder, ReminderStore


VALID_INTENTS = {
    "chat",
    "reminder",
    "todo",
    "memory",
    "list_tasks",
    "list_memory",
    "unknown",
}


@dataclass
class AgentResult:
    reply: str
    intent: str
    changed: bool = False
    used_fallback: bool = False


@dataclass
class ParsedIntent:
    intent: str = "unknown"
    content: str = ""
    delay_seconds: int | None = None
    datetime: str | None = None
    memory_key: str = ""
    memory_value: str = ""
    confidence: float = 0.0
    clarification: str = ""
    user_reply: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ParsedIntent | None":
        intent = str(data.get("intent", "unknown")).strip().lower()
        if intent not in VALID_INTENTS:
            return None

        return cls(
            intent=intent,
            content=str(data.get("content") or "").strip(),
            delay_seconds=_coerce_delay(data.get("delay_seconds")),
            datetime=_coerce_optional_string(data.get("datetime")),
            memory_key=str(data.get("memory_key") or "").strip(),
            memory_value=str(data.get("memory_value") or "").strip(),
            confidence=_coerce_confidence(data.get("confidence")),
            clarification=str(data.get("clarification") or "").strip(),
            user_reply=str(data.get("user_reply") or "").strip(),
        )


class AgentCore:
    def __init__(
        self,
        memory_store: MemoryStore | None = None,
        reminder_store: ReminderStore | None = None,
        llm_client: CatLLMClient | None = None,
    ) -> None:
        self.memory_store = memory_store or MemoryStore()
        self.reminder_store = reminder_store or ReminderStore()
        self.llm_client = llm_client or CatLLMClient()

    def handle_message(self, message: str) -> AgentResult:
        text = message.strip()
        if not text:
            return AgentResult(self._fallback_reply("empty_message"), "chat", used_fallback=True)

        now = datetime.now()
        parsed = self._parse_with_llm(text, now)
        if parsed is None:
            parsed = self._parse_basic_english_fallback(text)

        if parsed is None or parsed.intent in ("chat", "unknown"):
            result = self.llm_client.chat(text, memory_context=self.memory_store.get_context())
            return AgentResult(result.text, "chat", used_fallback=result.used_fallback)

        if parsed.confidence < 0.45:
            return AgentResult(
                parsed.clarification or parsed.user_reply or self._fallback_reply("unclear"),
                "unknown",
                used_fallback=True,
            )

        return self._execute_intent(parsed, text, now)

    def format_open_tasks(self, user_message: str = "") -> str:
        items = self.reminder_store.list_open()
        payload = {
            "tasks": [self._item_payload(item) for item in items],
            "task_count": len(items),
        }
        return self._compose_reply(
            event="list_tasks",
            user_message=user_message,
            payload=payload,
            fallback=self._format_task_list_english(items),
        )

    def proactive_message(self) -> str:
        hour = datetime.now().hour
        if 0 <= hour < 6:
            event = "late_night_care"
        elif 11 <= hour <= 13:
            event = "midday_care"
        elif 18 <= hour <= 22:
            event = "evening_care"
        else:
            event = "focus_break_care"

        return self._compose_reply(
            event=event,
            user_message="",
            payload={"local_hour": hour},
            fallback="Meow, you have been focused for a while. Maybe take a small break?",
        )

    def reminder_due_message(self, item: Reminder) -> str:
        return self._compose_reply(
            event="reminder_due",
            user_message="",
            payload=self._item_payload(item),
            fallback=f"Meow, reminder time: {item.text}",
        )

    def _parse_with_llm(self, text: str, now: datetime) -> ParsedIntent | None:
        raw = self.llm_client.parse_intent(
            text,
            now=now,
            memory_context=self.memory_store.get_context(),
        )
        return ParsedIntent.from_dict(raw) if raw else None

    def _execute_intent(self, parsed: ParsedIntent, user_message: str, now: datetime) -> AgentResult:
        if parsed.intent == "reminder":
            return self._handle_reminder(parsed, user_message, now)
        if parsed.intent == "todo":
            return self._handle_todo(parsed, user_message)
        if parsed.intent == "memory":
            return self._handle_memory(parsed, user_message)
        if parsed.intent == "list_tasks":
            return AgentResult(self.format_open_tasks(user_message), "list_tasks")
        if parsed.intent == "list_memory":
            return AgentResult(self._format_memories(user_message), "list_memory")
        return AgentResult(parsed.clarification or parsed.user_reply or self._fallback_reply("unclear"), "unknown")

    def _handle_reminder(self, parsed: ParsedIntent, user_message: str, now: datetime) -> AgentResult:
        content = parsed.content.strip()
        trigger_at = self._resolve_trigger_time(parsed, now)
        if not content or trigger_at is None:
            reply = parsed.clarification or parsed.user_reply
            if not reply:
                reply = self._compose_reply(
                    event="missing_reminder_details",
                    user_message=user_message,
                    payload={"content": content, "has_time": trigger_at is not None},
                    fallback="I can set that reminder. What exact time should I use?",
                )
            return AgentResult(reply, "reminder")

        item = self.reminder_store.add_reminder(content, trigger_at)
        reply = parsed.user_reply or self._compose_reply(
            event="reminder_created",
            user_message=user_message,
            payload=self._item_payload(item),
            fallback=f"Meow, reminder saved for {self._format_time(trigger_at)}: {item.text}",
        )
        return AgentResult(reply, "reminder", changed=True)

    def _handle_todo(self, parsed: ParsedIntent, user_message: str) -> AgentResult:
        content = parsed.content.strip()
        if not content:
            reply = parsed.clarification or parsed.user_reply or self._compose_reply(
                event="missing_todo_content",
                user_message=user_message,
                payload={},
                fallback="What would you like me to add as a todo?",
            )
            return AgentResult(reply, "todo")

        item = self.reminder_store.add_todo(content)
        reply = parsed.user_reply or self._compose_reply(
            event="todo_created",
            user_message=user_message,
            payload=self._item_payload(item),
            fallback=f"Meow, todo added: {item.text}",
        )
        return AgentResult(reply, "todo", changed=True)

    def _handle_memory(self, parsed: ParsedIntent, user_message: str) -> AgentResult:
        value = (parsed.memory_value or parsed.content).strip()
        key = (parsed.memory_key or "note").strip() or "note"
        if not value:
            reply = parsed.clarification or parsed.user_reply or self._compose_reply(
                event="missing_memory_content",
                user_message=user_message,
                payload={},
                fallback="What would you like me to remember?",
            )
            return AgentResult(reply, "memory")

        self.memory_store.remember(key, value)
        reply = parsed.user_reply or self._compose_reply(
            event="memory_saved",
            user_message=user_message,
            payload={"memory_key": key, "memory_value": value},
            fallback=f"Meow, I will remember: {value}",
        )
        return AgentResult(reply, "memory", changed=True)

    def _format_memories(self, user_message: str) -> str:
        memories = self.memory_store.all_memories()
        return self._compose_reply(
            event="list_memory",
            user_message=user_message,
            payload={"memories": memories},
            fallback=self._format_memory_list_english(memories),
        )

    def _resolve_trigger_time(self, parsed: ParsedIntent, now: datetime) -> datetime | None:
        if parsed.delay_seconds is not None:
            return now + timedelta(seconds=parsed.delay_seconds)
        if parsed.datetime:
            try:
                return datetime.fromisoformat(parsed.datetime)
            except ValueError:
                return None
        return None

    def _compose_reply(
        self,
        event: str,
        user_message: str,
        payload: dict[str, Any],
        fallback: str,
    ) -> str:
        reply = self.llm_client.compose_agent_reply(
            event=event,
            user_message=user_message,
            payload=payload,
            memory_context=self.memory_store.get_context(),
        )
        return reply or fallback

    def _parse_basic_english_fallback(self, text: str) -> ParsedIntent | None:
        lowered = text.lower().strip()
        if lowered in {"tasks", "todos", "list tasks", "show tasks", "reminders"}:
            return ParsedIntent(intent="list_tasks", confidence=0.8)
        if lowered in {"memories", "memory", "what do you remember"}:
            return ParsedIntent(intent="list_memory", confidence=0.8)
        return None

    def _item_payload(self, item: Reminder) -> dict[str, Any]:
        return {
            "id": item.id,
            "text": item.text,
            "kind": item.kind,
            "created_at": item.created_at,
            "trigger_at": item.trigger_at,
            "completed": item.completed,
            "notified": item.notified,
        }

    def _format_task_list_english(self, items: list[Reminder]) -> str:
        if not items:
            return "Meow, there are no open reminders or todos."
        lines = []
        for index, item in enumerate(items, start=1):
            label = "Reminder" if item.is_reminder else "Todo"
            when = f" at {self._format_time(item.trigger_datetime)}" if item.is_reminder else ""
            lines.append(f"{index}. [{label}{when}] {item.text}")
        return "Meow, here are your open items:\n" + "\n".join(lines)

    def _format_memory_list_english(self, memories: dict[str, Any]) -> str:
        if not memories:
            return "Meow, I do not have any saved memories yet."
        lines = [f"{key}: {value}" for key, value in sorted(memories.items())]
        return "Meow, I remember:\n" + "\n".join(lines)

    def _fallback_reply(self, event: str) -> str:
        replies = {
            "empty_message": "Meow? Did you want to say something?",
            "unclear": "Meow, I am not sure what to do with that yet.",
        }
        return replies.get(event, "Meow, I am here.")

    def _format_time(self, value: datetime | None) -> str:
        if value is None:
            return "unset time"
        return value.strftime("%Y-%m-%d %H:%M")


def _coerce_delay(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return max(0, int(float(value)))
    except (TypeError, ValueError):
        return None


def _coerce_confidence(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _coerce_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "null":
        return None
    return text

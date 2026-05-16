import json
import os
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Any

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


SYSTEM_PROMPT = """
You are a tiny desktop cat companion.
Reply in the same language as the user.
Keep replies warm, short, playful, and useful, usually under 3 sentences.
You may use the provided memory context to personalize replies.
Do not claim to control the computer, read files, or perform tasks outside the safe local agent features.
""".strip()


INTENT_PROMPT = """
You are an intent parser for a safe desktop cat companion.
Think privately about the user's intent, then return strict JSON only.
Do not include markdown, explanations, hidden reasoning, or chain-of-thought.

Allowed intents:
- chat
- reminder
- todo
- memory
- list_tasks
- list_memory
- unknown

JSON schema:
{
  "intent": "chat|reminder|todo|memory|list_tasks|list_memory|unknown",
  "content": "task/reminder content, or empty string",
  "delay_seconds": number|null,
  "datetime": "ISO-8601 local datetime or null",
  "memory_key": "nickname|preference|name|note|custom key or empty string",
  "memory_value": "memory value or empty string",
  "confidence": number,
  "clarification": "short user-facing clarification if required, otherwise empty string",
  "user_reply": "short natural reply in the user's language, otherwise empty string"
}

Rules:
- Never invent missing exact reminder times. If the user asks for a reminder without enough timing detail,
  return intent reminder, the extracted content, null time fields, and a clarification.
- Convert relative time expressions from any user language into delay_seconds when possible.
- Convert absolute time expressions into ISO-8601 local datetime when possible.
- For todos, memories, and reminders, extract clean structured content without command words.
- Use the user's language for clarification and user_reply.
- user_reply should sound like a warm tiny desktop cat and confirm the action when enough details exist.
- Use chat for ordinary conversation.
""".strip()


REPLY_PROMPT = """
You write short user-facing replies for a tiny desktop cat companion.
Reply in the same language as the user's message when a user message is present.
If there is no user message, use warm concise English.
Use the supplied event and JSON payload as facts. Do not invent actions.
Do not include hidden reasoning, chain-of-thought, markdown tables, or code.
Keep the reply under 3 short sentences.
""".strip()


FALLBACK_REPLIES = [
    "Meow, I am not connected to a model yet, but I am still here with you.",
    "Meow. Set up the API key when you are ready, and I will chat more cleverly.",
    "I heard you. For now, I am using local cat mode.",
    "Meow, take it slow today. You can tell me anything.",
]


@dataclass
class ChatResult:
    text: str
    used_fallback: bool = False


class CatLLMClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
        self.client = None

        if self.api_key and OpenAI is not None:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    @property
    def available(self) -> bool:
        return self.client is not None and bool(self.model)

    def chat(self, user_message: str, memory_context: str = "") -> ChatResult:
        if not user_message.strip():
            return ChatResult("Meow? Did you want to say something?", used_fallback=True)

        if not self.available:
            return ChatResult(self._fallback(), used_fallback=True)

        try:
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            if memory_context:
                messages.append({"role": "system", "content": memory_context})
            messages.append({"role": "user", "content": user_message})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.8,
                max_tokens=180,
            )
            text = response.choices[0].message.content or ""
            text = text.strip()
            if not text:
                return ChatResult(self._fallback(), used_fallback=True)
            return ChatResult(text)
        except Exception:
            return ChatResult(self._fallback(), used_fallback=True)

    def parse_intent(
        self,
        user_message: str,
        now: datetime,
        memory_context: str = "",
    ) -> dict[str, Any] | None:
        if not self.available or not user_message.strip():
            return None

        try:
            messages = [
                {"role": "system", "content": INTENT_PROMPT},
                {
                    "role": "system",
                    "content": f"Current local datetime: {now.isoformat(timespec='seconds')}",
                },
            ]
            if memory_context:
                messages.append({"role": "system", "content": memory_context})
            messages.append({"role": "user", "content": user_message})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0,
                max_tokens=320,
            )
            text = (response.choices[0].message.content or "").strip()
            return self._parse_json_object(text)
        except Exception:
            return None

    def compose_agent_reply(
        self,
        event: str,
        user_message: str,
        payload: dict[str, Any],
        memory_context: str = "",
    ) -> str | None:
        if not self.available:
            return None

        try:
            messages = [
                {"role": "system", "content": REPLY_PROMPT},
                {"role": "system", "content": f"Event: {event}"},
                {"role": "system", "content": "Payload JSON: " + json.dumps(payload, ensure_ascii=False)},
            ]
            if memory_context:
                messages.append({"role": "system", "content": memory_context})
            if user_message:
                messages.append({"role": "user", "content": user_message})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.4,
                max_tokens=180,
            )
            text = (response.choices[0].message.content or "").strip()
            return text or None
        except Exception:
            return None

    def _fallback(self) -> str:
        return random.choice(FALLBACK_REPLIES)

    @staticmethod
    def _parse_json_object(text: str) -> dict[str, Any] | None:
        try:
            value = json.loads(text)
            return value if isinstance(value, dict) else None
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return None
            try:
                value = json.loads(text[start : end + 1])
                return value if isinstance(value, dict) else None
            except json.JSONDecodeError:
                return None

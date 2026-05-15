import os
import random
from dataclasses import dataclass

from openai import OpenAI


SYSTEM_PROMPT = """
You are a tiny desktop cat companion.
Reply in the same language as the user.
Keep replies warm, short, playful, and useful.
Do not claim to control the computer or perform tasks outside this chat.
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

        if self.api_key:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    @property
    def available(self) -> bool:
        return self.client is not None and bool(self.model)

    def chat(self, user_message: str) -> ChatResult:
        if not user_message.strip():
            return ChatResult("Meow? Did you want to say something?", used_fallback=True)

        if not self.available:
            return ChatResult(self._fallback(), used_fallback=True)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
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

    def _fallback(self) -> str:
        return random.choice(FALLBACK_REPLIES)

import os
from .base import AIResponse

try:
    from groq import Groq
except ImportError:
    Groq = None


class GroqProvider:
    """Groq Llama provider using Groq SDK."""

    def __init__(self):
        self.provider_name = "Groq"
        self.model_name = "llama-3.1-8b-instant"
        self.timeout = 65

    def call(self, prompt: str) -> AIResponse:
        """Call Groq API with the given prompt."""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return AIResponse(
                provider=self.provider_name,
                model=self.model_name,
                text="",
                error="GROQ_API_KEY not found in .env",
            )

        if Groq is None:
            return AIResponse(
                provider=self.provider_name,
                model=self.model_name,
                text="",
                error="groq package not installed",
            )

        try:
            client = Groq(api_key=api_key)
            message = client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                timeout=self.timeout,
            )
            text = message.choices[0].message.content
            return AIResponse(
                provider=self.provider_name,
                model=self.model_name,
                text=text or "",
                error=None,
            )
        except Exception as e:
            return AIResponse(
                provider=self.provider_name,
                model=self.model_name,
                text="",
                error=str(e),
            )

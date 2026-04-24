import os

from .base import AIResponse

try:
    from google import genai
except ImportError:
    genai = None


class GeminiProvider:
    """Google Gemini provider using the google-genai SDK."""

    def __init__(self):
        self.provider_name = "Gemini"
        self.model_name = "gemini-2.0-flash"
        self.timeout = 65

    def call(self, prompt: str) -> AIResponse:
        """Call Gemini API with the given prompt."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return AIResponse(
                provider=self.provider_name,
                model=self.model_name,
                text="",
                error="GEMINI_API_KEY not found in .env",
            )

        if genai is None:
            return AIResponse(
                provider=self.provider_name,
                model=self.model_name,
                text="",
                error="google-genai package not installed",
            )

        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            return AIResponse(
                provider=self.provider_name,
                model=self.model_name,
                text=response.text or "",
                error=None,
            )
        except Exception as e:
            return AIResponse(
                provider=self.provider_name,
                model=self.model_name,
                text="",
                error=str(e),
            )

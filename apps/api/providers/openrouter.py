import os

import requests

from .base import AIResponse


class OpenRouterProvider:
    """OpenRouter-backed council provider."""

    def __init__(self, provider_name: str, model_name: str):
        self.provider_name = provider_name
        self.model_name = model_name
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.timeout = int(os.getenv("AI_REQUEST_TIMEOUT", "65"))

    def call(self, prompt: str) -> AIResponse:
        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            return AIResponse(
                provider=self.provider_name,
                model=self.model_name,
                text="",
                error="OPENROUTER_API_KEY not found in .env",
            )

        try:
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1400,
                },
                timeout=self.timeout,
            )
            data = response.json()
            if not response.ok:
                error = data.get("error", {})
                message = error.get("message") if isinstance(error, dict) else str(error)
                return AIResponse(
                    provider=self.provider_name,
                    model=self.model_name,
                    text="",
                    error=message or f"OpenRouter error {response.status_code}",
                )

            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return AIResponse(
                provider=self.provider_name,
                model=self.model_name,
                text=text or "",
                error=None,
            )
        except requests.exceptions.Timeout:
            return AIResponse(
                provider=self.provider_name,
                model=self.model_name,
                text="",
                error=f"Request timed out after {self.timeout}s",
            )
        except requests.exceptions.RequestException as e:
            return AIResponse(
                provider=self.provider_name,
                model=self.model_name,
                text="",
                error=f"Network error: {str(e)}",
            )
        except Exception as e:
            return AIResponse(
                provider=self.provider_name,
                model=self.model_name,
                text="",
                error=str(e),
            )

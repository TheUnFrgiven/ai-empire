import os
import requests
from .base import AIResponse


class GrokProvider:
    """xAI Grok provider using direct API calls."""

    def __init__(self):
        self.provider_name = "Grok"
        self.model_name = "grok-3-mini"
        self.api_url = "https://api.x.ai/v1/chat/completions"
        self.timeout = 65

    def call(self, prompt: str) -> AIResponse:
        """Call xAI Grok API with the given prompt."""
        api_key = os.getenv("XAI_API_KEY")
        if not api_key:
            return AIResponse(
                provider=self.provider_name,
                model=self.model_name,
                text="",
                error="XAI_API_KEY not found in .env",
            )

        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
            }
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )

            if not response.ok:
                error_msg = f"API error: {response.status_code}"
                try:
                    error_msg = response.json().get("error", {}).get("message", error_msg)
                except Exception:
                    pass
                if response.status_code == 401:
                    error_msg = "xAI rejected XAI_API_KEY. Check that the key is valid."
                elif response.status_code == 403:
                    error_msg = (
                        "xAI returned 403. Check that XAI_API_KEY has API access, billing, "
                        "and permission for the selected Grok model."
                    )
                return AIResponse(
                    provider=self.provider_name,
                    model=self.model_name,
                    text="",
                    error=error_msg,
                )

            data = response.json()
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

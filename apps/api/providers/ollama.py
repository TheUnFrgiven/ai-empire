import os
import requests
from .base import AIResponse


class OllamaProvider:
    """Local Ollama provider using HTTP API."""

    def __init__(self):
        self.provider_name = "Ollama"
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model_name = os.getenv("OLLAMA_MODEL", "llama3.2")
        self.timeout = 65

    def call(self, prompt: str) -> AIResponse:
        """Call Ollama API with the given prompt."""
        try:
            api_endpoint = f"{self.base_url}/api/chat"
            payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            }
            response = requests.post(
                api_endpoint,
                json=payload,
                timeout=self.timeout,
            )

            if not response.ok:
                error_msg = f"API error: {response.status_code}"
                try:
                    error_msg = response.json().get("error", error_msg)
                except Exception:
                    pass
                return AIResponse(
                    provider=self.provider_name,
                    model=self.model_name,
                    text="",
                    error=error_msg,
                )

            data = response.json()
            text = data.get("message", {}).get("content", "")
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
        except requests.exceptions.ConnectionError as e:
            return AIResponse(
                provider=self.provider_name,
                model=self.model_name,
                text="",
                error=f"Connection error: {str(e)}",
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

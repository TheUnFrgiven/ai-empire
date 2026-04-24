import os
from .base import AIResponse


class OpenClawProvider:
    """OpenClaw provider - reserved for future agent/action layer."""

    def __init__(self):
        self.provider_name = "OpenClaw"
        self.model_name = "openclaw-reserved"

    def call(self, prompt: str) -> AIResponse:
        """
        OpenClaw is reserved for the future agent/action layer.
        This provider only works if OPENCLAW_BASE_URL is explicitly configured.
        """
        base_url = os.getenv("OPENCLAW_BASE_URL", "").strip()
        if not base_url or base_url == "":
            return AIResponse(
                provider=self.provider_name,
                model=self.model_name,
                text="",
                error="OpenClaw is reserved for the future agent/action layer and is not yet available for council debates. OPENCLAW_BASE_URL is not configured.",
            )

        return AIResponse(
            provider=self.provider_name,
            model=self.model_name,
            text="",
            error="OpenClaw integration is not yet implemented.",
        )

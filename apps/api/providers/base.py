from dataclasses import dataclass
from typing import Optional


@dataclass
class AIResponse:
    """Standard response format from any AI provider."""

    provider: str
    model: str
    text: str
    error: Optional[str] = None

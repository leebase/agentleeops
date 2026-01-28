"""LLM request and response data structures."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMRequest:
    """Request data for LLM completion."""

    role: str
    messages: list[dict[str, str]]
    json_mode: bool = False
    schema: dict[str, Any] | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    timeout_s: int | None = None


@dataclass
class LLMResponse:
    """Response data from LLM completion."""

    text: str
    provider: str
    model: str | None = None
    usage: dict[str, Any] | None = None
    raw: dict[str, Any] | str | None = None
    request_id: str = ""
    elapsed_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure request_id is set."""
        if not self.request_id:
            import uuid
            self.request_id = str(uuid.uuid4())

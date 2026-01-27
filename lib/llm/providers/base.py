"""Base provider protocol/interface."""

from typing import Protocol, runtime_checkable

from ..response import LLMRequest, LLMResponse


@runtime_checkable
class Provider(Protocol):
    """Protocol for LLM providers."""

    id: str

    def validate_config(self, cfg: dict) -> None:
        """Validate provider-specific config.

        Args:
            cfg: Provider configuration dictionary

        Raises:
            ValueError: If configuration is invalid
        """
        ...

    def complete(self, request: LLMRequest, config: dict) -> LLMResponse:
        """Execute completion request and return response.

        Args:
            request: LLM request data
            config: Provider configuration

        Returns:
            LLM response data

        Raises:
            Various exceptions for different failure modes
        """
        ...

"""LLM provider implementations."""

from .base import Provider
from .openrouter import OpenRouterProvider
from .opencode_cli import OpenCodeCLIProvider
from .codex_cli import CodexCLIProvider
from .gemini_cli import GeminiCLIProvider
from .registry import get_provider, list_providers, register_provider

# Register providers
register_provider(OpenRouterProvider())
register_provider(OpenCodeCLIProvider())
register_provider(CodexCLIProvider())
register_provider(GeminiCLIProvider())

__all__ = [
    "Provider",
    "OpenRouterProvider",
    "OpenCodeCLIProvider",
    "CodexCLIProvider",
    "GeminiCLIProvider",
    "register_provider",
    "get_provider",
    "list_providers",
]

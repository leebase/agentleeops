"""LLM provider implementations."""

from .base import Provider
from .openrouter import OpenRouterProvider
from .registry import get_provider, list_providers, register_provider

# Register providers
register_provider(OpenRouterProvider())

__all__ = [
    "Provider",
    "OpenRouterProvider",
    "register_provider",
    "get_provider",
    "list_providers",
]

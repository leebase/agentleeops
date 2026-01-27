"""Provider registration and lookup system."""

from typing import Dict

from .base import Provider


class ProviderRegistry:
    """Registry for LLM providers."""

    def __init__(self):
        self._providers: Dict[str, Provider] = {}

    def register(self, provider: Provider) -> None:
        """Register a provider.

        Args:
            provider: Provider instance to register
        """
        self._providers[provider.id] = provider

    def get(self, provider_id: str) -> Provider:
        """Get a provider by ID.

        Args:
            provider_id: Provider identifier

        Returns:
            Provider instance

        Raises:
            ValueError: If provider not found
        """
        if provider_id not in self._providers:
            available = ", ".join(self._providers.keys())
            raise ValueError(
                f"Provider '{provider_id}' not found. "
                f"Available providers: {available or 'none'}"
            )
        return self._providers[provider_id]

    def list(self) -> list[str]:
        """List all registered provider IDs.

        Returns:
            List of provider identifiers
        """
        return list(self._providers.keys())


# Global registry instance
_registry = ProviderRegistry()


def register_provider(provider: Provider) -> None:
    """Register a provider in the global registry."""
    _registry.register(provider)


def get_provider(provider_id: str) -> Provider:
    """Get a provider from the global registry."""
    return _registry.get(provider_id)


def list_providers() -> list[str]:
    """List all registered provider IDs."""
    return _registry.list()

"""Main LLM client interface."""

import time
from pathlib import Path
from typing import Any

from lib.logger import get_logger

from .config import LLMConfig, load_config, resolve_role
from .providers.registry import get_provider
from .response import LLMRequest, LLMResponse
from .trace import record_error_trace, record_trace

logger = get_logger(__name__)


class LLMClient:
    """Main LLM client for executing completions via configured providers."""

    def __init__(self, config: LLMConfig, workspace: Path | None = None):
        """Initialize client with configuration.

        Args:
            config: LLM configuration
            workspace: Optional workspace path for trace recording
        """
        self.config = config
        self.workspace = workspace

    @classmethod
    def from_config(cls, config_path: str | Path, workspace: Path | None = None) -> "LLMClient":
        """Load client from YAML config file.

        Args:
            config_path: Path to configuration file
            workspace: Optional workspace path for trace recording

        Returns:
            Initialized LLM client

        Raises:
            FileNotFoundError: If config file not found
            ValueError: If configuration is invalid
        """
        config = load_config(config_path)
        return cls(config, workspace)

    def complete(
        self,
        role: str,
        messages: list[dict[str, str]],
        *,
        json_mode: bool | None = None,
        schema: dict[str, Any] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        timeout_s: int | None = None,
    ) -> LLMResponse:
        """Execute completion request via configured provider.

        Args:
            role: Role name (e.g., "planner", "coder")
            messages: List of chat messages
            json_mode: Request JSON output
            schema: Optional JSON schema (Phase B)
            max_tokens: Override max tokens
            temperature: Override temperature
            timeout_s: Override timeout

        Returns:
            LLM response

        Raises:
            ValueError: If role or provider not found
            Various provider-specific exceptions
        """
        # Resolve role configuration
        role_cfg, provider_cfg = resolve_role(role, self.config)

        # Build request with merged parameters
        request = LLMRequest(
            role=role,
            messages=messages,
            json_mode=json_mode if json_mode is not None else role_cfg.json_mode,
            schema=schema,
            max_tokens=max_tokens if max_tokens is not None else role_cfg.max_tokens,
            temperature=temperature if temperature is not None else role_cfg.temperature,
            timeout_s=timeout_s if timeout_s is not None else role_cfg.timeout_s,
        )

        # Get provider
        provider = get_provider(role_cfg.provider)

        # Log structured event
        logger.info(
            "llm.complete",
            extra={
                "event": "llm.complete.start",
                "role": role,
                "provider": role_cfg.provider,
                "model": role_cfg.model,
                "json_mode": request.json_mode,
                "max_tokens": request.max_tokens,
            },
        )

        # Execute request
        start_time = time.time()
        try:
            # Merge provider config with role model
            provider_config = provider_cfg.config.copy()
            provider_config["model"] = role_cfg.model

            response = provider.complete(request, provider_config)

            # Record trace
            trace_file = record_trace(
                request,
                response,
                role_cfg,
                provider_cfg,
                self.workspace,
            )

            # Log success
            logger.info(
                "llm.complete.success",
                extra={
                    "event": "llm.complete.success",
                    "role": role,
                    "provider": response.provider,
                    "model": response.model,
                    "request_id": response.request_id,
                    "elapsed_ms": response.elapsed_ms,
                    "usage": response.usage,
                    "trace_file": str(trace_file),
                },
            )

            return response

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)

            # Record error trace
            trace_file = record_error_trace(
                request,
                e,
                role_cfg,
                provider_cfg,
                elapsed_ms,
                self.workspace,
            )

            # Log error
            logger.error(
                "llm.complete.error",
                extra={
                    "event": "llm.complete.error",
                    "role": role,
                    "provider": role_cfg.provider,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "elapsed_ms": elapsed_ms,
                    "trace_file": str(trace_file),
                },
            )

            raise

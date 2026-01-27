"""OpenRouter HTTP provider implementation."""

import json
import os
import time
import uuid
from typing import Any

import requests

from ..response import LLMRequest, LLMResponse


class OpenRouterProvider:
    """OpenRouter HTTP API provider."""

    id = "openrouter"

    def validate_config(self, cfg: dict) -> None:
        """Validate OpenRouter configuration.

        Args:
            cfg: Provider configuration

        Raises:
            ValueError: If configuration is invalid
        """
        required_fields = ["base_url", "api_key_env"]
        missing = [f for f in required_fields if f not in cfg]
        if missing:
            raise ValueError(
                f"OpenRouter config missing required fields: {', '.join(missing)}"
            )

        # Check API key environment variable exists
        api_key_env = cfg["api_key_env"]
        if not os.getenv(api_key_env):
            raise ValueError(
                f"Missing environment variable: {api_key_env}"
            )

    def complete(self, request: LLMRequest, config: dict) -> LLMResponse:
        """Execute completion via OpenRouter API.

        Args:
            request: LLM request data
            config: Provider configuration (must include model)

        Returns:
            LLM response data

        Raises:
            ValueError: If configuration is invalid
            requests.HTTPError: For HTTP errors
            requests.Timeout: For timeout errors
        """
        # Get API key from environment
        api_key_env = config["api_key_env"]
        api_key = os.getenv(api_key_env)
        if not api_key:
            raise ValueError(f"Missing environment variable: {api_key_env}")

        # Get model from config
        model = config.get("model")
        if not model:
            raise ValueError("Model not specified in configuration")

        # Build request
        base_url = config["base_url"].rstrip("/")
        url = f"{base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/agentleeops/agentleeops",
            "X-Title": "AgentLeeOps",
        }

        # Merge request parameters with config defaults
        temperature = request.temperature if request.temperature is not None else config.get("temperature", 0.2)
        max_tokens = request.max_tokens if request.max_tokens is not None else config.get("max_tokens", 4000)
        timeout_s = request.timeout_s if request.timeout_s is not None else config.get("timeout_s", 120)

        payload: dict[str, Any] = {
            "model": model,
            "messages": request.messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Add JSON mode if requested (OpenAI-compatible format)
        if request.json_mode:
            payload["response_format"] = {"type": "json_object"}

        # Execute request with timing
        request_id = str(uuid.uuid4())
        start_time = time.time()

        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=timeout_s,
            )
            elapsed_ms = int((time.time() - start_time) * 1000)

            # Handle HTTP errors
            if response.status_code == 401 or response.status_code == 403:
                raise requests.HTTPError(
                    f"Authentication failed (HTTP {response.status_code}). "
                    f"Check your {api_key_env} environment variable.",
                    response=response
                )
            elif response.status_code == 429:
                raise requests.HTTPError(
                    f"Rate limit exceeded (HTTP {response.status_code}). "
                    "Please retry later.",
                    response=response
                )

            response.raise_for_status()

            # Parse response
            data = response.json()

            # Extract content
            if "choices" not in data or not data["choices"]:
                raise ValueError("No choices in OpenRouter response")

            content = data["choices"][0].get("message", {}).get("content", "")

            # Extract usage info
            usage = None
            if "usage" in data:
                usage = {
                    "prompt_tokens": data["usage"].get("prompt_tokens", 0),
                    "completion_tokens": data["usage"].get("completion_tokens", 0),
                    "total_tokens": data["usage"].get("total_tokens", 0),
                }
                # Include cost if available
                if "total_cost" in data["usage"]:
                    usage["total_cost"] = data["usage"]["total_cost"]

            return LLMResponse(
                text=content,
                provider=self.id,
                model=data.get("model", model),
                usage=usage,
                raw=data,
                request_id=request_id,
                elapsed_ms=elapsed_ms,
            )

        except requests.Timeout as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            raise requests.Timeout(
                f"Request timed out after {elapsed_ms}ms "
                f"(timeout: {timeout_s}s)"
            ) from e

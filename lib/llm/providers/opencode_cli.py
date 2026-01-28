"""OpenCode CLI provider implementation."""

import json
import os
import subprocess
import time
import uuid
from typing import Any, Optional

from ..response import LLMRequest, LLMResponse


class OpenCodeCLIProvider:
    """OpenCode CLI subprocess provider."""

    id = "opencode_cli"

    def validate_config(self, cfg: dict) -> None:
        """Validate OpenCode CLI configuration.

        Args:
            cfg: Provider configuration

        Raises:
            ValueError: If configuration is invalid
        """
        # Get command (from config or env var)
        command = cfg.get("command") or os.getenv("OPENCODE_CMD", "opencode")

        # Check if CLI is installed
        try:
            version_result = subprocess.run(
                [command, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if version_result.returncode != 0:
                raise ValueError(
                    f"OpenCode CLI command '{command}' failed version check. "
                    "Install from https://github.com/opencodedev/opencode"
                )
        except FileNotFoundError:
            raise ValueError(
                f"OpenCode CLI not found: '{command}'. "
                "Install from https://github.com/opencodedev/opencode or "
                "set OPENCODE_CMD environment variable."
            )
        except subprocess.TimeoutExpired:
            raise ValueError(
                f"OpenCode CLI version check timed out for command '{command}'"
            )

        # Validate timeout is reasonable
        timeout_s = cfg.get("timeout_s", 300)
        if timeout_s <= 0 or timeout_s > 3600:
            raise ValueError(
                f"Invalid timeout_s: {timeout_s}. Must be between 1 and 3600 seconds."
            )

    def complete(self, request: LLMRequest, config: dict) -> LLMResponse:
        """Execute completion via OpenCode CLI.

        Args:
            request: LLM request data
            config: Provider configuration (must include model)

        Returns:
            LLM response data

        Raises:
            ValueError: If configuration is invalid
            subprocess.TimeoutExpired: If CLI times out
            RuntimeError: If CLI execution fails
        """
        # Get model from config
        model = config.get("model")
        if not model:
            raise ValueError("Model not specified in configuration")

        # Get configuration parameters
        command = config.get("command") or os.getenv("OPENCODE_CMD", "opencode")
        subcommand = config.get("subcommand") or os.getenv("OPENCODE_SUBCOMMAND", "run")
        model_flag = config.get("model_flag") or os.getenv("OPENCODE_MODEL_FLAG", "--model")
        timeout_s = config.get("timeout_s", 300)

        # Build prompt from messages
        # For CLI, we concatenate all messages into a single prompt
        prompt = self._build_prompt(request.messages)

        # Build command
        cmd = [command]
        if subcommand:
            cmd.append(subcommand)

        # Add model flag if specified
        if model_flag and model:
            cmd.extend([model_flag, model])

        # For large prompts, use stdin instead of argv
        ARGV_LIMIT = 100_000  # Conservative limit (~100KB)
        use_stdin = len(prompt) > ARGV_LIMIT

        if not use_stdin:
            # Small prompt: pass as argument (current behavior)
            cmd.append(prompt)
            stdin_input = None
        else:
            # Large prompt: pass via stdin
            stdin_input = prompt.encode('utf-8')

        # Execute with timing
        request_id = str(uuid.uuid4())
        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                input=stdin_input,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
            elapsed_ms = int((time.time() - start_time) * 1000)

        except FileNotFoundError:
            raise RuntimeError(
                f"OpenCode CLI not found: '{command}'. "
                "Install from https://github.com/opencodedev/opencode or "
                "run 'opencode --version' to verify installation."
            )
        except subprocess.TimeoutExpired as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            raise subprocess.TimeoutExpired(
                cmd=e.cmd,
                timeout=timeout_s,
                output=f"OpenCode CLI timed out after {elapsed_ms}ms (timeout: {timeout_s}s)"
            )

        # Check for errors
        if result.returncode != 0:
            stderr = result.stderr.strip() if result.stderr else "Unknown error"
            raise RuntimeError(
                f"OpenCode CLI failed (exit code {result.returncode}): {stderr}"
            )

        # Get response text
        response_text = result.stdout.strip()

        # If JSON mode requested, attempt to repair malformed JSON
        json_repair_applied = False
        json_repair_method = None
        if request.json_mode:
            response_text, json_repair_applied, json_repair_method = self._handle_json_mode(response_text)

        # Build response (CLI doesn't provide usage info)
        return LLMResponse(
            text=response_text,
            provider=self.id,
            model=model,
            usage=None,  # CLI doesn't expose token usage
            raw={"stdout": result.stdout, "stderr": result.stderr},
            request_id=request_id,
            elapsed_ms=elapsed_ms,
            metadata={"command": " ".join(cmd)},
            json_repair_applied=json_repair_applied,
            json_repair_method=json_repair_method,
        )

    def _build_prompt(self, messages: list[dict[str, str]]) -> str:
        """Build a single prompt string from message list.

        For CLI tools, we concatenate all messages with role prefixes.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Single prompt string
        """
        if len(messages) == 1 and messages[0].get("role") == "user":
            # Simple case: single user message
            return messages[0]["content"]

        # Multiple messages: format with role prefixes
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                parts.append(f"System: {content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")
            else:
                parts.append(f"User: {content}")

        return "\n\n".join(parts)

    def _handle_json_mode(self, text: str) -> tuple[str, bool, str]:
        """Handle JSON mode output with repair if needed.

        Args:
            text: Raw CLI output

        Returns:
            Tuple of (repaired_json, was_repaired, repair_method)

        Raises:
            RuntimeError: If JSON is unrepairable
        """
        from lib.llm.json_repair import safe_repair_json

        repaired, error, was_repaired, method = safe_repair_json(text)

        if error:
            raise RuntimeError(
                f"JSON mode enabled but output is not valid JSON: {error}"
            )

        # Return all metadata for auditing
        return repaired, was_repaired, method

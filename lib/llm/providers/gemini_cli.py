"""Gemini CLI provider implementation."""

import json
import os
import subprocess
import time
import uuid
from typing import Any

from ..response import LLMRequest, LLMResponse


class GeminiCLIProvider:
    """Gemini CLI subprocess provider."""

    id = "gemini_cli"

    def validate_config(self, cfg: dict) -> None:
        """Validate Gemini CLI configuration.

        Args:
            cfg: Provider configuration

        Raises:
            ValueError: If configuration is invalid
        """
        # Get command (from config or env var)
        command = cfg.get("command") or os.getenv("GEMINI_CMD", "gemini")

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
                    f"Gemini CLI command '{command}' failed version check. "
                    "Install from https://github.com/google-gemini/gemini-cli"
                )
        except FileNotFoundError:
            raise ValueError(
                f"Gemini CLI not found: '{command}'. "
                "Install from https://github.com/google-gemini/gemini-cli or "
                "set GEMINI_CMD environment variable."
            )
        except subprocess.TimeoutExpired:
            raise ValueError(
                f"Gemini CLI version check timed out for command '{command}'"
            )

        # Validate timeout is reasonable
        timeout_s = cfg.get("timeout_s", 120)
        if timeout_s <= 0 or timeout_s > 3600:
            raise ValueError(
                f"Invalid timeout_s: {timeout_s}. Must be between 1 and 3600 seconds."
            )

    def complete(self, request: LLMRequest, config: dict) -> LLMResponse:
        """Execute completion via Gemini CLI.

        Args:
            request: LLM request data
            config: Provider configuration (may include model)

        Returns:
            LLM response data

        Raises:
            ValueError: If configuration is invalid
            subprocess.TimeoutExpired: If CLI times out
            RuntimeError: If CLI execution fails
        """
        # Get configuration parameters
        command = config.get("command") or os.getenv("GEMINI_CMD", "gemini")
        model = config.get("model")  # Optional for Gemini CLI
        timeout_s = config.get("timeout_s", 120)

        # Build prompt from messages
        prompt = self._build_prompt(request.messages)

        # Build command
        cmd = [command]

        # Add model flag if specified
        if model:
            cmd.extend(["--model", model])

        # Always use JSON output format for structured parsing
        cmd.extend(["--output-format", "json"])

        # Add prompt as last argument
        cmd.append(prompt)

        # Execute with timing
        request_id = str(uuid.uuid4())
        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
            elapsed_ms = int((time.time() - start_time) * 1000)

        except FileNotFoundError:
            raise RuntimeError(
                f"Gemini CLI not found: '{command}'. "
                "Install from https://github.com/google-gemini/gemini-cli or "
                "run 'npm install -g @google/gemini-cli' to install."
            )
        except subprocess.TimeoutExpired as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            raise subprocess.TimeoutExpired(
                cmd=e.cmd,
                timeout=timeout_s,
                output=f"Gemini CLI timed out after {elapsed_ms}ms (timeout: {timeout_s}s)"
            )

        # Check for errors
        if result.returncode != 0:
            stderr = result.stderr.strip() if result.stderr else "Unknown error"
            raise RuntimeError(
                f"Gemini CLI failed (exit code {result.returncode}): {stderr}"
            )

        # Parse JSON output
        response_text = self._parse_gemini_output(result.stdout)

        # If JSON mode requested, attempt to repair malformed JSON
        if request.json_mode:
            response_text = self._handle_json_mode(response_text)

        # Extract usage info from JSON output if available
        usage = self._extract_usage(result.stdout)

        # Build response
        return LLMResponse(
            text=response_text,
            provider=self.id,
            model=model or "gemini-default",
            usage=usage,
            raw={"stdout": result.stdout, "stderr": result.stderr},
            request_id=request_id,
            elapsed_ms=elapsed_ms,
            metadata={"command": " ".join(cmd)}
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

    def _parse_gemini_output(self, stdout: str) -> str:
        """Parse Gemini CLI JSON output to extract response text.

        Args:
            stdout: Raw stdout from Gemini CLI

        Returns:
            Extracted response text

        Raises:
            RuntimeError: If output cannot be parsed
        """
        # Gemini CLI with --output-format json returns JSON followed by "Loaded cached credentials."
        # Split and take the first part
        lines = stdout.strip().split('\n')

        # Find the JSON content (everything before "Loaded cached credentials.")
        json_lines = []
        for line in lines:
            if "Loaded cached credentials" in line:
                break
            json_lines.append(line)

        json_str = '\n'.join(json_lines).strip()

        try:
            data = json.loads(json_str)

            # Extract response field
            if "response" in data:
                return data["response"]
            else:
                raise RuntimeError("Gemini CLI output missing 'response' field")

        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse Gemini CLI JSON output: {e}")

    def _extract_usage(self, stdout: str) -> dict[str, Any] | None:
        """Extract usage statistics from Gemini CLI output.

        Args:
            stdout: Raw stdout from Gemini CLI

        Returns:
            Usage dictionary or None
        """
        try:
            lines = stdout.strip().split('\n')
            json_lines = []
            for line in lines:
                if "Loaded cached credentials" in line:
                    break
                json_lines.append(line)

            json_str = '\n'.join(json_lines).strip()
            data = json.loads(json_str)

            if "stats" in data and "models" in data["stats"]:
                # Aggregate token usage across all models
                total_input = 0
                total_output = 0
                total_tokens = 0

                for model_name, model_stats in data["stats"]["models"].items():
                    if "tokens" in model_stats:
                        tokens = model_stats["tokens"]
                        total_input += tokens.get("input", 0)
                        total_output += tokens.get("candidates", 0)
                        total_tokens += tokens.get("total", 0)

                return {
                    "prompt_tokens": total_input,
                    "completion_tokens": total_output,
                    "total_tokens": total_tokens,
                }
        except Exception:
            # If we can't parse usage, just return None
            pass

        return None

    def _handle_json_mode(self, text: str) -> str:
        """Handle JSON mode output with repair if needed.

        Args:
            text: Raw CLI output

        Returns:
            Repaired JSON string if possible

        Raises:
            RuntimeError: If JSON is unrepairable
        """
        from lib.llm.json_repair import safe_repair_json

        repaired, error, was_repaired, method = safe_repair_json(text)

        if error:
            raise RuntimeError(
                f"JSON mode enabled but output is not valid JSON: {error}"
            )

        # Return repaired JSON
        return repaired

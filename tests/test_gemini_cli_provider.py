"""Tests for Gemini CLI provider."""

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock
import pytest

from lib.llm.providers.gemini_cli import GeminiCLIProvider
from lib.llm.response import LLMRequest, LLMResponse


class TestGeminiCLIProvider:
    """Test Gemini CLI provider."""

    def test_provider_id(self):
        """Provider has correct ID."""
        provider = GeminiCLIProvider()
        assert provider.id == "gemini_cli"

    def test_validate_config_success(self):
        """Validate configuration when CLI is installed."""
        provider = GeminiCLIProvider()
        config = {
            "command": "gemini",
            "timeout_s": 120,
        }

        # Mock successful version check
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            provider.validate_config(config)  # Should not raise

    def test_validate_config_cli_not_found(self):
        """Raise error when CLI not found."""
        provider = GeminiCLIProvider()
        config = {
            "command": "nonexistent-cli",
            "timeout_s": 120,
        }

        # Mock FileNotFoundError
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(ValueError) as exc_info:
                provider.validate_config(config)
            assert "Gemini CLI not found" in str(exc_info.value)

    def test_validate_config_invalid_timeout(self):
        """Raise error for invalid timeout."""
        provider = GeminiCLIProvider()
        config = {
            "command": "gemini",
            "timeout_s": 0,  # Invalid
        }

        with pytest.raises(ValueError) as exc_info:
            provider.validate_config(config)
        assert "Invalid timeout_s" in str(exc_info.value)

    def test_complete_simple_prompt(self):
        """Complete with simple user prompt."""
        provider = GeminiCLIProvider()
        request = LLMRequest(
            role="tester",
            messages=[{"role": "user", "content": "Hello"}],
            json_mode=False,
        )
        config = {
            "command": "gemini",
            "model": "gemini-3-flash-preview",
            "timeout_s": 120,
        }

        # Mock subprocess with Gemini JSON output
        gemini_output = json.dumps({
            "session_id": "test-session",
            "response": "Hello, world!",
            "stats": {
                "models": {
                    "gemini-3-flash-preview": {
                        "tokens": {
                            "input": 100,
                            "candidates": 20,
                            "total": 120
                        }
                    }
                }
            }
        }) + "\nLoaded cached credentials.\n"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=gemini_output,
                stderr="",
            )

            response = provider.complete(request, config)

            # Verify response
            assert isinstance(response, LLMResponse)
            assert response.text == "Hello, world!"
            assert response.provider == "gemini_cli"
            assert response.model == "gemini-3-flash-preview"
            assert response.usage is not None
            assert response.usage["prompt_tokens"] == 100
            assert response.usage["completion_tokens"] == 20
            assert response.usage["total_tokens"] == 120

            # Verify command
            call_args = mock_run.call_args
            cmd = call_args[0][0]
            assert cmd[0] == "gemini"
            assert "--model" in cmd
            assert "gemini-3-flash-preview" in cmd
            assert "--output-format" in cmd
            assert "json" in cmd

    def test_complete_json_mode(self):
        """Complete with JSON mode enabled."""
        provider = GeminiCLIProvider()
        request = LLMRequest(
            role="tester",
            messages=[{"role": "user", "content": "Generate JSON"}],
            json_mode=True,
        )
        config = {
            "command": "gemini",
            "model": "gemini-3-flash-preview",
            "timeout_s": 120,
        }

        # Mock subprocess returning JSON in markdown with trailing comma
        gemini_output = json.dumps({
            "session_id": "test-session",
            "response": '```json\n{"key": "value",}\n```',
            "stats": {}
        }) + "\nLoaded cached credentials.\n"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=gemini_output,
                stderr="",
            )

            response = provider.complete(request, config)

            # Should repair JSON (remove trailing comma and extract from markdown)
            assert response.text == '{"key": "value"}'
            data = json.loads(response.text)
            assert data == {"key": "value"}

    def test_complete_no_model_uses_default(self):
        """Complete without model specification uses default."""
        provider = GeminiCLIProvider()
        request = LLMRequest(
            role="tester",
            messages=[{"role": "user", "content": "Hello"}],
        )
        config = {
            "command": "gemini",
            "timeout_s": 120,
            # No model specified
        }

        gemini_output = json.dumps({
            "session_id": "test-session",
            "response": "Hello!",
            "stats": {}
        }) + "\nLoaded cached credentials.\n"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=gemini_output,
                stderr="",
            )

            response = provider.complete(request, config)

            # Verify model defaults
            assert response.model == "gemini-default"

            # Verify no --model flag in command
            call_args = mock_run.call_args
            cmd = call_args[0][0]
            assert "--model" not in cmd

    def test_complete_cli_timeout(self):
        """Raise TimeoutExpired when CLI times out."""
        provider = GeminiCLIProvider()
        request = LLMRequest(
            role="tester",
            messages=[{"role": "user", "content": "Hello"}],
        )
        config = {
            "command": "gemini",
            "timeout_s": 1,
        }

        # Mock timeout
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(["gemini"], 1)):
            with pytest.raises(subprocess.TimeoutExpired):
                provider.complete(request, config)

    def test_complete_cli_error(self):
        """Raise error when CLI returns non-zero exit code."""
        provider = GeminiCLIProvider()
        request = LLMRequest(
            role="tester",
            messages=[{"role": "user", "content": "Hello"}],
        )
        config = {
            "command": "gemini",
            "timeout_s": 120,
        }

        # Mock error
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=1,
                stdout="",
                stderr="API error",
            )

            with pytest.raises(RuntimeError) as exc_info:
                provider.complete(request, config)
            assert "Gemini CLI failed" in str(exc_info.value)
            assert "API error" in str(exc_info.value)

    def test_parse_gemini_output(self):
        """Parse Gemini CLI JSON output correctly."""
        provider = GeminiCLIProvider()

        output = json.dumps({
            "session_id": "test",
            "response": "Test response",
            "stats": {}
        }) + "\nLoaded cached credentials.\n"

        result = provider._parse_gemini_output(output)
        assert result == "Test response"

    def test_parse_gemini_output_missing_response(self):
        """Raise error when response field missing."""
        provider = GeminiCLIProvider()

        output = json.dumps({
            "session_id": "test",
            "stats": {}
        }) + "\nLoaded cached credentials.\n"

        with pytest.raises(RuntimeError) as exc_info:
            provider._parse_gemini_output(output)
        assert "missing 'response' field" in str(exc_info.value)

    def test_extract_usage_multi_model(self):
        """Extract and aggregate usage from multiple models."""
        provider = GeminiCLIProvider()

        output = json.dumps({
            "session_id": "test",
            "response": "Test",
            "stats": {
                "models": {
                    "gemini-2.5-flash-lite": {
                        "tokens": {
                            "input": 100,
                            "candidates": 20,
                            "total": 120
                        }
                    },
                    "gemini-3-flash-preview": {
                        "tokens": {
                            "input": 200,
                            "candidates": 30,
                            "total": 230
                        }
                    }
                }
            }
        }) + "\nLoaded cached credentials.\n"

        usage = provider._extract_usage(output)

        assert usage is not None
        assert usage["prompt_tokens"] == 300  # 100 + 200
        assert usage["completion_tokens"] == 50  # 20 + 30
        assert usage["total_tokens"] == 350  # 120 + 230

    def test_build_prompt_single_message(self):
        """Build prompt from single user message."""
        provider = GeminiCLIProvider()
        messages = [{"role": "user", "content": "Hello"}]
        prompt = provider._build_prompt(messages)
        assert prompt == "Hello"

    def test_build_prompt_multiple_messages(self):
        """Build prompt from multiple messages with role prefixes."""
        provider = GeminiCLIProvider()
        messages = [
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "Hi"},
        ]
        prompt = provider._build_prompt(messages)
        assert "System: Be helpful" in prompt
        assert "User: Hi" in prompt

    def test_complete_response_metadata(self):
        """Response includes command metadata."""
        provider = GeminiCLIProvider()
        request = LLMRequest(
            role="tester",
            messages=[{"role": "user", "content": "Hello"}],
        )
        config = {
            "command": "gemini",
            "timeout_s": 120,
        }

        gemini_output = json.dumps({
            "session_id": "test",
            "response": "Hi",
            "stats": {}
        }) + "\nLoaded cached credentials.\n"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=gemini_output,
                stderr="",
            )

            response = provider.complete(request, config)

            # Check metadata
            assert "command" in response.metadata
            assert "gemini" in response.metadata["command"]

    def test_complete_uses_explicit_cwd(self):
        """Pass cwd through to subprocess.run when configured."""
        provider = GeminiCLIProvider()
        request = LLMRequest(
            role="tester",
            messages=[{"role": "user", "content": "Hello"}],
        )
        config = {
            "command": "gemini",
            "timeout_s": 120,
            "cwd": "/tmp",
        }

        gemini_output = json.dumps({
            "session_id": "test",
            "response": "Hi",
            "stats": {}
        }) + "\nLoaded cached credentials.\n"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=gemini_output,
                stderr="",
            )

            response = provider.complete(request, config)

            assert Path(mock_run.call_args.kwargs["cwd"]) == Path("/tmp").resolve()
            assert Path(response.metadata["cwd"]) == Path("/tmp").resolve()

    def test_validate_config_invalid_cwd(self):
        """Raise error for invalid cwd path."""
        provider = GeminiCLIProvider()
        config = {
            "command": "gemini",
            "timeout_s": 120,
            "cwd": "/definitely/not/a/real/path",
        }

        with pytest.raises(ValueError) as exc_info:
            provider.validate_config(config)
        assert "Invalid cwd" in str(exc_info.value)

"""Tests for CLI providers (OpenCode, Gemini)."""

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock
import pytest

from lib.llm.providers.opencode_cli import OpenCodeCLIProvider
from lib.llm.response import LLMRequest, LLMResponse


class TestOpenCodeCLIProvider:
    """Test OpenCode CLI provider."""

    def test_provider_id(self):
        """Provider has correct ID."""
        provider = OpenCodeCLIProvider()
        assert provider.id == "opencode_cli"

    def test_validate_config_success(self):
        """Validate configuration when CLI is installed."""
        provider = OpenCodeCLIProvider()
        config = {
            "command": "opencode",
            "timeout_s": 300,
        }

        # Mock successful version check
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            provider.validate_config(config)  # Should not raise

    def test_validate_config_cli_not_found(self):
        """Raise error when CLI not found."""
        provider = OpenCodeCLIProvider()
        config = {
            "command": "nonexistent-cli",
            "timeout_s": 300,
        }

        # Mock FileNotFoundError
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(ValueError) as exc_info:
                provider.validate_config(config)
            assert "OpenCode CLI not found" in str(exc_info.value)

    def test_validate_config_invalid_timeout(self):
        """Raise error for invalid timeout."""
        provider = OpenCodeCLIProvider()
        config = {
            "command": "opencode",
            "timeout_s": 0,  # Invalid
        }

        with pytest.raises(ValueError) as exc_info:
            provider.validate_config(config)
        assert "Invalid timeout_s" in str(exc_info.value)

    def test_validate_config_timeout_too_large(self):
        """Raise error for timeout too large."""
        provider = OpenCodeCLIProvider()
        config = {
            "command": "opencode",
            "timeout_s": 5000,  # > 3600
        }

        with pytest.raises(ValueError) as exc_info:
            provider.validate_config(config)
        assert "Invalid timeout_s" in str(exc_info.value)

    def test_complete_simple_prompt(self):
        """Complete with simple user prompt."""
        provider = OpenCodeCLIProvider()
        request = LLMRequest(
            role="coder",
            messages=[{"role": "user", "content": "Hello"}],
            json_mode=False,
        )
        config = {
            "command": "opencode",
            "subcommand": "run",
            "model_flag": "--model",
            "model": "gpt-4o",
            "timeout_s": 300,
        }

        # Mock subprocess
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="Hello, world!",
                stderr="",
            )

            response = provider.complete(request, config)

            # Verify response
            assert isinstance(response, LLMResponse)
            assert response.text == "Hello, world!"
            assert response.provider == "opencode_cli"
            assert response.model == "gpt-4o"

            # Verify command
            call_args = mock_run.call_args
            cmd = call_args[0][0]
            assert cmd[0] == "opencode"
            assert cmd[1] == "run"
            assert "--model" in cmd
            assert "gpt-4o" in cmd
            assert "Hello" in cmd

    def test_complete_json_mode(self):
        """Complete with JSON mode enabled."""
        provider = OpenCodeCLIProvider()
        request = LLMRequest(
            role="planner",
            messages=[{"role": "user", "content": "Generate JSON"}],
            json_mode=True,
        )
        config = {
            "command": "opencode",
            "model": "gpt-4o",
            "timeout_s": 300,
        }

        # Mock subprocess returning JSON with trailing comma
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout='{"key": "value",}',  # Malformed
                stderr="",
            )

            response = provider.complete(request, config)

            # Should repair JSON
            assert response.text == '{"key": "value"}'
            data = json.loads(response.text)
            assert data == {"key": "value"}

    def test_complete_json_mode_unrepairable(self):
        """Raise error when JSON mode output is unrepairable."""
        provider = OpenCodeCLIProvider()
        request = LLMRequest(
            role="planner",
            messages=[{"role": "user", "content": "Generate JSON"}],
            json_mode=True,
        )
        config = {
            "command": "opencode",
            "model": "gpt-4o",
            "timeout_s": 300,
        }

        # Mock subprocess returning broken JSON
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout='{"key": broken}',  # Unrepairable
                stderr="",
            )

            with pytest.raises(RuntimeError) as exc_info:
                provider.complete(request, config)
            assert "not valid JSON" in str(exc_info.value)

    def test_complete_cli_timeout(self):
        """Raise TimeoutExpired when CLI times out."""
        provider = OpenCodeCLIProvider()
        request = LLMRequest(
            role="coder",
            messages=[{"role": "user", "content": "Hello"}],
        )
        config = {
            "command": "opencode",
            "model": "gpt-4o",
            "timeout_s": 1,
        }

        # Mock timeout
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(["opencode"], 1)):
            with pytest.raises(subprocess.TimeoutExpired):
                provider.complete(request, config)

    def test_complete_cli_error(self):
        """Raise error when CLI returns non-zero exit code."""
        provider = OpenCodeCLIProvider()
        request = LLMRequest(
            role="coder",
            messages=[{"role": "user", "content": "Hello"}],
        )
        config = {
            "command": "opencode",
            "model": "gpt-4o",
            "timeout_s": 300,
        }

        # Mock error
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=1,
                stdout="",
                stderr="Authentication failed",
            )

            with pytest.raises(RuntimeError) as exc_info:
                provider.complete(request, config)
            assert "OpenCode CLI failed" in str(exc_info.value)
            assert "Authentication failed" in str(exc_info.value)

    def test_complete_multi_message_prompt(self):
        """Build prompt from multiple messages."""
        provider = OpenCodeCLIProvider()
        request = LLMRequest(
            role="coder",
            messages=[
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"},
                {"role": "user", "content": "How are you?"},
            ],
        )
        config = {
            "command": "opencode",
            "model": "gpt-4o",
            "timeout_s": 300,
        }

        # Mock subprocess
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="I'm good!",
                stderr="",
            )

            provider.complete(request, config)

            # Verify prompt construction
            call_args = mock_run.call_args
            cmd = call_args[0][0]
            prompt = cmd[-1]  # Last argument is the prompt
            assert "System: You are helpful" in prompt
            assert "User: Hello" in prompt
            assert "Assistant: Hi" in prompt
            assert "User: How are you?" in prompt

    def test_complete_env_var_fallback(self):
        """Use environment variables for config fallback."""
        provider = OpenCodeCLIProvider()
        request = LLMRequest(
            role="coder",
            messages=[{"role": "user", "content": "Hello"}],
        )
        config = {
            "model": "gpt-4o",
            "timeout_s": 300,
        }

        # Set environment variables
        with patch.dict(os.environ, {
            "OPENCODE_CMD": "custom-opencode",
            "OPENCODE_SUBCOMMAND": "chat",
            "OPENCODE_MODEL_FLAG": "--llm",
        }):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(
                    returncode=0,
                    stdout="Response",
                    stderr="",
                )

                provider.complete(request, config)

                # Verify environment variables used
                call_args = mock_run.call_args
                cmd = call_args[0][0]
                assert cmd[0] == "custom-opencode"
                assert cmd[1] == "chat"
                assert "--llm" in cmd

    def test_complete_no_model_error(self):
        """Raise error when model not specified."""
        provider = OpenCodeCLIProvider()
        request = LLMRequest(
            role="coder",
            messages=[{"role": "user", "content": "Hello"}],
        )
        config = {
            "command": "opencode",
            "timeout_s": 300,
            # No model
        }

        with pytest.raises(ValueError) as exc_info:
            provider.complete(request, config)
        assert "Model not specified" in str(exc_info.value)

    def test_complete_response_metadata(self):
        """Response includes command metadata."""
        provider = OpenCodeCLIProvider()
        request = LLMRequest(
            role="coder",
            messages=[{"role": "user", "content": "Hello"}],
        )
        config = {
            "command": "opencode",
            "model": "gpt-4o",
            "timeout_s": 300,
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="Response",
                stderr="",
            )

            response = provider.complete(request, config)

            # Check metadata
            assert "command" in response.metadata
            assert "opencode" in response.metadata["command"]

    def test_complete_uses_explicit_cwd(self):
        """Pass cwd through to subprocess.run when configured."""
        provider = OpenCodeCLIProvider()
        request = LLMRequest(
            role="coder",
            messages=[{"role": "user", "content": "Hello"}],
        )
        config = {
            "command": "opencode",
            "model": "gpt-4o",
            "timeout_s": 300,
            "cwd": "/tmp",
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="Response",
                stderr="",
            )

            response = provider.complete(request, config)

            assert Path(mock_run.call_args.kwargs["cwd"]) == Path("/tmp").resolve()
            assert Path(response.metadata["cwd"]) == Path("/tmp").resolve()

    def test_validate_config_invalid_cwd(self):
        """Raise error for invalid cwd path."""
        provider = OpenCodeCLIProvider()
        config = {
            "command": "opencode",
            "timeout_s": 300,
            "cwd": "/definitely/not/a/real/path",
        }

        with pytest.raises(ValueError) as exc_info:
            provider.validate_config(config)
        assert "Invalid cwd" in str(exc_info.value)

    def test_complete_elapsed_time(self):
        """Response includes elapsed time."""
        provider = OpenCodeCLIProvider()
        request = LLMRequest(
            role="coder",
            messages=[{"role": "user", "content": "Hello"}],
        )
        config = {
            "command": "opencode",
            "model": "gpt-4o",
            "timeout_s": 300,
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="Response",
                stderr="",
            )

            response = provider.complete(request, config)

            # Check elapsed time exists and is reasonable
            assert response.elapsed_ms >= 0
            assert response.elapsed_ms < 10000  # Less than 10s for mocked call

    def test_build_prompt_single_message(self):
        """Build prompt from single user message."""
        provider = OpenCodeCLIProvider()
        messages = [{"role": "user", "content": "Hello"}]
        prompt = provider._build_prompt(messages)
        assert prompt == "Hello"

    def test_build_prompt_multiple_messages(self):
        """Build prompt from multiple messages with role prefixes."""
        provider = OpenCodeCLIProvider()
        messages = [
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "Hi"},
        ]
        prompt = provider._build_prompt(messages)
        assert "System: Be helpful" in prompt
        assert "User: Hi" in prompt

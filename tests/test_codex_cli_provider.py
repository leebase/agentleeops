"""Tests for Codex CLI provider."""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from lib.llm.providers.codex_cli import CodexCLIProvider
from lib.llm.response import LLMRequest


class TestCodexCLIProvider:
    """Test Codex CLI provider behavior."""

    def test_provider_id(self):
        provider = CodexCLIProvider()
        assert provider.id == "codex_cli"

    def test_validate_config_success(self):
        provider = CodexCLIProvider()
        config = {
            "command": "codex",
            "timeout_s": 300,
        }

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                Mock(returncode=0, stdout="codex-cli 0.46.0", stderr=""),
                Mock(returncode=0, stdout="Logged in using ChatGPT", stderr=""),
            ]
            provider.validate_config(config)

    def test_validate_config_cli_not_found(self):
        provider = CodexCLIProvider()
        config = {"command": "codex", "timeout_s": 300}

        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(ValueError) as exc_info:
                provider.validate_config(config)
            assert "Codex CLI not found" in str(exc_info.value)

    def test_validate_config_not_logged_in(self):
        provider = CodexCLIProvider()
        config = {"command": "codex", "timeout_s": 300}

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                Mock(returncode=0, stdout="codex-cli 0.46.0", stderr=""),
                Mock(returncode=1, stdout="", stderr="not logged in"),
            ]
            with pytest.raises(ValueError) as exc_info:
                provider.validate_config(config)
            assert "not logged in" in str(exc_info.value).lower()

    def test_validate_config_invalid_cwd(self):
        provider = CodexCLIProvider()
        config = {"command": "codex", "timeout_s": 300, "cwd": "/no/such/path"}

        with pytest.raises(ValueError) as exc_info:
            provider.validate_config(config)
        assert "Invalid cwd" in str(exc_info.value)

    def test_complete_uses_output_last_message_and_cwd(self):
        provider = CodexCLIProvider()
        request = LLMRequest(
            role="planner",
            messages=[{"role": "user", "content": "Say hi"}],
        )
        config = {
            "command": "codex",
            "subcommand": "exec",
            "model_flag": "--model",
            "model": "gpt-5",
            "timeout_s": 300,
            "cwd": "/tmp",
        }

        def _mock_run(cmd, **kwargs):
            output_path = cmd[cmd.index("--output-last-message") + 1]
            Path(output_path).write_text("hello from codex\n", encoding="utf-8")
            return Mock(returncode=0, stdout="transcript", stderr="")

        with patch("subprocess.run", side_effect=_mock_run) as mock_run:
            response = provider.complete(request, config)
            assert response.text == "hello from codex"
            assert response.provider == "codex_cli"
            assert response.model == "gpt-5"
            assert Path(response.metadata["cwd"]) == Path("/tmp").resolve()
            assert Path(mock_run.call_args.kwargs["cwd"]) == Path("/tmp").resolve()

    def test_complete_json_mode_repairs(self):
        provider = CodexCLIProvider()
        request = LLMRequest(
            role="planner",
            messages=[{"role": "user", "content": "Return JSON"}],
            json_mode=True,
        )
        config = {
            "command": "codex",
            "model": "gpt-5",
            "timeout_s": 300,
        }

        def _mock_run(cmd, **kwargs):
            output_path = cmd[cmd.index("--output-last-message") + 1]
            Path(output_path).write_text('{"ok": true,}', encoding="utf-8")
            return Mock(returncode=0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=_mock_run):
            response = provider.complete(request, config)
            assert response.text == '{"ok": true}'

    def test_complete_timeout(self):
        provider = CodexCLIProvider()
        request = LLMRequest(role="planner", messages=[{"role": "user", "content": "Hi"}])
        config = {"command": "codex", "model": "gpt-5", "timeout_s": 1}

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(["codex"], 1)):
            with pytest.raises(subprocess.TimeoutExpired):
                provider.complete(request, config)

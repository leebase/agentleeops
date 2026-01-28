"""Tests for lib/llm/doctor.py - Configuration validation."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
import pytest

from lib.llm.doctor import (
    check_provider,
    check_role,
    check_config,
)
from lib.llm.config import LLMConfig, ProviderConfig, RoleConfig


class TestCheckProvider:
    """Test provider validation."""

    def test_valid_openrouter_provider(self):
        """Valid OpenRouter provider passes."""
        provider_cfg = ProviderConfig(
            type="openrouter_http",
            config={
                "base_url": "https://openrouter.ai/api/v1",
                "api_key_env": "OPENROUTER_API_KEY",
                "timeout_s": 120,
            }
        )

        # Mock environment variable
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            result = check_provider("openrouter", provider_cfg)

        assert result["available"] is True
        assert result["error"] is None

    def test_missing_api_key(self):
        """Provider unavailable when API key missing."""
        provider_cfg = ProviderConfig(
            type="openrouter_http",
            config={
                "base_url": "https://openrouter.ai/api/v1",
                "api_key_env": "MISSING_KEY",
                "timeout_s": 120,
            }
        )

        result = check_provider("openrouter", provider_cfg)

        assert result["available"] is False
        assert "MISSING_KEY" in result["error"]

    def test_valid_opencode_cli_provider(self):
        """Valid OpenCode CLI provider passes when CLI installed."""
        provider_cfg = ProviderConfig(
            type="opencode_cli",
            config={
                "command": "opencode",
                "timeout_s": 300,
            }
        )

        # Mock successful CLI check
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = check_provider("opencode", provider_cfg)

        assert result["available"] is True
        assert result["error"] is None

    def test_opencode_cli_not_found(self):
        """Provider unavailable when CLI not found."""
        provider_cfg = ProviderConfig(
            type="opencode_cli",
            config={
                "command": "nonexistent-cli",
                "timeout_s": 300,
            }
        )

        # Mock FileNotFoundError
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = check_provider("opencode", provider_cfg)

        assert result["available"] is False
        assert "not found" in result["error"]

    def test_unknown_provider_type(self):
        """Provider unavailable for unknown type."""
        provider_cfg = ProviderConfig(
            type="unknown_type",
            config={}
        )

        result = check_provider("custom", provider_cfg)

        assert result["available"] is False
        assert "Unknown provider type" in result["error"]


class TestCheckRole:
    """Test role validation."""

    def test_valid_role(self):
        """Valid role passes."""
        config = LLMConfig(
            default_role="planner",
            providers={
                "openrouter": ProviderConfig(
                    type="openrouter_http",
                    config={"base_url": "https://openrouter.ai/api/v1", "api_key_env": "KEY"}
                )
            },
            roles={
                "planner": RoleConfig(
                    provider="openrouter",
                    model="gpt-4o",
                    temperature=0.2,
                    max_tokens=4000,
                )
            }
        )
        provider_results = {
            "openrouter": {"available": True}
        }

        result = check_role("planner", config.roles["planner"], config, provider_results)

        assert result["valid"] is True
        assert result["error"] is None

    def test_role_provider_not_found(self):
        """Role invalid when provider not in config."""
        config = LLMConfig(
            default_role="planner",
            providers={},
            roles={
                "planner": RoleConfig(
                    provider="missing",
                    model="gpt-4o",
                )
            }
        )
        provider_results = {}

        result = check_role("planner", config.roles["planner"], config, provider_results)

        assert result["valid"] is False
        assert "not found" in result["error"]

    def test_role_provider_unavailable(self):
        """Role invalid when provider unavailable."""
        config = LLMConfig(
            default_role="planner",
            providers={
                "opencode": ProviderConfig(type="opencode_cli", config={})
            },
            roles={
                "planner": RoleConfig(
                    provider="opencode",
                    model="gpt-4o",
                )
            }
        )
        provider_results = {
            "opencode": {"available": False, "error": "CLI not found"}
        }

        result = check_role("planner", config.roles["planner"], config, provider_results)

        assert result["valid"] is False
        assert "not available" in result["error"]

    def test_role_missing_model_warning(self):
        """Warn when model not specified."""
        config = LLMConfig(
            default_role="planner",
            providers={
                "openrouter": ProviderConfig(type="openrouter_http", config={"api_key_env": "KEY", "base_url": "url"})
            },
            roles={
                "planner": RoleConfig(
                    provider="openrouter",
                    model=None,  # Missing
                )
            }
        )
        provider_results = {
            "openrouter": {"available": True}
        }

        result = check_role("planner", config.roles["planner"], config, provider_results)

        assert result["valid"] is True  # Still valid, just warning
        assert "No model specified" in result["warnings"]

    def test_role_temperature_out_of_range(self):
        """Warn when temperature out of range."""
        config = LLMConfig(
            default_role="planner",
            providers={
                "openrouter": ProviderConfig(type="openrouter_http", config={"api_key_env": "KEY", "base_url": "url"})
            },
            roles={
                "planner": RoleConfig(
                    provider="openrouter",
                    model="gpt-4o",
                    temperature=1.5,  # Out of range
                )
            }
        )
        provider_results = {
            "openrouter": {"available": True}
        }

        result = check_role("planner", config.roles["planner"], config, provider_results)

        assert result["valid"] is True  # Still valid, just warning
        assert "Temperature" in result["warnings"][0]

    def test_role_invalid_max_tokens(self):
        """Error when max_tokens invalid."""
        config = LLMConfig(
            default_role="planner",
            providers={
                "openrouter": ProviderConfig(type="openrouter_http", config={"api_key_env": "KEY", "base_url": "url"})
            },
            roles={
                "planner": RoleConfig(
                    provider="openrouter",
                    model="gpt-4o",
                    max_tokens=0,  # Invalid
                )
            }
        )
        provider_results = {
            "openrouter": {"available": True}
        }

        result = check_role("planner", config.roles["planner"], config, provider_results)

        assert result["valid"] is False
        assert "max_tokens" in result["error"]


class TestCheckConfig:
    """Test full configuration validation."""

    def test_valid_config(self, tmp_path):
        """Valid configuration passes."""
        config_content = """
llm:
  default_role: planner
  providers:
    openrouter:
      type: openrouter_http
      base_url: "https://openrouter.ai/api/v1"
      api_key_env: "OPENROUTER_API_KEY"
      timeout_s: 120
  roles:
    planner:
      provider: openrouter
      model: "gpt-4o"
      temperature: 0.2
      max_tokens: 4000
"""
        config_path = tmp_path / "llm.yaml"
        config_path.write_text(config_content)

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            result = check_config(str(config_path))

        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert "openrouter" in result["providers"]
        assert "planner" in result["roles"]

    def test_config_file_not_found(self):
        """Error when config file not found."""
        result = check_config("/nonexistent/config.yaml")

        assert result["valid"] is False
        assert "not found" in result["errors"][0]

    def test_config_with_unavailable_provider(self, tmp_path):
        """Warning when provider unavailable."""
        config_content = """
llm:
  default_role: planner
  providers:
    opencode:
      type: opencode_cli
      command: "nonexistent-cli"
      timeout_s: 300
  roles:
    planner:
      provider: opencode
      model: "gpt-4o"
"""
        config_path = tmp_path / "llm.yaml"
        config_path.write_text(config_content)

        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = check_config(str(config_path))

        # Should have warnings about unavailable provider
        assert len(result["warnings"]) > 0
        assert any("unavailable" in w for w in result["warnings"])

    def test_config_with_invalid_role(self, tmp_path):
        """Error when role references invalid provider."""
        config_content = """
llm:
  default_role: planner
  providers:
    openrouter:
      type: openrouter_http
      base_url: "https://openrouter.ai/api/v1"
      api_key_env: "OPENROUTER_API_KEY"
  roles:
    planner:
      provider: missing_provider
      model: "gpt-4o"
"""
        config_path = tmp_path / "llm.yaml"
        config_path.write_text(config_content)

        result = check_config(str(config_path))

        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert any("not found" in e for e in result["errors"])

    def test_config_multiple_providers_and_roles(self, tmp_path):
        """Check config with multiple providers and roles."""
        config_content = """
llm:
  default_role: planner
  providers:
    openrouter:
      type: openrouter_http
      base_url: "https://openrouter.ai/api/v1"
      api_key_env: "OPENROUTER_API_KEY"
      timeout_s: 120
    opencode:
      type: opencode_cli
      command: "opencode"
      timeout_s: 300
  roles:
    planner:
      provider: openrouter
      model: "gpt-4o"
    coder:
      provider: opencode
      model: "gpt-4o"
"""
        config_path = tmp_path / "llm.yaml"
        config_path.write_text(config_content)

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                result = check_config(str(config_path))

        assert len(result["providers"]) == 2
        assert len(result["roles"]) == 2
        assert "openrouter" in result["providers"]
        assert "opencode" in result["providers"]
        assert "planner" in result["roles"]
        assert "coder" in result["roles"]

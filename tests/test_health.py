"""Tests for LLM provider health checks."""

import json
from unittest.mock import MagicMock, patch

import pytest

from lib.llm.health import (
    HealthCheckResult,
    ProviderHealth,
    check_all_providers,
    check_provider_health,
    format_health_status,
    print_health_json,
)


class TestProviderHealth:
    """Test ProviderHealth dataclass."""

    def test_healthy_provider(self):
        """Should create healthy provider status."""
        health = ProviderHealth(
            provider_id="test_provider",
            provider_type="openrouter_http",
            healthy=True,
            latency_ms=150,
            model_tested="gpt-4o",
        )

        assert health.provider_id == "test_provider"
        assert health.healthy is True
        assert health.latency_ms == 150
        assert health.error is None

    def test_unhealthy_provider(self):
        """Should create unhealthy provider status."""
        health = ProviderHealth(
            provider_id="broken_provider",
            provider_type="opencode_cli",
            healthy=False,
            error="Connection timeout",
            latency_ms=5000,
        )

        assert health.provider_id == "broken_provider"
        assert health.healthy is False
        assert health.error == "Connection timeout"


class TestHealthCheckResult:
    """Test HealthCheckResult dataclass."""

    def test_all_healthy(self):
        """Should report all healthy."""
        providers = [
            ProviderHealth("p1", "http", True, latency_ms=100),
            ProviderHealth("p2", "cli", True, latency_ms=200),
        ]

        result = HealthCheckResult(
            config_path="config.yaml",
            providers=providers,
            overall_healthy=True,
            total_checks=2,
            healthy_count=2,
            unhealthy_count=0,
        )

        assert result.overall_healthy is True
        assert result.healthy_count == 2
        assert result.unhealthy_count == 0

    def test_some_unhealthy(self):
        """Should report some unhealthy."""
        providers = [
            ProviderHealth("p1", "http", True, latency_ms=100),
            ProviderHealth("p2", "cli", False, error="Failed"),
        ]

        result = HealthCheckResult(
            config_path="config.yaml",
            providers=providers,
            overall_healthy=False,
            total_checks=2,
            healthy_count=1,
            unhealthy_count=1,
        )

        assert result.overall_healthy is False
        assert result.healthy_count == 1
        assert result.unhealthy_count == 1


class TestCheckProviderHealth:
    """Test provider health checking."""

    def test_healthy_provider_check(self):
        """Should successfully check healthy provider."""
        # Mock client and response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "OK"

        mock_client.complete.return_value = mock_response
        mock_client.config.roles = {}

        # Check health
        health = check_provider_health(
            provider_id="test_provider",
            provider_type="openrouter_http",
            model="gpt-4o",
            client=mock_client,
            timeout_s=10,
        )

        # Verify
        assert health.healthy is True
        assert health.provider_id == "test_provider"
        assert health.provider_type == "openrouter_http"
        assert health.model_tested == "gpt-4o"
        assert health.latency_ms is not None
        assert health.latency_ms >= 0  # Mocked calls may have 0ms latency
        assert health.error is None

    def test_unhealthy_provider_check(self):
        """Should detect unhealthy provider."""
        # Mock client that raises exception
        mock_client = MagicMock()
        mock_client.complete.side_effect = Exception("Connection failed")
        mock_client.config.roles = {}

        # Check health
        health = check_provider_health(
            provider_id="broken_provider",
            provider_type="opencode_cli",
            model="gpt-4o",
            client=mock_client,
            timeout_s=10,
        )

        # Verify
        assert health.healthy is False
        assert health.error == "Connection failed"
        assert health.model_tested is None

    def test_empty_response_unhealthy(self):
        """Should treat empty response as unhealthy."""
        # Mock client with empty response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = ""

        mock_client.complete.return_value = mock_response
        mock_client.config.roles = {}

        # Check health
        health = check_provider_health(
            provider_id="empty_provider",
            provider_type="http",
            model="test-model",
            client=mock_client,
        )

        # Verify
        assert health.healthy is False
        assert health.error == "Empty response from provider"

    def test_whitespace_only_response_unhealthy(self):
        """Should treat whitespace-only response as unhealthy."""
        # Mock client with whitespace response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "   \n  \t  "

        mock_client.complete.return_value = mock_response
        mock_client.config.roles = {}

        # Check health
        health = check_provider_health(
            provider_id="ws_provider",
            provider_type="http",
            model="test-model",
            client=mock_client,
        )

        # Verify
        assert health.healthy is False
        assert health.error == "Empty response from provider"


class TestCheckAllProviders:
    """Test checking all providers."""

    @patch("lib.llm.health.load_config")
    @patch("lib.llm.health.LLMClient")
    def test_check_all_providers_success(self, mock_client_class, mock_load_config):
        """Should check all configured providers."""
        from lib.llm.config import LLMConfig, ProviderConfig, RoleConfig

        # Mock configuration
        config = LLMConfig(
            default_role="planner",
            providers={
                "p1": ProviderConfig(provider_id="p1", type="http", config={}),
                "p2": ProviderConfig(provider_id="p2", type="cli", config={}),
            },
            roles={
                "role1": RoleConfig(
                    role="role1", provider="p1", model="model1", temperature=0.2
                ),
                "role2": RoleConfig(
                    role="role2", provider="p2", model="model2", temperature=0.2
                ),
            },
        )
        mock_load_config.return_value = config

        # Mock client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "OK"
        mock_client.complete.return_value = mock_response
        mock_client.config = config
        mock_client_class.return_value = mock_client

        # Check all providers
        result = check_all_providers("config.yaml", timeout_s=5)

        # Verify
        assert result.total_checks == 2
        assert result.healthy_count == 2
        assert result.unhealthy_count == 0
        assert result.overall_healthy is True
        assert len(result.providers) == 2

    @patch("lib.llm.health.load_config")
    @patch("lib.llm.health.LLMClient")
    def test_check_specific_provider(self, mock_client_class, mock_load_config):
        """Should check only specific provider."""
        from lib.llm.config import LLMConfig, ProviderConfig, RoleConfig

        # Mock configuration
        config = LLMConfig(
            default_role="planner",
            providers={
                "p1": ProviderConfig(provider_id="p1", type="http", config={}),
                "p2": ProviderConfig(provider_id="p2", type="cli", config={}),
            },
            roles={
                "role1": RoleConfig(
                    role="role1", provider="p1", model="model1", temperature=0.2
                ),
            },
        )
        mock_load_config.return_value = config

        # Mock client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "OK"
        mock_client.complete.return_value = mock_response
        mock_client.config = config
        mock_client_class.return_value = mock_client

        # Check specific provider
        result = check_all_providers("config.yaml", specific_provider="p1")

        # Verify
        assert result.total_checks == 1
        assert result.providers[0].provider_id == "p1"

    @patch("lib.llm.health.load_config")
    def test_provider_not_found(self, mock_load_config):
        """Should handle provider not found."""
        from lib.llm.config import LLMConfig

        # Mock configuration
        config = LLMConfig(
            default_role="planner",
            providers={},
            roles={},
        )
        mock_load_config.return_value = config

        # Check non-existent provider
        result = check_all_providers("config.yaml", specific_provider="nonexistent")

        # Verify
        assert result.total_checks == 0
        assert result.overall_healthy is False

    @patch("lib.llm.health.load_config")
    @patch("lib.llm.health.LLMClient")
    def test_provider_no_role_configured(self, mock_client_class, mock_load_config):
        """Should handle provider with no configured role."""
        from lib.llm.config import LLMConfig, ProviderConfig

        # Mock configuration with provider but no role using it
        config = LLMConfig(
            default_role="planner",
            providers={
                "unused": ProviderConfig(
                    provider_id="unused", type="http", config={}
                ),
            },
            roles={},  # No roles
        )
        mock_load_config.return_value = config

        # Mock client
        mock_client = MagicMock()
        mock_client.config = config
        mock_client_class.return_value = mock_client

        # Check provider
        result = check_all_providers("config.yaml")

        # Verify
        assert result.total_checks == 1
        assert result.providers[0].healthy is False
        assert "No role configured" in result.providers[0].error


class TestFormatHealthStatus:
    """Test health status formatting."""

    def test_format_healthy(self):
        """Should format healthy status."""
        assert format_health_status(True) == "✓"

    def test_format_unhealthy(self):
        """Should format unhealthy status."""
        assert format_health_status(False) == "✗"


class TestPrintHealthJson:
    """Test JSON output."""

    def test_json_output_format(self, capsys):
        """Should output valid JSON."""
        providers = [
            ProviderHealth(
                provider_id="test",
                provider_type="http",
                healthy=True,
                latency_ms=100,
                model_tested="gpt-4o",
            ),
        ]

        result = HealthCheckResult(
            config_path="config.yaml",
            providers=providers,
            overall_healthy=True,
            total_checks=1,
            healthy_count=1,
            unhealthy_count=0,
        )

        print_health_json(result)

        captured = capsys.readouterr()
        data = json.loads(captured.out)

        assert data["overall_healthy"] is True
        assert data["total_checks"] == 1
        assert data["healthy_count"] == 1
        assert len(data["providers"]) == 1
        assert data["providers"][0]["provider_id"] == "test"
        assert data["providers"][0]["healthy"] is True
        assert data["providers"][0]["latency_ms"] == 100


class TestHealthCheckIntegration:
    """Test health check integration scenarios."""

    @patch("lib.llm.health.load_config")
    @patch("lib.llm.health.LLMClient")
    def test_mixed_health_status(self, mock_client_class, mock_load_config):
        """Should handle mix of healthy and unhealthy providers."""
        from lib.llm.config import LLMConfig, ProviderConfig, RoleConfig

        # Mock configuration
        config = LLMConfig(
            default_role="planner",
            providers={
                "healthy": ProviderConfig(
                    provider_id="healthy", type="http", config={}
                ),
                "broken": ProviderConfig(
                    provider_id="broken", type="cli", config={}
                ),
            },
            roles={
                "role1": RoleConfig(
                    role="role1",
                    provider="healthy",
                    model="model1",
                    temperature=0.2,
                ),
                "role2": RoleConfig(
                    role="role2", provider="broken", model="model2", temperature=0.2
                ),
            },
        )
        mock_load_config.return_value = config

        # Mock client - healthy for p1, error for p2
        mock_client = MagicMock()
        mock_client.config = config

        def complete_side_effect(*args, **kwargs):
            role = kwargs.get("role", "")
            if "healthy" in role:
                response = MagicMock()
                response.text = "OK"
                return response
            else:
                raise Exception("Provider error")

        mock_client.complete.side_effect = complete_side_effect
        mock_client_class.return_value = mock_client

        # Check all providers
        result = check_all_providers("config.yaml")

        # Verify
        assert result.total_checks == 2
        assert result.healthy_count == 1
        assert result.unhealthy_count == 1
        assert result.overall_healthy is False

        # Find results by provider
        healthy_result = next(
            p for p in result.providers if p.provider_id == "healthy"
        )
        broken_result = next(p for p in result.providers if p.provider_id == "broken")

        assert healthy_result.healthy is True
        assert broken_result.healthy is False
        assert "Provider error" in broken_result.error

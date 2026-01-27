"""Tests for LLM client logic."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from lib.llm import LLMClient
from lib.llm.config import LLMConfig, ProviderConfig, RoleConfig
from lib.llm.response import LLMResponse


def create_test_config() -> tuple[Path, LLMConfig]:
    """Create a test configuration file and object."""
    config_data = {
        "llm": {
            "default_role": "planner",
            "providers": {
                "openrouter": {
                    "type": "openrouter_http",
                    "base_url": "https://openrouter.ai/api/v1",
                    "api_key_env": "TEST_API_KEY",
                    "timeout_s": 120,
                }
            },
            "roles": {
                "planner": {
                    "provider": "openrouter",
                    "model": "anthropic/claude-sonnet-4",
                    "temperature": 0.2,
                    "max_tokens": 4000,
                    "json_mode": True,
                },
                "coder": {
                    "provider": "openrouter",
                    "model": "anthropic/claude-sonnet-4",
                    "temperature": 0.1,
                    "max_tokens": 8000,
                },
            },
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    # Also create config object
    config = LLMConfig(
        default_role="planner",
        providers={
            "openrouter": ProviderConfig(
                provider_id="openrouter",
                type="openrouter_http",
                config={
                    "base_url": "https://openrouter.ai/api/v1",
                    "api_key_env": "TEST_API_KEY",
                    "timeout_s": 120,
                },
            )
        },
        roles={
            "planner": RoleConfig(
                role="planner",
                provider="openrouter",
                model="anthropic/claude-sonnet-4",
                temperature=0.2,
                max_tokens=4000,
                json_mode=True,
            ),
            "coder": RoleConfig(
                role="coder",
                provider="openrouter",
                model="anthropic/claude-sonnet-4",
                temperature=0.1,
                max_tokens=8000,
            ),
        },
    )

    return config_path, config


@patch.dict("os.environ", {"TEST_API_KEY": "test-key-123"})
def test_client_from_config():
    """Test loading client from config file."""
    config_path, _ = create_test_config()

    try:
        client = LLMClient.from_config(config_path)
        assert client.config is not None
        assert "planner" in client.config.roles
        assert "coder" in client.config.roles
    finally:
        config_path.unlink()


def test_client_missing_config():
    """Test loading client from non-existent config."""
    with pytest.raises(FileNotFoundError):
        LLMClient.from_config("/nonexistent/config.yaml")


@patch.dict("os.environ", {"TEST_API_KEY": "test-key-123"})
@patch("lib.llm.client.get_provider")
@patch("lib.llm.client.record_trace")
def test_role_routing(mock_record_trace, mock_get_provider):
    """Test that role routing works correctly."""
    _, config = create_test_config()
    client = LLMClient(config)

    # Mock provider
    mock_provider = Mock()
    mock_provider.complete.return_value = LLMResponse(
        text="Test response",
        provider="openrouter",
        model="anthropic/claude-sonnet-4",
        request_id="test-123",
        elapsed_ms=100,
    )
    mock_get_provider.return_value = mock_provider

    # Call with planner role
    response = client.complete(
        role="planner",
        messages=[{"role": "user", "content": "Test prompt"}],
    )

    # Verify provider was called with correct config
    assert mock_provider.complete.called
    call_args = mock_provider.complete.call_args
    request = call_args[0][0]
    provider_config = call_args[0][1]

    assert request.role == "planner"
    assert request.json_mode is True  # From role config
    assert request.max_tokens == 4000  # From role config
    assert request.temperature == 0.2  # From role config
    assert provider_config["model"] == "anthropic/claude-sonnet-4"


@patch.dict("os.environ", {"TEST_API_KEY": "test-key-123"})
@patch("lib.llm.client.get_provider")
@patch("lib.llm.client.record_trace")
def test_call_time_overrides(mock_record_trace, mock_get_provider):
    """Test that call-time parameters override role defaults."""
    _, config = create_test_config()
    client = LLMClient(config)

    # Mock provider
    mock_provider = Mock()
    mock_provider.complete.return_value = LLMResponse(
        text="Test response",
        provider="openrouter",
        model="anthropic/claude-sonnet-4",
        request_id="test-123",
        elapsed_ms=100,
    )
    mock_get_provider.return_value = mock_provider

    # Call with overrides
    response = client.complete(
        role="planner",
        messages=[{"role": "user", "content": "Test prompt"}],
        max_tokens=2000,  # Override
        temperature=0.5,  # Override
        json_mode=False,  # Override
    )

    # Verify overrides were applied
    call_args = mock_provider.complete.call_args
    request = call_args[0][0]

    assert request.max_tokens == 2000
    assert request.temperature == 0.5
    assert request.json_mode is False


@patch.dict("os.environ", {"TEST_API_KEY": "test-key-123"})
def test_unknown_role():
    """Test calling with unknown role fails."""
    _, config = create_test_config()
    client = LLMClient(config)

    with pytest.raises(ValueError, match="Role 'nonexistent' not found"):
        client.complete(
            role="nonexistent",
            messages=[{"role": "user", "content": "Test"}],
        )


@patch.dict("os.environ", {"TEST_API_KEY": "test-key-123"})
@patch("lib.llm.client.get_provider")
@patch("lib.llm.client.record_trace")
@patch("lib.llm.client.record_error_trace")
def test_error_recording(mock_error_trace, mock_record_trace, mock_get_provider):
    """Test that errors are recorded in traces."""
    _, config = create_test_config()
    client = LLMClient(config)

    # Mock provider to raise error
    mock_provider = Mock()
    mock_provider.complete.side_effect = ValueError("Test error")
    mock_get_provider.return_value = mock_provider

    # Call should raise error
    with pytest.raises(ValueError, match="Test error"):
        client.complete(
            role="planner",
            messages=[{"role": "user", "content": "Test"}],
        )

    # Verify error trace was recorded
    assert mock_error_trace.called

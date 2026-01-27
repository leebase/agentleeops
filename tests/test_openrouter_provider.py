"""Tests for OpenRouter HTTP provider."""

import json
from unittest.mock import Mock, patch

import pytest
import requests

from lib.llm.providers.openrouter import OpenRouterProvider
from lib.llm.response import LLMRequest


@pytest.fixture
def provider():
    """Create OpenRouter provider instance."""
    return OpenRouterProvider()


@pytest.fixture
def base_config():
    """Create base provider configuration."""
    return {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "TEST_API_KEY",
        "timeout_s": 120,
        "model": "anthropic/claude-sonnet-4",
    }


@pytest.fixture
def base_request():
    """Create base LLM request."""
    return LLMRequest(
        role="planner",
        messages=[{"role": "user", "content": "Test prompt"}],
    )


def test_validate_config_valid(provider, base_config):
    """Test validation of valid config."""
    with patch.dict("os.environ", {"TEST_API_KEY": "test-key"}):
        # Should not raise
        provider.validate_config(base_config)


def test_validate_config_missing_field(provider):
    """Test validation with missing required field."""
    config = {
        "base_url": "https://openrouter.ai/api/v1",
        # Missing api_key_env
    }

    with pytest.raises(ValueError, match="missing required fields"):
        provider.validate_config(config)


def test_validate_config_missing_env_var(provider, base_config):
    """Test validation with missing environment variable."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="Missing environment variable: TEST_API_KEY"):
            provider.validate_config(base_config)


@patch("lib.llm.providers.openrouter.requests.post")
@patch.dict("os.environ", {"TEST_API_KEY": "test-key-123"})
def test_successful_completion(mock_post, provider, base_config, base_request):
    """Test successful completion request."""
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "Test response content"
                }
            }
        ],
        "model": "anthropic/claude-sonnet-4",
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        },
    }
    mock_post.return_value = mock_response

    response = provider.complete(base_request, base_config)

    assert response.text == "Test response content"
    assert response.provider == "openrouter"
    assert response.model == "anthropic/claude-sonnet-4"
    assert response.usage["total_tokens"] == 30
    assert response.elapsed_ms >= 0  # May be 0 in mocked tests


@patch("lib.llm.providers.openrouter.requests.post")
@patch.dict("os.environ", {"TEST_API_KEY": "test-key-123"})
def test_json_mode(mock_post, provider, base_config, base_request):
    """Test that JSON mode sets correct request format."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": '{"key": "value"}'}}],
        "model": "anthropic/claude-sonnet-4",
    }
    mock_post.return_value = mock_response

    # Enable JSON mode
    base_request.json_mode = True

    response = provider.complete(base_request, base_config)

    # Verify request payload included response_format
    call_args = mock_post.call_args
    payload = call_args[1]["json"]
    assert "response_format" in payload
    assert payload["response_format"]["type"] == "json_object"


@patch("lib.llm.providers.openrouter.requests.post")
@patch.dict("os.environ", {"TEST_API_KEY": "test-key-123"})
def test_usage_with_cost(mock_post, provider, base_config, base_request):
    """Test that cost info is extracted when available."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Response"}}],
        "model": "anthropic/claude-sonnet-4",
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 200,
            "total_tokens": 300,
            "total_cost": 0.05,
        },
    }
    mock_post.return_value = mock_response

    response = provider.complete(base_request, base_config)

    assert response.usage["total_cost"] == 0.05


@patch("lib.llm.providers.openrouter.requests.post")
@patch.dict("os.environ", {"TEST_API_KEY": "test-key-123"})
def test_http_401_error(mock_post, provider, base_config, base_request):
    """Test handling of authentication error."""
    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.raise_for_status.side_effect = requests.HTTPError(
        response=mock_response
    )
    mock_post.return_value = mock_response

    with pytest.raises(requests.HTTPError, match="Authentication failed"):
        provider.complete(base_request, base_config)


@patch("lib.llm.providers.openrouter.requests.post")
@patch.dict("os.environ", {"TEST_API_KEY": "test-key-123"})
def test_http_429_error(mock_post, provider, base_config, base_request):
    """Test handling of rate limit error."""
    mock_response = Mock()
    mock_response.status_code = 429
    mock_response.raise_for_status.side_effect = requests.HTTPError(
        response=mock_response
    )
    mock_post.return_value = mock_response

    with pytest.raises(requests.HTTPError, match="Rate limit exceeded"):
        provider.complete(base_request, base_config)


@patch("lib.llm.providers.openrouter.requests.post")
@patch.dict("os.environ", {"TEST_API_KEY": "test-key-123"})
def test_timeout_error(mock_post, provider, base_config, base_request):
    """Test handling of timeout."""
    mock_post.side_effect = requests.Timeout("Connection timeout")

    with pytest.raises(requests.Timeout, match="Request timed out"):
        provider.complete(base_request, base_config)


@patch.dict("os.environ", {}, clear=True)
def test_missing_api_key(provider, base_config, base_request):
    """Test that missing API key produces clear error."""
    with pytest.raises(ValueError, match="Missing environment variable: TEST_API_KEY"):
        provider.complete(base_request, base_config)


def test_missing_model(provider, base_request):
    """Test that missing model produces clear error."""
    config = {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "TEST_API_KEY",
        # Missing model
    }

    with patch.dict("os.environ", {"TEST_API_KEY": "test-key"}):
        with pytest.raises(ValueError, match="Model not specified"):
            provider.complete(base_request, config)


@patch("lib.llm.providers.openrouter.requests.post")
@patch.dict("os.environ", {"TEST_API_KEY": "test-key-123"})
def test_malformed_response(mock_post, provider, base_config, base_request):
    """Test handling of malformed API response."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        # Missing choices
        "model": "anthropic/claude-sonnet-4",
    }
    mock_post.return_value = mock_response

    with pytest.raises(ValueError, match="No choices in OpenRouter response"):
        provider.complete(base_request, base_config)


@patch("lib.llm.providers.openrouter.requests.post")
@patch.dict("os.environ", {"TEST_API_KEY": "test-key-123"})
def test_parameter_merging(mock_post, provider, base_config, base_request):
    """Test that request parameters are merged with config defaults."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Response"}}],
        "model": "anthropic/claude-sonnet-4",
    }
    mock_post.return_value = mock_response

    # Set request-level overrides
    base_request.temperature = 0.5
    base_request.max_tokens = 2000

    provider.complete(base_request, base_config)

    # Verify merged parameters in request
    call_args = mock_post.call_args
    payload = call_args[1]["json"]
    assert payload["temperature"] == 0.5
    assert payload["max_tokens"] == 2000

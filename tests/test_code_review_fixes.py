"""Tests for Sprint 17 code review fixes.

Tests for the 5 issues identified in codereview/codexReview17.md:
1. Lazy provider validation
2. Dynamic log field extraction
3. JSON repair metadata
4. Large prompt handling (stdin)
5. Raw output in traces
"""

import json
import logging
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from lib.llm import LLMClient
from lib.llm.config import LLMConfig, ProviderConfig, RoleConfig, load_config
from lib.llm.response import LLMResponse, LLMRequest
from lib.llm.trace import record_trace
from lib.logger import JsonFormatter


class TestLazyProviderValidation:
    """Test Issue 1: Lazy provider validation."""

    def test_config_loads_with_missing_api_key(self):
        """Config should load even with missing OPENROUTER_API_KEY."""
        config_data = {
            "llm": {
                "default_role": "planner",
                "providers": {
                    "openrouter": {
                        "type": "openrouter_http",
                        "base_url": "https://openrouter.ai/api/v1",
                        "api_key_env": "MISSING_OPENROUTER_API_KEY",
                    },
                    "opencode": {
                        "type": "opencode_cli",
                        "command": "opencode",
                    },
                },
                "roles": {
                    "test": {"provider": "opencode", "model": "gpt-4o"},
                },
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            # Should NOT raise ValueError during config load
            config = load_config(config_path)
            assert config is not None
            assert "openrouter" in config.providers
            assert "opencode" in config.providers
        finally:
            config_path.unlink()

    def test_validation_happens_on_first_use(self):
        """Validation should occur when provider is actually used."""
        config = LLMConfig(
            default_role="test",
            providers={
                "broken": ProviderConfig(
                    provider_id="broken",
                    type="openrouter_http",
                    config={
                        "base_url": "http://localhost",
                        "api_key_env": "MISSING_KEY",
                    },
                )
            },
            roles={
                "test": RoleConfig(
                    role="test",
                    provider="broken",
                    model="gpt-4o",
                )
            },
        )

        client = LLMClient(config, workspace=None)

        # Should fail on first complete() call, not during client creation
        with pytest.raises(ValueError, match="not properly configured"):
            client.complete(role="test", messages=[{"role": "user", "content": "test"}])

    def test_validated_providers_cached(self):
        """Validated providers should be cached to avoid re-validation."""
        config = LLMConfig(
            default_role="test",
            providers={
                "opencode_cli": ProviderConfig(  # Use matching key
                    provider_id="opencode_cli",
                    type="opencode_cli",
                    config={"command": "opencode"},
                )
            },
            roles={
                "test": RoleConfig(
                    role="test",
                    provider="opencode_cli",
                    model="gpt-4o",
                )
            },
        )

        client = LLMClient(config, workspace=None)

        # Initially empty
        assert len(client._validated_providers) == 0

        # After first validation attempt, should be cached (even if complete() fails for other reasons)
        with patch("lib.llm.providers.opencode_cli.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="test response", stderr="")
            try:
                client.complete(role="test", messages=[{"role": "user", "content": "test"}])
            except Exception:
                pass  # May fail for other reasons (like missing workspace), but validation should succeed

        # Should be cached now (validation happened successfully)
        assert "opencode_cli" in client._validated_providers


class TestDynamicLogFieldExtraction:
    """Test Issue 2: Dynamic log field extraction."""

    def test_json_formatter_includes_all_extra_fields(self):
        """JsonFormatter should include all extra fields dynamically."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add extra fields
        record.event = "llm.complete.start"
        record.role = "planner"
        record.provider = "openrouter"
        record.request_id = "req-123"
        record.model = "gpt-4o"
        record.json_mode = True
        record.max_tokens = 4000

        output = formatter.format(record)
        data = json.loads(output)

        # All extra fields should be present
        assert data["event"] == "llm.complete.start"
        assert data["role"] == "planner"
        assert data["provider"] == "openrouter"
        assert data["request_id"] == "req-123"
        assert data["model"] == "gpt-4o"
        assert data["json_mode"] is True
        assert data["max_tokens"] == 4000

    def test_json_formatter_handles_complex_objects(self):
        """JsonFormatter should handle complex objects like dicts."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test",
            args=(),
            exc_info=None,
        )

        # Add complex object
        record.usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}

        output = formatter.format(record)
        data = json.loads(output)

        assert data["usage"]["prompt_tokens"] == 100
        assert data["usage"]["completion_tokens"] == 50
        assert data["usage"]["total_tokens"] == 150


class TestJSONRepairMetadata:
    """Test Issue 3: JSON repair metadata tracking."""

    def test_response_has_repair_metadata_fields(self):
        """LLMResponse should have repair metadata fields."""
        response = LLMResponse(
            text='{"key": "value"}',
            provider="opencode_cli",
            model="gpt-4o",
            json_repair_applied=True,
            json_repair_method="trailing_commas",
        )

        assert response.json_repair_applied is True
        assert response.json_repair_method == "trailing_commas"

    def test_response_defaults_to_no_repair(self):
        """LLMResponse should default to no repair."""
        response = LLMResponse(
            text='{"key": "value"}',
            provider="opencode_cli",
            model="gpt-4o",
        )

        assert response.json_repair_applied is False
        assert response.json_repair_method is None

    def test_cli_provider_captures_repair_metadata(self):
        """CLI providers should capture repair metadata."""
        from lib.llm.providers.opencode_cli import OpenCodeCLIProvider

        provider = OpenCodeCLIProvider()
        request = LLMRequest(
            role="test",
            messages=[{"role": "user", "content": "Generate JSON"}],
            json_mode=True,
        )

        # Mock CLI response with trailing comma (needs repair)
        with patch("lib.llm.providers.opencode_cli.subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout='{"key": "value",}',  # Trailing comma
                stderr="",
            )

            response = provider.complete(
                request, {"model": "gpt-4o", "command": "opencode"}
            )

        # Should have repair metadata
        assert response.json_repair_applied is True
        assert response.json_repair_method == "trailing_commas"


class TestLargePromptHandling:
    """Test Issue 4: Large prompt handling via stdin."""

    def test_small_prompt_uses_argv(self):
        """Small prompts should use argv."""
        from lib.llm.providers.opencode_cli import OpenCodeCLIProvider

        provider = OpenCodeCLIProvider()
        request = LLMRequest(
            role="test",
            messages=[{"role": "user", "content": "Short prompt"}],
        )

        with patch("lib.llm.providers.opencode_cli.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="response", stderr="")

            provider.complete(request, {"model": "gpt-4o", "command": "opencode"})

            # Check that prompt was passed as arg, not stdin
            call_args = mock_run.call_args
            assert call_args[1]["input"] is None  # stdin not used
            assert "Short prompt" in call_args[0][0]  # in command args

    def test_large_prompt_uses_stdin(self):
        """Large prompts should use stdin."""
        from lib.llm.providers.opencode_cli import OpenCodeCLIProvider

        provider = OpenCodeCLIProvider()

        # Create a large prompt (>100KB)
        large_content = "x" * 150_000
        request = LLMRequest(
            role="test",
            messages=[{"role": "user", "content": large_content}],
        )

        with patch("lib.llm.providers.opencode_cli.subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="response", stderr="")

            provider.complete(request, {"model": "gpt-4o", "command": "opencode"})

            # Check that stdin was used
            call_args = mock_run.call_args
            assert call_args[1]["input"] is not None  # stdin used
            assert large_content not in " ".join(call_args[0][0])  # not in command args


class TestRawOutputInTraces:
    """Test Issue 5: Raw output in trace files."""

    def test_trace_includes_raw_output(self):
        """Trace files should include raw provider output."""
        request = LLMRequest(
            role="test",
            messages=[{"role": "user", "content": "test"}],
        )

        response = LLMResponse(
            text="parsed response",
            provider="opencode_cli",
            model="gpt-4o",
            raw={"stdout": "raw stdout", "stderr": "raw stderr"},
            json_repair_applied=True,
            json_repair_method="markdown_extraction",
        )

        role_cfg = RoleConfig(
            role="test",
            provider="opencode_cli",
            model="gpt-4o",
        )

        provider_cfg = ProviderConfig(
            provider_id="opencode_cli",
            type="opencode_cli",
            config={},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            trace_file = record_trace(
                request, response, role_cfg, provider_cfg, workspace=Path(tmpdir)
            )

            # Read trace file
            with open(trace_file) as f:
                trace_data = json.load(f)

            # Should have raw output
            assert "raw" in trace_data["response"]
            assert trace_data["response"]["raw"]["stdout"] == "raw stdout"
            assert trace_data["response"]["raw"]["stderr"] == "raw stderr"

            # Should have repair metadata
            assert trace_data["response"]["json_repair_applied"] is True
            assert trace_data["response"]["json_repair_method"] == "markdown_extraction"

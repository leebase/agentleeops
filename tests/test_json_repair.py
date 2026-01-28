"""Tests for lib/llm/json_repair.py - JSON repair strategies."""

import json
import pytest
from lib.llm.json_repair import (
    remove_trailing_commas,
    quote_keys,
    convert_single_quotes,
    extract_from_markdown,
    repair_json,
    safe_repair_json,
)


class TestRemoveTrailingCommas:
    """Test trailing comma removal."""

    def test_trailing_comma_in_object(self):
        """Remove trailing comma before closing brace."""
        result = remove_trailing_commas('{"key": "value",}')
        assert result == '{"key": "value"}'

    def test_trailing_comma_in_array(self):
        """Remove trailing comma before closing bracket."""
        result = remove_trailing_commas('[1, 2, 3,]')
        assert result == '[1, 2, 3]'

    def test_nested_trailing_commas(self):
        """Remove trailing commas in nested structures."""
        result = remove_trailing_commas('{"a": [1, 2,], "b": 3,}')
        assert result == '{"a": [1, 2], "b": 3}'

    def test_no_trailing_commas(self):
        """Leave valid JSON unchanged."""
        result = remove_trailing_commas('{"key": "value"}')
        assert result == '{"key": "value"}'


class TestQuoteKeys:
    """Test key quoting."""

    def test_unquoted_keys(self):
        """Quote unquoted object keys."""
        result = quote_keys('{key: "value"}')
        assert result == '{"key": "value"}'

    def test_multiple_unquoted_keys(self):
        """Quote multiple unquoted keys."""
        result = quote_keys('{key1: "value1", key2: "value2"}')
        assert result == '{"key1": "value1", "key2": "value2"}'

    def test_already_quoted_keys(self):
        """Leave quoted keys unchanged."""
        result = quote_keys('{"key": "value"}')
        assert result == '{"key": "value"}'


class TestConvertSingleQuotes:
    """Test single quote conversion."""

    def test_single_quotes_to_double(self):
        """Convert single quotes to double quotes."""
        result = convert_single_quotes("{'key': 'value'}")
        assert result == '{"key": "value"}'

    def test_already_double_quotes(self):
        """Leave double quotes unchanged."""
        result = convert_single_quotes('{"key": "value"}')
        assert result == '{"key": "value"}'


class TestExtractFromMarkdown:
    """Test markdown extraction."""

    def test_extract_json_code_block(self):
        """Extract JSON from ```json marker."""
        text = '```json\n{"key": "value"}\n```'
        result = extract_from_markdown(text)
        assert result == '{"key": "value"}'

    def test_extract_generic_code_block(self):
        """Extract from generic ``` marker."""
        text = '```\n{"key": "value"}\n```'
        result = extract_from_markdown(text)
        assert result == '{"key": "value"}'

    def test_extract_with_json_language_marker(self):
        """Extract when language marker is on first line."""
        text = '```\njson\n{"key": "value"}\n```'
        result = extract_from_markdown(text)
        assert result == '{"key": "value"}'

    def test_no_markdown(self):
        """Return unchanged if no markdown."""
        text = '{"key": "value"}'
        result = extract_from_markdown(text)
        assert result == '{"key": "value"}'


class TestRepairJson:
    """Test repair_json main function."""

    def test_already_valid_json(self):
        """Return valid JSON unchanged."""
        text = '{"key": "value"}'
        result, was_repaired, method = repair_json(text)
        assert result == text
        assert was_repaired is False
        assert method == "none"
        # Verify it's actually valid
        json.loads(result)

    def test_markdown_extraction(self):
        """Repair JSON wrapped in markdown."""
        text = '```json\n{"key": "value"}\n```'
        result, was_repaired, method = repair_json(text)
        assert was_repaired is True
        assert method == "markdown_extraction"
        assert json.loads(result) == {"key": "value"}

    def test_trailing_commas(self):
        """Repair JSON with trailing commas."""
        text = '{"key": "value",}'
        result, was_repaired, method = repair_json(text)
        assert was_repaired is True
        assert method == "trailing_commas"
        assert json.loads(result) == {"key": "value"}

    def test_unquoted_keys(self):
        """Repair JSON with unquoted keys."""
        text = '{key: "value"}'
        result, was_repaired, method = repair_json(text)
        assert was_repaired is True
        assert method == "quote_keys"
        assert json.loads(result) == {"key": "value"}

    def test_single_quotes(self):
        """Repair JSON with single quotes."""
        text = "{'key': 'value'}"
        result, was_repaired, method = repair_json(text)
        assert was_repaired is True
        assert method == "single_to_double_quotes"
        assert json.loads(result) == {"key": "value"}

    def test_combined_issues(self):
        """Repair JSON with multiple issues."""
        text = "{key: 'value',}"
        result, was_repaired, method = repair_json(text)
        assert was_repaired is True
        # Should use one of the combined strategies
        assert json.loads(result) == {"key": "value"}

    def test_unrepairable_json(self):
        """Raise ValueError for unrepairable JSON."""
        text = '{"key": broken}'
        with pytest.raises(ValueError) as exc_info:
            repair_json(text)
        assert "Unable to repair JSON" in str(exc_info.value)

    def test_nested_objects(self):
        """Repair nested JSON with trailing commas."""
        text = '{"outer": {"inner": "value",},}'
        result, was_repaired, method = repair_json(text)
        assert was_repaired is True
        assert json.loads(result) == {"outer": {"inner": "value"}}

    def test_arrays(self):
        """Repair JSON arrays with trailing commas."""
        text = '{"items": [1, 2, 3,]}'
        result, was_repaired, method = repair_json(text)
        assert was_repaired is True
        assert json.loads(result) == {"items": [1, 2, 3]}


class TestSafeRepairJson:
    """Test safe_repair_json wrapper."""

    def test_successful_repair(self):
        """Return repaired JSON on success."""
        text = '{"key": "value",}'
        result, error, was_repaired, method = safe_repair_json(text)
        assert error == ""
        assert was_repaired is True
        assert method == "trailing_commas"
        assert json.loads(result) == {"key": "value"}

    def test_repair_failure(self):
        """Return error on failure."""
        text = '{"key": broken}'
        result, error, was_repaired, method = safe_repair_json(text)
        assert result == ""
        assert "Unable to repair JSON" in error
        assert was_repaired is False
        assert method == ""

    def test_no_repair_needed(self):
        """Return original JSON if valid."""
        text = '{"key": "value"}'
        result, error, was_repaired, method = safe_repair_json(text)
        assert error == ""
        assert was_repaired is False
        assert method == "none"
        assert result == text


class TestRealWorldExamples:
    """Test real-world CLI output examples."""

    def test_opencode_cli_output(self):
        """Repair typical OpenCode CLI JSON output."""
        text = '''Here's the JSON:
```json
{
  "stories": [
    {"id": "s1", "title": "Story 1"},
    {"id": "s2", "title": "Story 2"},
  ],
}
```'''
        result, was_repaired, method = repair_json(text)
        assert was_repaired is True
        data = json.loads(result)
        assert len(data["stories"]) == 2

    def test_gemini_cli_output(self):
        """Repair typical Gemini CLI JSON output."""
        text = "```\n{title: 'Test Story', complexity: 'M'}\n```"
        result, was_repaired, method = repair_json(text)
        assert was_repaired is True
        data = json.loads(result)
        assert data["title"] == "Test Story"

    def test_claude_api_json_mode(self):
        """Already valid JSON from Claude API."""
        text = '{"key": "value"}'
        result, was_repaired, method = repair_json(text)
        assert was_repaired is False
        assert method == "none"

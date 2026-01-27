"""Tests for LLM syntax validation."""
import pytest
from lib.syntax_guard import (
    validate_python,
    validate_json,
    safe_extract_python,
    safe_extract_json,
    extract_code_block,
)


class TestValidatePython:
    """Tests for Python syntax validation."""

    def test_valid_python_passes(self):
        """Valid Python code should pass validation."""
        is_valid, err = validate_python("def foo():\n    return 42")
        assert is_valid
        assert err == ""

    def test_invalid_python_fails(self):
        """Invalid Python should fail with error message."""
        is_valid, err = validate_python("def foo( return 42")
        assert not is_valid
        assert err != ""

    def test_empty_string_passes(self):
        """Empty string is valid Python."""
        is_valid, err = validate_python("")
        assert is_valid


class TestValidateJson:
    """Tests for JSON syntax validation."""

    def test_valid_json_passes(self):
        """Valid JSON should pass validation."""
        is_valid, err = validate_json('{"key": "value"}')
        assert is_valid
        assert err == ""

    def test_invalid_json_fails(self):
        """Invalid JSON should fail with error message."""
        is_valid, err = validate_json('{key: value}')
        assert not is_valid
        assert err != ""

    def test_array_json_passes(self):
        """JSON arrays should pass validation."""
        is_valid, err = validate_json('[1, 2, 3]')
        assert is_valid


class TestExtractCodeBlock:
    """Tests for code block extraction."""

    def test_extracts_python_block(self):
        """Should extract code from python code block."""
        response = "Here's the code:\n```python\ndef add(a, b):\n    return a + b\n```"
        code = extract_code_block(response, "python")
        assert "def add" in code
        assert "```" not in code

    def test_extracts_generic_block(self):
        """Should extract code from generic code block."""
        response = "Here:\n```\nsome code\n```"
        code = extract_code_block(response, "python")
        assert code == "some code"

    def test_returns_raw_when_no_block(self):
        """Should return stripped text when no code block."""
        response = "  def foo(): pass  "
        code = extract_code_block(response, "python")
        assert code == "def foo(): pass"


class TestSafeExtractPython:
    """Tests for safe Python extraction."""

    def test_prose_rejection(self):
        """Prose (non-code) should be rejected."""
        code, err = safe_extract_python("I cannot help with that request.")
        assert err != ""
        assert code == ""

    def test_valid_code_extracted(self):
        """Valid Python code should be extracted."""
        response = "```python\ndef foo():\n    return 42\n```"
        code, err = safe_extract_python(response)
        assert err == ""
        assert "def foo" in code

    def test_raw_valid_code_accepted(self):
        """Raw valid Python (no code block) should be accepted."""
        code, err = safe_extract_python("def foo(): pass")
        assert err == ""
        assert code == "def foo(): pass"


class TestSafeExtractJson:
    """Tests for safe JSON extraction."""

    def test_valid_json_extracted(self):
        """Valid JSON should be extracted."""
        response = '```json\n{"stories": []}\n```'
        content, err = safe_extract_json(response)
        assert err == ""
        assert '"stories"' in content

    def test_invalid_json_rejected(self):
        """Invalid JSON should be rejected."""
        response = "```json\n{invalid}\n```"
        content, err = safe_extract_json(response)
        assert err != ""
        assert content == ""

    def test_raw_valid_json_accepted(self):
        """Raw valid JSON (no code block) should be accepted."""
        content, err = safe_extract_json('{"key": "value"}')
        assert err == ""

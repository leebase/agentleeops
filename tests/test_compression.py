"""Tests for prompt compression functionality."""

import pytest

from lib.llm.compression import (
    compress_prompt,
    compress_json,
    remove_excessive_whitespace,
    remove_comments,
    truncate_long_strings,
    extract_key_sections,
    should_compress,
    auto_compress_messages,
)


class TestWhitespaceCompression:
    """Test whitespace normalization."""

    def test_remove_multiple_spaces(self):
        """Should replace multiple spaces with single space."""
        text = "Hello    world     test"
        result = remove_excessive_whitespace(text)
        assert result == "Hello world test"

    def test_remove_excessive_blank_lines(self):
        """Should limit consecutive blank lines to 2."""
        text = "Line 1\n\n\n\n\nLine 2"
        result = remove_excessive_whitespace(text)
        assert result == "Line 1\n\nLine 2"

    def test_remove_trailing_whitespace(self):
        """Should remove trailing whitespace from lines."""
        text = "Line 1    \nLine 2  \n   Line 3"
        result = remove_excessive_whitespace(text)
        # Multiple spaces are collapsed to single space
        assert result == "Line 1\nLine 2\n Line 3"

    def test_preserve_single_spaces(self):
        """Should preserve normal spacing."""
        text = "Normal text with proper spacing"
        result = remove_excessive_whitespace(text)
        assert result == text


class TestCommentRemoval:
    """Test comment removal."""

    def test_remove_python_comments(self):
        """Should remove Python inline comments."""
        text = """
def foo():
    x = 1  # This is a comment
    y = 2  # Another comment
    return x + y
"""
        result = remove_comments(text, language="python")
        assert "# This is a comment" not in result
        assert "# Another comment" not in result
        assert "def foo():" in result
        assert "x = 1" in result

    def test_preserve_python_docstrings(self):
        """Should preserve Python docstrings."""
        text = '''
def foo():
    """This is a docstring."""
    return 42
'''
        result = remove_comments(text, language="python")
        assert '"""This is a docstring."""' in result

    def test_remove_javascript_comments(self):
        """Should remove JavaScript comments."""
        text = """
function foo() {
    // Single line comment
    const x = 1;
    /* Multi-line
       comment */
    return x;
}
"""
        result = remove_comments(text, language="javascript")
        assert "// Single line comment" not in result
        assert "/* Multi-line" not in result
        assert "const x = 1;" in result


class TestStringTruncation:
    """Test string truncation."""

    def test_truncate_long_strings(self):
        """Should truncate very long strings."""
        text = 'x = "' + "a" * 200 + '"'
        result = truncate_long_strings(text, max_length=100)
        assert "... [truncated]" in result
        assert len(result) < len(text)

    def test_preserve_short_strings(self):
        """Should not truncate short strings."""
        text = 'x = "short string"'
        result = truncate_long_strings(text, max_length=100)
        assert result == text


class TestJSONCompression:
    """Test JSON compression."""

    def test_compress_valid_json(self):
        """Should minify valid JSON."""
        text = """
{
    "key": "value",
    "nested": {
        "item": 123
    }
}
"""
        result = compress_json(text)
        assert "\n" not in result
        assert "  " not in result
        assert '"key":"value"' in result

    def test_handle_invalid_json(self):
        """Should return original text for invalid JSON."""
        text = "This is not JSON"
        result = compress_json(text)
        assert result == text


class TestKeyExtraction:
    """Test key section extraction."""

    def test_extract_from_large_text(self):
        """Should extract key sections from large text."""
        text = "A" * 10000 + "B" * 10000 + "C" * 10000
        result = extract_key_sections(text, max_chars=5000)

        assert len(result) < len(text)
        assert "[middle section compressed" in result
        assert "A" in result  # Header
        assert "C" in result  # Footer

    def test_preserve_small_text(self):
        """Should not extract from small text."""
        text = "Short text"
        result = extract_key_sections(text, max_chars=5000)
        assert result == text


class TestCompressPrompt:
    """Test main compression function."""

    def test_whitespace_strategy(self):
        """Should apply whitespace compression only."""
        text = "Test    text\n\n\n\nwith    spaces"
        result = compress_prompt(text, strategy="whitespace")

        assert result.original_size == len(text)
        assert result.compressed_size < result.original_size
        assert result.compression_ratio > 0
        assert result.method == "whitespace"

    def test_aggressive_strategy(self):
        """Should apply aggressive compression."""
        text = """
def foo():
    # Comment to remove
    x = 1  # Another comment
    y = "very long string " * 100
    return x + y
"""
        result = compress_prompt(text, strategy="aggressive", preserve_code=True)

        assert result.compressed_size < result.original_size
        assert "# Comment" not in result.compressed_text
        assert "comments" in result.method

    def test_smart_strategy_medium_text(self):
        """Smart strategy should apply appropriate compression for medium text."""
        text = "def foo():\n    # comment\n    " + "x = 1\n" * 200
        result = compress_prompt(text, strategy="smart")

        assert result.compressed_size < result.original_size
        assert "whitespace" in result.method

    def test_smart_strategy_large_text(self):
        """Smart strategy should extract sections for very large text."""
        text = "A" * 60000
        result = compress_prompt(text, strategy="smart")

        assert result.compressed_size < result.original_size
        assert "extract" in result.method

    def test_extract_strategy(self):
        """Should extract key sections."""
        text = "Start " + ("middle " * 10000) + "End"
        result = compress_prompt(text, strategy="extract", max_size=1000)

        assert result.compressed_size < result.original_size
        assert "[middle section compressed" in result.compressed_text

    def test_tokens_saved_calculation(self):
        """Should estimate tokens saved."""
        text = "A" * 1000
        result = compress_prompt(text, strategy="whitespace")

        # Rough estimate: 1 token ≈ 4 characters
        expected_tokens = (result.original_size - result.compressed_size) // 4
        assert result.tokens_saved == expected_tokens


class TestShouldCompress:
    """Test compression threshold detection."""

    def test_small_text_no_compression(self):
        """Small text should not need compression."""
        text = "Short message"
        assert not should_compress(text, threshold=10000)

    def test_large_text_needs_compression(self):
        """Large text should need compression."""
        text = "A" * 15000
        assert should_compress(text, threshold=10000)

    def test_custom_threshold(self):
        """Should respect custom threshold."""
        text = "A" * 5000
        assert not should_compress(text, threshold=10000)
        assert should_compress(text, threshold=1000)


class TestAutoCompressMessages:
    """Test automatic message compression."""

    def test_compress_large_messages(self):
        """Should compress messages exceeding threshold."""
        # Create large message with compressible content (whitespace)
        large_content = ("Line with content    \n\n\n\n" * 1000)
        messages = [
            {"role": "user", "content": "Small message"},
            {"role": "user", "content": large_content},  # Large message with whitespace
            {"role": "user", "content": "Another small message"},
        ]

        compressed_messages, results = auto_compress_messages(
            messages, threshold=10000, strategy="whitespace"
        )

        assert len(compressed_messages) == 3
        assert len(results) == 1  # Only one message compressed
        assert compressed_messages[0]["content"] == "Small message"  # Unchanged
        assert len(compressed_messages[1]["content"]) < len(large_content)  # Compressed

    def test_preserve_message_structure(self):
        """Should preserve message role and structure."""
        messages = [
            {"role": "system", "content": "A" * 15000},
            {"role": "user", "content": "test"},
        ]

        compressed_messages, results = auto_compress_messages(messages, threshold=10000)

        assert compressed_messages[0]["role"] == "system"
        assert compressed_messages[1]["role"] == "user"

    def test_no_compression_needed(self):
        """Should not compress if all messages are small."""
        messages = [
            {"role": "user", "content": "Small message 1"},
            {"role": "user", "content": "Small message 2"},
        ]

        compressed_messages, results = auto_compress_messages(messages, threshold=10000)

        assert len(results) == 0
        assert compressed_messages == messages


class TestCompressionIntegration:
    """Test compression integration scenarios."""

    def test_code_compression(self):
        """Should compress code while preserving structure."""
        code = """
def calculate_fibonacci(n):
    \"\"\"Calculate fibonacci number.\"\"\"
    if n <= 0:
        return 0   # Base case
    elif n == 1:
        return 1   # Base case
    else:
        return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

# Full line comment
for i in range(10):
    print(f"fib({i}) = {calculate_fibonacci(i)}")
"""
        result = compress_prompt(code, strategy="aggressive", preserve_code=True)

        # Should preserve docstring and code structure
        assert '"""Calculate fibonacci number."""' in result.compressed_text
        assert "def calculate_fibonacci" in result.compressed_text
        assert "for i in range(10)" in result.compressed_text
        # Compression should reduce size through comment removal and whitespace
        assert result.compressed_size < result.original_size

    def test_json_data_compression(self):
        """Should compress JSON data."""
        json_text = """
{
    "users": [
        {
            "name": "Alice",
            "age": 30
        },
        {
            "name": "Bob",
            "age": 25
        }
    ]
}
"""
        result = compress_prompt(json_text, strategy="smart")

        assert result.compressed_size < result.original_size
        assert "json" in result.method or "whitespace" in result.method

"""Prompt compression for large LLM inputs.

Provides strategies for compressing large prompts to reduce token usage
and improve performance while maintaining semantic meaning.
"""

import re
from dataclasses import dataclass
from typing import Callable


@dataclass
class CompressionResult:
    """Result of prompt compression."""

    original_text: str
    compressed_text: str
    original_size: int
    compressed_size: int
    compression_ratio: float
    method: str
    tokens_saved: int = 0


# Compression strategies


def remove_excessive_whitespace(text: str) -> str:
    """Remove excessive whitespace while preserving structure.

    Args:
        text: Input text

    Returns:
        Text with normalized whitespace
    """
    # Replace multiple spaces with single space
    text = re.sub(r" +", " ", text)

    # Replace multiple blank lines with max 2
    text = re.sub(r"\n\n\n+", "\n\n", text)

    # Remove trailing whitespace from lines
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Remove leading/trailing whitespace
    text = text.strip()

    return text


def remove_comments(text: str, language: str = "auto") -> str:
    """Remove code comments from text.

    Args:
        text: Input text
        language: Language hint ("python", "javascript", "auto")

    Returns:
        Text with comments removed
    """
    if language == "auto":
        # Detect language by presence of certain patterns
        if "def " in text or "import " in text or "class " in text:
            language = "python"
        elif "function " in text or "const " in text or "let " in text:
            language = "javascript"

    if language == "python":
        # Remove Python comments (preserve docstrings)
        lines = []
        in_docstring = False
        docstring_char = None

        for line in text.split("\n"):
            stripped = line.strip()

            # Check for docstring start/end
            if stripped.startswith('"""') or stripped.startswith("'''"):
                if not in_docstring:
                    in_docstring = True
                    docstring_char = stripped[:3]
                elif stripped.endswith(docstring_char):
                    in_docstring = False
                lines.append(line)
                continue

            if in_docstring:
                lines.append(line)
                continue

            # Remove inline comments
            if "#" in line:
                # Don't remove # inside strings
                code_part = line.split("#")[0]
                if code_part.strip():
                    lines.append(code_part.rstrip())
            else:
                lines.append(line)

        text = "\n".join(lines)

    elif language == "javascript":
        # Remove JS comments
        # Remove single-line comments
        text = re.sub(r"//.*?$", "", text, flags=re.MULTILINE)
        # Remove multi-line comments
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)

    return text


def truncate_long_strings(text: str, max_length: int = 100) -> str:
    """Truncate very long string literals in code.

    Args:
        text: Input text
        max_length: Maximum length for strings

    Returns:
        Text with truncated strings
    """
    # Find long string literals and truncate them
    def truncate_match(match):
        quote = match.group(1)
        content = match.group(2)
        if len(content) > max_length:
            return f"{quote}{content[:max_length]}... [truncated]{quote}"
        return match.group(0)

    # Match strings (both single and double quoted)
    text = re.sub(r'(["\'])(.+?)\1', truncate_match, text, flags=re.DOTALL)

    return text


def compress_json(text: str) -> str:
    """Compress JSON by removing unnecessary whitespace.

    Args:
        text: Input JSON text

    Returns:
        Minified JSON
    """
    try:
        import json

        # Try to parse as JSON
        data = json.loads(text)
        # Compact format (no extra spaces)
        return json.dumps(data, separators=(",", ":"))
    except (json.JSONDecodeError, ValueError):
        # Not valid JSON, return as-is
        return text


def extract_key_sections(text: str, max_chars: int = 5000) -> str:
    """Extract key sections from very large text.

    Keeps the beginning, end, and tries to identify important middle sections.

    Args:
        text: Input text
        max_chars: Target maximum characters

    Returns:
        Extracted key sections
    """
    if len(text) <= max_chars:
        return text

    # Calculate section sizes
    header_size = max_chars // 3
    footer_size = max_chars // 3
    middle_size = max_chars - header_size - footer_size

    # Extract sections
    header = text[:header_size]
    footer = text[-footer_size:]

    # Try to extract meaningful middle section
    middle_start = len(text) // 2 - middle_size // 2
    middle_end = middle_start + middle_size
    middle = text[middle_start:middle_end]

    # Combine with indicators
    compressed = f"{header}\n\n... [middle section compressed, ~{len(text) - max_chars} chars omitted] ...\n\n{middle}\n\n... [continuing] ...\n\n{footer}"

    return compressed


# Main compression function


def compress_prompt(
    text: str,
    strategy: str = "smart",
    preserve_code: bool = True,
    max_size: int | None = None,
) -> CompressionResult:
    """Compress a prompt using specified strategy.

    Args:
        text: Input text to compress
        strategy: Compression strategy:
            - "smart": Apply multiple compression techniques intelligently
            - "whitespace": Only normalize whitespace
            - "aggressive": Remove comments, normalize whitespace, truncate strings
            - "extract": Extract key sections (for very large inputs)
        preserve_code: Try to preserve code structure and readability
        max_size: Maximum target size in characters (for "extract" strategy)

    Returns:
        CompressionResult with original and compressed text
    """
    original_text = text
    original_size = len(text)
    compressed_text = text
    methods_used = []

    if strategy == "whitespace":
        compressed_text = remove_excessive_whitespace(compressed_text)
        methods_used.append("whitespace")

    elif strategy == "aggressive":
        # Remove comments
        if preserve_code:
            compressed_text = remove_comments(compressed_text)
            methods_used.append("comments")

        # Normalize whitespace
        compressed_text = remove_excessive_whitespace(compressed_text)
        methods_used.append("whitespace")

        # Truncate long strings
        compressed_text = truncate_long_strings(compressed_text)
        methods_used.append("strings")

    elif strategy == "extract":
        # Extract key sections for very large inputs
        target_size = max_size or 10000
        compressed_text = extract_key_sections(compressed_text, max_chars=target_size)
        methods_used.append("extract")

    elif strategy == "smart":
        # Smart compression: apply techniques based on content
        size = len(text)

        # Always normalize whitespace
        compressed_text = remove_excessive_whitespace(compressed_text)
        methods_used.append("whitespace")

        # For medium-large prompts, remove comments
        if size > 5000 and preserve_code:
            compressed_text = remove_comments(compressed_text)
            methods_used.append("comments")

        # For very large prompts, extract key sections
        if size > 50000:
            target_size = max_size or 15000
            compressed_text = extract_key_sections(compressed_text, max_chars=target_size)
            methods_used.append("extract")

        # Try to detect and compress JSON
        if "{" in compressed_text and "}" in compressed_text:
            try_compressed = compress_json(compressed_text)
            if len(try_compressed) < len(compressed_text):
                compressed_text = try_compressed
                methods_used.append("json")

    else:
        raise ValueError(f"Unknown compression strategy: {strategy}")

    compressed_size = len(compressed_text)
    compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0

    # Estimate tokens saved (rough: 1 token ≈ 4 characters)
    tokens_saved = (original_size - compressed_size) // 4

    return CompressionResult(
        original_text=original_text,
        compressed_text=compressed_text,
        original_size=original_size,
        compressed_size=compressed_size,
        compression_ratio=compression_ratio,
        method="+".join(methods_used) if methods_used else strategy,
        tokens_saved=tokens_saved,
    )


def should_compress(text: str, threshold: int = 10000) -> bool:
    """Determine if text should be compressed.

    Args:
        text: Input text
        threshold: Size threshold in characters (default: 10KB)

    Returns:
        True if text should be compressed
    """
    return len(text) > threshold


def auto_compress_messages(
    messages: list[dict[str, str]],
    threshold: int = 10000,
    strategy: str = "smart",
) -> tuple[list[dict[str, str]], list[CompressionResult]]:
    """Automatically compress large messages in a message list.

    Args:
        messages: List of message dictionaries
        threshold: Size threshold for compression
        strategy: Compression strategy to use

    Returns:
        Tuple of (compressed messages, compression results)
    """
    compressed_messages = []
    compression_results = []

    for msg in messages:
        content = msg.get("content", "")

        if should_compress(content, threshold):
            result = compress_prompt(content, strategy=strategy)
            compressed_msg = msg.copy()
            compressed_msg["content"] = result.compressed_text
            compressed_messages.append(compressed_msg)
            compression_results.append(result)
        else:
            compressed_messages.append(msg)

    return compressed_messages, compression_results

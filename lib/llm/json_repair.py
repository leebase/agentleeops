"""
JSON Repair - Multi-strategy repair for malformed JSON from LLM CLI output.

This module attempts to repair common JSON syntax issues that occur when
CLI tools output JSON with trailing commas, unquoted keys, or wrapped in
markdown code blocks.
"""

import json
import re
from typing import Tuple


def remove_trailing_commas(text: str) -> str:
    """
    Remove trailing commas before closing braces/brackets.

    Example: {"key": "value",} -> {"key": "value"}
    """
    # Remove commas before closing braces
    text = re.sub(r',\s*}', '}', text)
    # Remove commas before closing brackets
    text = re.sub(r',\s*]', ']', text)
    return text


def quote_keys(text: str) -> str:
    """
    Quote unquoted object keys.

    Example: {key: "value"} -> {"key": "value"}

    Note: This is a simple heuristic and may not handle all cases.
    """
    # Match unquoted keys followed by colon
    # Pattern: word characters followed by optional whitespace and colon
    text = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', text)
    return text


def convert_single_quotes(text: str) -> str:
    """
    Convert single quotes to double quotes.

    Example: {'key': 'value'} -> {"key": "value"}

    Warning: This is naive and will fail if strings contain quotes.
    Only use as last resort.
    """
    return text.replace("'", '"')


def extract_from_markdown(text: str) -> str:
    """
    Extract JSON from markdown code block.

    Example:
        ```json
        {"key": "value"}
        ```
    -> {"key": "value"}
    """
    # Look for ```json marker
    if '```json' in text:
        parts = text.split('```json')
        if len(parts) > 1:
            content = parts[1].split('```')[0].strip()
            return content

    # Look for generic ``` marker
    if '```' in text:
        parts = text.split('```')
        if len(parts) >= 3:
            # Take first code block
            content = parts[1].strip()
            # Remove language marker if present
            lines = content.split('\n')
            if lines and lines[0].strip() in ['json', 'JSON']:
                content = '\n'.join(lines[1:])
            return content

    return text


def repair_json(text: str) -> Tuple[str, bool, str]:
    """
    Attempt to repair malformed JSON using multiple strategies.

    Args:
        text: Potentially malformed JSON string

    Returns:
        Tuple of (repaired_json, was_repaired, repair_method)
        - repaired_json: Valid JSON string
        - was_repaired: True if any repair was applied
        - repair_method: Name of successful repair strategy

    Raises:
        ValueError: If JSON is unrepairable

    Strategies (in order):
    1. Validate as-is (may already be valid)
    2. Extract from markdown code block
    3. Remove trailing commas
    4. Quote unquoted keys
    5. Convert single quotes to double quotes
    """
    # Strategy 1: Try as-is
    try:
        json.loads(text)
        return text, False, "none"
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from markdown
    extracted = extract_from_markdown(text)
    if extracted != text:
        try:
            json.loads(extracted)
            return extracted, True, "markdown_extraction"
        except json.JSONDecodeError:
            # Continue with extracted text for further repair
            text = extracted

    # Strategy 3: Remove trailing commas
    no_trailing = remove_trailing_commas(text)
    try:
        json.loads(no_trailing)
        return no_trailing, True, "trailing_commas"
    except json.JSONDecodeError:
        pass

    # Strategy 4: Quote unquoted keys (on original or comma-fixed text)
    quoted = quote_keys(no_trailing)
    try:
        json.loads(quoted)
        return quoted, True, "quote_keys"
    except json.JSONDecodeError:
        pass

    # Strategy 5: Convert single quotes (last resort, most fragile)
    double_quoted = convert_single_quotes(no_trailing)
    try:
        json.loads(double_quoted)
        return double_quoted, True, "single_to_double_quotes"
    except json.JSONDecodeError:
        pass

    # Try combining quote_keys and single quote conversion
    combined = convert_single_quotes(quoted)
    try:
        json.loads(combined)
        return combined, True, "quote_keys_and_single_quotes"
    except json.JSONDecodeError:
        pass

    # All strategies failed
    raise ValueError(f"Unable to repair JSON after trying all strategies")


def safe_repair_json(text: str) -> Tuple[str, str, bool, str]:
    """
    Safe wrapper around repair_json that never raises.

    Args:
        text: Potentially malformed JSON string

    Returns:
        Tuple of (json_str, error, was_repaired, repair_method)
        - json_str: Repaired JSON or empty string on failure
        - error: Error message or empty string on success
        - was_repaired: True if any repair was applied
        - repair_method: Name of repair strategy or empty on failure
    """
    try:
        repaired, was_repaired, method = repair_json(text)
        return repaired, "", was_repaired, method
    except ValueError as e:
        return "", str(e), False, ""
    except Exception as e:
        return "", f"Unexpected error: {e}", False, ""

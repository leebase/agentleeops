"""
Syntax Guard - Validates LLM output before writing to disk.

Prevents "LLM Refusal Injection" where model responds with prose instead of code.
This is Sprint 12 deliverable for Robustness & LLM Guards.
"""

import ast
import json
from typing import Tuple


def validate_python(code: str) -> Tuple[bool, str]:
    """
    Validate Python code syntax.

    Args:
        code: Python source code to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"


def validate_json(content: str) -> Tuple[bool, str]:
    """
    Validate JSON syntax.

    Args:
        content: JSON string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        json.loads(content)
        return True, ""
    except json.JSONDecodeError as e:
        return False, f"Line {e.lineno}: {e.msg}"


def extract_code_block(llm_response: str, language: str = "python") -> str:
    """
    Extract code from markdown code block.

    Args:
        llm_response: Full LLM response text
        language: Language marker to look for (default: python)

    Returns:
        Extracted code content
    """
    marker = f"```{language}"
    if marker in llm_response:
        code = llm_response.split(marker)[1].split("```")[0].strip()
        return code
    elif "```" in llm_response:
        # Generic code block without language marker
        code = llm_response.split("```")[1].split("```")[0].strip()
        return code
    else:
        # No code block - might be raw code or refusal
        return llm_response.strip()


def safe_extract_python(llm_response: str) -> Tuple[str, str]:
    """
    Extract and validate Python from LLM response.

    Args:
        llm_response: Full LLM response text

    Returns:
        Tuple of (code, error). If error is non-empty, code should not be used.
    """
    code = extract_code_block(llm_response, "python")
    is_valid, error = validate_python(code)
    if not is_valid:
        return "", f"Invalid Python: {error}"
    return code, ""


def safe_extract_json(llm_response: str) -> Tuple[str, str]:
    """
    Extract and validate JSON from LLM response.

    Args:
        llm_response: Full LLM response text

    Returns:
        Tuple of (json_str, error). If error is non-empty, json should not be used.
    """
    content = extract_code_block(llm_response, "json")
    is_valid, error = validate_json(content)
    if not is_valid:
        return "", f"Invalid JSON: {error}"
    return content, ""

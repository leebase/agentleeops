"""
LLM CLI wrapper for AgentLeeOps.
Uses the OpenCode CLI with an optional OpenRouter fallback.
"""

import json
import os
import subprocess
import urllib.error
import urllib.request
from typing import Optional


class LLMError(Exception):
    """Raised when LLM CLI execution fails."""
    pass


# Keep OpenCodeError as alias for backwards compatibility
OpenCodeError = LLMError


def call_opencode(
    prompt: str,
    model: Optional[str] = None,
    timeout: int = 300
) -> str:
    """
    Call OpenCode CLI with a prompt and return the response.

    Args:
        prompt: The prompt to send to Claude
        model: Optional model override for the CLI
        timeout: Timeout in seconds (default 5 minutes)

    Returns:
        The text response from Claude

    Raises:
        LLMError: If OpenCode CLI fails and fallback is unavailable
    """
    if model is None:
        model = os.getenv("OPENCODE_MODEL")

    if model and "/" not in model:
        model = None

    try:
        return _call_opencode_cli(prompt, model=model, timeout=timeout)
    except LLMError as cli_error:
        if os.getenv("OPENROUTER_API_KEY"):
            return _call_openrouter(prompt, timeout=timeout)
        raise cli_error


def call_llm(
    prompt: str,
    model: Optional[str] = None,
    timeout: int = 300
) -> str:
    """
    Alias for call_opencode - calls OpenCode CLI.
    """
    return call_opencode(prompt, model, timeout)


def check_opencode_installed() -> bool:
    """
    Check if OpenCode CLI is installed and accessible.

    Returns:
        True if OpenCode CLI is installed, False otherwise
    """
    try:
        cmd = [
            _get_opencode_cmd(),
            _get_opencode_version_flag(),
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_opencode_auth() -> bool:
    """
    Check if OpenCode CLI is authenticated.

    Returns:
        True if authenticated, False otherwise
    """
    # OpenCode handles auth via its own /connect flow.
    # Just check if it's installed.
    return check_opencode_installed()


def _get_opencode_cmd() -> str:
    return os.getenv("OPENCODE_CMD", "opencode")


def _get_opencode_prompt_flag() -> str:
    return os.getenv("OPENCODE_PROMPT_FLAG", "")


def _get_opencode_model_flag() -> str:
    return os.getenv("OPENCODE_MODEL_FLAG", "--model")


def _get_opencode_version_flag() -> str:
    return os.getenv("OPENCODE_VERSION_FLAG", "--version")


def _get_opencode_subcommand() -> str:
    return os.getenv("OPENCODE_SUBCOMMAND", "run")


def _call_opencode_cli(prompt: str, model: Optional[str], timeout: int) -> str:
    cmd = [_get_opencode_cmd()]
    subcommand = _get_opencode_subcommand()
    if subcommand:
        cmd.append(subcommand)
    prompt_flag = _get_opencode_prompt_flag()
    if prompt_flag:
        cmd.append(prompt_flag)
    if model:
        model_flag = _get_opencode_model_flag()
        if model_flag:
            cmd.extend([model_flag, model])
    if prompt_flag:
        cmd.append(prompt)
    else:
        cmd.append(prompt)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        raise LLMError(
            "OpenCode CLI not found. Install and run /connect in OpenCode."
        )
    except subprocess.TimeoutExpired:
        raise LLMError(f"OpenCode CLI timed out after {timeout} seconds")

    if result.returncode != 0:
        raise LLMError(f"OpenCode CLI failed: {result.stderr}")

    return result.stdout.strip()


def _call_openrouter(prompt: str, timeout: int) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise LLMError("OPENROUTER_API_KEY not set for fallback")

    api_base = os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1")
    model = os.getenv("OPENCODE_FALLBACK_MODEL", "grok-code-fast")
    url = f"{api_base.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise LLMError(f"OpenRouter API error: {detail}")
    except urllib.error.URLError as exc:
        raise LLMError(f"OpenRouter API request failed: {exc}")

    try:
        payload = json.loads(body)
        choices = payload.get("choices", [])
        if not choices:
            raise LLMError("OpenRouter returned no choices")
        return choices[0]["message"]["content"].strip()
    except (KeyError, ValueError, TypeError) as exc:
        raise LLMError(f"OpenRouter response parse failed: {exc}")

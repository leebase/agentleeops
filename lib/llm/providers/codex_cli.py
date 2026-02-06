"""Codex CLI provider implementation."""

import os
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

from ..response import LLMRequest, LLMResponse


class CodexCLIProvider:
    """Codex CLI subprocess provider."""

    id = "codex_cli"

    def validate_config(self, cfg: dict) -> None:
        """Validate Codex CLI configuration."""
        cwd = cfg.get("cwd")
        if cwd:
            cwd_path = Path(cwd).expanduser()
            if not cwd_path.exists() or not cwd_path.is_dir():
                raise ValueError(f"Invalid cwd: {cwd}")

        command = cfg.get("command") or os.getenv("CODEX_CMD", "codex")

        try:
            version_result = subprocess.run(
                [command, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if version_result.returncode != 0:
                raise ValueError(
                    f"Codex CLI command '{command}' failed version check."
                )
        except FileNotFoundError:
            raise ValueError(
                f"Codex CLI not found: '{command}'. Install Codex CLI or set CODEX_CMD."
            )
        except subprocess.TimeoutExpired:
            raise ValueError(
                f"Codex CLI version check timed out for command '{command}'"
            )

        # Validate login state because this provider relies on local auth.
        login_result = subprocess.run(
            [command, "login", "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if login_result.returncode != 0:
            raise ValueError(
                "Codex CLI is not logged in. Run 'codex login' first."
            )

        timeout_s = cfg.get("timeout_s", 300)
        if timeout_s <= 0 or timeout_s > 3600:
            raise ValueError(
                f"Invalid timeout_s: {timeout_s}. Must be between 1 and 3600 seconds."
            )

    def complete(self, request: LLMRequest, config: dict) -> LLMResponse:
        """Execute completion via Codex CLI."""
        model = config.get("model")
        if not model:
            raise ValueError("Model not specified in configuration")

        command = config.get("command") or os.getenv("CODEX_CMD", "codex")
        subcommand = config.get("subcommand", "exec")
        model_flag = config.get("model_flag", "--model")
        output_flag = config.get("output_flag", "--output-last-message")
        timeout_s = config.get("timeout_s", 300)
        extra_args = config.get("args", [])

        if extra_args and not isinstance(extra_args, list):
            raise ValueError("Provider config 'args' must be a list")

        cwd = config.get("cwd")
        if cwd:
            cwd = str(Path(cwd).expanduser().resolve())

        prompt = self._build_prompt(request.messages)
        request_id = str(uuid.uuid4())
        start_time = time.time()

        output_path = None
        try:
            with tempfile.NamedTemporaryFile(prefix="codex-last-", suffix=".txt", delete=False) as tmp:
                output_path = tmp.name

            cmd = [command]
            if subcommand:
                cmd.append(subcommand)
            if model_flag and model:
                cmd.extend([model_flag, model])
            if extra_args:
                cmd.extend([str(arg) for arg in extra_args])
            cmd.extend([output_flag, output_path])

            argv_limit = 100_000
            use_stdin = len(prompt) > argv_limit
            if use_stdin:
                cmd.append("-")
                stdin_input = prompt
            else:
                cmd.append(prompt)
                stdin_input = None

            result = subprocess.run(
                cmd,
                input=stdin_input,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                cwd=cwd,
            )
            elapsed_ms = int((time.time() - start_time) * 1000)

            if result.returncode != 0:
                stderr = result.stderr.strip() if result.stderr else "Unknown error"
                raise RuntimeError(
                    f"Codex CLI failed (exit code {result.returncode}): {stderr}"
                )

            response_text = ""
            if output_path and Path(output_path).exists():
                response_text = Path(output_path).read_text(encoding="utf-8").strip()
            if not response_text:
                response_text = result.stdout.strip()

            json_repair_applied = False
            json_repair_method = None
            if request.json_mode:
                response_text, json_repair_applied, json_repair_method = self._handle_json_mode(response_text)

            return LLMResponse(
                text=response_text,
                provider=self.id,
                model=model,
                usage=None,
                raw={"stdout": result.stdout, "stderr": result.stderr},
                request_id=request_id,
                elapsed_ms=elapsed_ms,
                metadata={"command": " ".join(cmd), "cwd": cwd},
                json_repair_applied=json_repair_applied,
                json_repair_method=json_repair_method,
            )

        except FileNotFoundError:
            raise RuntimeError(
                f"Codex CLI not found: '{command}'. Install Codex CLI or set CODEX_CMD."
            )
        except subprocess.TimeoutExpired as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            raise subprocess.TimeoutExpired(
                cmd=e.cmd,
                timeout=timeout_s,
                output=f"Codex CLI timed out after {elapsed_ms}ms (timeout: {timeout_s}s)",
            )
        finally:
            if output_path:
                try:
                    Path(output_path).unlink(missing_ok=True)
                except Exception:
                    pass

    def _build_prompt(self, messages: list[dict[str, str]]) -> str:
        """Build a single prompt string from message list."""
        if len(messages) == 1 and messages[0].get("role") == "user":
            return messages[0]["content"]

        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                parts.append(f"System: {content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")
            else:
                parts.append(f"User: {content}")

        return "\n\n".join(parts)

    def _handle_json_mode(self, text: str) -> tuple[str, bool, str]:
        """Handle JSON mode output with repair if needed."""
        from lib.llm.json_repair import safe_repair_json

        repaired, error, was_repaired, method = safe_repair_json(text)
        if error:
            raise RuntimeError(
                f"JSON mode enabled but output is not valid JSON: {error}"
            )

        return repaired, was_repaired, method

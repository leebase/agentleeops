"""Enhanced trace recording for LLM calls."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import RoleConfig, ProviderConfig, compute_config_hash
from .response import LLMRequest, LLMResponse


def record_trace(
    request: LLMRequest,
    response: LLMResponse,
    role_cfg: RoleConfig,
    provider_cfg: ProviderConfig,
    workspace: Path | None = None,
) -> Path:
    """Record LLM trace to file.

    Args:
        request: LLM request data
        response: LLM response data
        role_cfg: Role configuration used
        provider_cfg: Provider configuration used
        workspace: Optional workspace path (defaults to current directory)

    Returns:
        Path to trace file
    """
    # Determine trace directory
    if workspace:
        trace_dir = Path(workspace) / ".agentleeops" / "traces"
    else:
        trace_dir = Path(".agentleeops") / "traces"

    # Create dated subdirectory
    date_str = datetime.now().strftime("%Y%m%d")
    trace_dir = trace_dir / date_str
    trace_dir.mkdir(parents=True, exist_ok=True)

    # Build trace data
    trace_data = {
        "request_id": response.request_id,
        "timestamp": datetime.now().isoformat(),
        "role": request.role,
        "provider": response.provider,
        "model": response.model,
        "config_hash": compute_config_hash(role_cfg, provider_cfg),
        "request": {
            "messages": request.messages,
            "json_mode": request.json_mode,
            "schema": request.schema,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "timeout_s": request.timeout_s,
        },
        "response": {
            "text": response.text,
            "usage": response.usage,
            "elapsed_ms": response.elapsed_ms,
        },
        "success": True,
        "metadata": {
            "role_config": {
                "provider": role_cfg.provider,
                "model": role_cfg.model,
                "temperature": role_cfg.temperature,
                "max_tokens": role_cfg.max_tokens,
                "timeout_s": role_cfg.timeout_s,
                "json_mode": role_cfg.json_mode,
            },
            "provider_type": provider_cfg.type,
        },
    }

    # Write trace file
    trace_file = trace_dir / f"{response.request_id}.json"
    with open(trace_file, "w") as f:
        json.dump(trace_data, f, indent=2)

    return trace_file


def record_error_trace(
    request: LLMRequest,
    error: Exception,
    role_cfg: RoleConfig,
    provider_cfg: ProviderConfig,
    elapsed_ms: int,
    workspace: Path | None = None,
) -> Path:
    """Record failed LLM trace to file.

    Args:
        request: LLM request data
        error: Exception that occurred
        role_cfg: Role configuration used
        provider_cfg: Provider configuration used
        elapsed_ms: Time elapsed before failure
        workspace: Optional workspace path

    Returns:
        Path to trace file
    """
    # Determine trace directory
    if workspace:
        trace_dir = Path(workspace) / ".agentleeops" / "traces"
    else:
        trace_dir = Path(".agentleeops") / "traces"

    # Create dated subdirectory
    date_str = datetime.now().strftime("%Y%m%d")
    trace_dir = trace_dir / date_str
    trace_dir.mkdir(parents=True, exist_ok=True)

    # Generate request ID
    import uuid
    request_id = str(uuid.uuid4())

    # Build trace data
    trace_data = {
        "request_id": request_id,
        "timestamp": datetime.now().isoformat(),
        "role": request.role,
        "provider": role_cfg.provider,
        "config_hash": compute_config_hash(role_cfg, provider_cfg),
        "request": {
            "messages": request.messages,
            "json_mode": request.json_mode,
            "schema": request.schema,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "timeout_s": request.timeout_s,
        },
        "error": {
            "type": type(error).__name__,
            "message": str(error),
            "elapsed_ms": elapsed_ms,
        },
        "success": False,
        "metadata": {
            "role_config": {
                "provider": role_cfg.provider,
                "model": role_cfg.model,
                "temperature": role_cfg.temperature,
                "max_tokens": role_cfg.max_tokens,
                "timeout_s": role_cfg.timeout_s,
                "json_mode": role_cfg.json_mode,
            },
            "provider_type": provider_cfg.type,
        },
    }

    # Write trace file
    trace_file = trace_dir / f"{request_id}.json"
    with open(trace_file, "w") as f:
        json.dump(trace_data, f, indent=2)

    return trace_file

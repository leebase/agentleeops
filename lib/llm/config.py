"""LLM configuration loading and resolution."""

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

import yaml

from .providers.registry import get_provider


@dataclass
class RoleConfig:
    """Configuration for a specific role."""

    role: str
    provider: str
    model: str
    temperature: float = 0.2
    max_tokens: int = 4000
    timeout_s: int = 120
    json_mode: bool = False


@dataclass
class ProviderConfig:
    """Configuration for a provider."""

    provider_id: str
    type: str
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMConfig:
    """Complete LLM configuration."""

    default_role: str
    providers: Dict[str, ProviderConfig]
    roles: Dict[str, RoleConfig]


def load_config(path: str | Path) -> LLMConfig:
    """Load and validate LLM configuration from YAML file.

    Args:
        path: Path to YAML configuration file

    Returns:
        Validated LLM configuration

    Raises:
        FileNotFoundError: If config file not found
        ValueError: If configuration is invalid
        yaml.YAMLError: If YAML is malformed
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    if not data or "llm" not in data:
        raise ValueError("Configuration file missing 'llm' section")

    llm_config = data["llm"]

    # Validate required top-level fields
    if "providers" not in llm_config:
        raise ValueError("Configuration missing 'providers' section")
    if "roles" not in llm_config:
        raise ValueError("Configuration missing 'roles' section")

    default_role = llm_config.get("default_role", "planner")

    # Parse providers
    providers = {}
    for provider_id, provider_data in llm_config["providers"].items():
        if "type" not in provider_data:
            raise ValueError(f"Provider '{provider_id}' missing 'type' field")

        providers[provider_id] = ProviderConfig(
            provider_id=provider_id,
            type=provider_data["type"],
            config=provider_data,
        )

    # Parse roles
    roles = {}
    for role_name, role_data in llm_config["roles"].items():
        if "provider" not in role_data:
            raise ValueError(f"Role '{role_name}' missing 'provider' field")
        if "model" not in role_data:
            raise ValueError(f"Role '{role_name}' missing 'model' field")

        provider_id = role_data["provider"]
        if provider_id not in providers:
            raise ValueError(
                f"Role '{role_name}' references unknown provider '{provider_id}'"
            )

        roles[role_name] = RoleConfig(
            role=role_name,
            provider=provider_id,
            model=role_data["model"],
            temperature=role_data.get("temperature", 0.2),
            max_tokens=role_data.get("max_tokens", 4000),
            timeout_s=role_data.get("timeout_s", 120),
            json_mode=role_data.get("json_mode", False),
        )

    config = LLMConfig(
        default_role=default_role,
        providers=providers,
        roles=roles,
    )

    # Validate provider configurations
    for provider_id, provider_cfg in config.providers.items():
        try:
            provider = get_provider(provider_id)
            provider.validate_config(provider_cfg.config)
        except ValueError as e:
            raise ValueError(f"Provider '{provider_id}' validation failed: {e}") from e

    return config


def resolve_role(role: str, config: LLMConfig) -> tuple[RoleConfig, ProviderConfig]:
    """Resolve effective configuration for a role.

    Args:
        role: Role name
        config: LLM configuration

    Returns:
        Tuple of (role config, provider config)

    Raises:
        ValueError: If role not found
    """
    if role not in config.roles:
        available = ", ".join(config.roles.keys())
        raise ValueError(
            f"Role '{role}' not found. Available roles: {available or 'none'}"
        )

    role_cfg = config.roles[role]
    provider_cfg = config.providers[role_cfg.provider]

    return role_cfg, provider_cfg


def compute_config_hash(role_cfg: RoleConfig, provider_cfg: ProviderConfig) -> str:
    """Compute hash of configuration for reproducibility tracking.

    Excludes secrets (API keys) from the hash.

    Args:
        role_cfg: Role configuration
        provider_cfg: Provider configuration

    Returns:
        SHA256 hex digest of configuration
    """
    # Build hashable representation
    config_dict = {
        "role": role_cfg.role,
        "provider": role_cfg.provider,
        "model": role_cfg.model,
        "temperature": role_cfg.temperature,
        "max_tokens": role_cfg.max_tokens,
        "timeout_s": role_cfg.timeout_s,
        "json_mode": role_cfg.json_mode,
        "provider_type": provider_cfg.type,
        # Exclude API keys and other secrets
        "provider_config": {
            k: v
            for k, v in provider_cfg.config.items()
            if "key" not in k.lower() and "secret" not in k.lower() and "token" not in k.lower()
        },
    }

    # Compute SHA256
    config_json = json.dumps(config_dict, sort_keys=True)
    return hashlib.sha256(config_json.encode()).hexdigest()

"""
WorkItem provider configuration loading.

Loads provider configuration from YAML with environment variable expansion.
"""

import os
import re
from pathlib import Path
from typing import Any

import yaml


def expand_env_vars(value: Any) -> Any:
    """
    Recursively expand ${VAR} environment variables in config values.
    
    Args:
        value: Config value (string, dict, list, or other)
        
    Returns:
        Value with env vars expanded
    """
    if isinstance(value, str):
        # Match ${VAR} or $VAR patterns
        pattern = r'\$\{([^}]+)\}|\$([A-Z_][A-Z0-9_]*)'
        
        def replace(match):
            var_name = match.group(1) or match.group(2)
            return os.environ.get(var_name, "")
        
        return re.sub(pattern, replace, value)
    
    elif isinstance(value, dict):
        return {k: expand_env_vars(v) for k, v in value.items()}
    
    elif isinstance(value, list):
        return [expand_env_vars(item) for item in value]
    
    return value


def load_provider_config(config_path: str | Path | None = None) -> dict:
    """
    Load provider configuration from YAML file.
    
    Looks for config in this order:
    1. Explicitly provided path
    2. config/workitem.yaml relative to project root
    3. Returns minimal default config
    
    Environment variables in the format ${VAR} are expanded.
    
    Args:
        config_path: Optional path to config file
        
    Returns:
        Dict with provider configuration
    """
    if config_path is None:
        # Try to find config relative to this file's location
        # lib/workitem/config.py -> project root is ../../..
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "config" / "workitem.yaml"
    
    config_path = Path(config_path)
    
    if not config_path.exists():
        # Return minimal default config from environment
        return {
            "default_provider": "kanboard",
            "providers": {
                "kanboard": {
                    "url": os.environ.get("KANBOARD_URL", "http://localhost:188/jsonrpc.php"),
                    "user": os.environ.get("KANBOARD_USER", "jsonrpc"),
                    "token": os.environ.get("KANBOARD_TOKEN", ""),
                    "project_id": 1,
                    "column_mapping": {},
                }
            }
        }
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    # Expand environment variables
    config = expand_env_vars(config)
    
    return config


def get_provider_config(provider_name: str, config: dict | None = None) -> dict:
    """
    Get configuration for a specific provider.
    
    Args:
        provider_name: Name of the provider (e.g., "kanboard")
        config: Optional pre-loaded config dict
        
    Returns:
        Provider-specific configuration dict
        
    Raises:
        ValueError: If provider not found in config
    """
    if config is None:
        config = load_provider_config()
    
    providers = config.get("providers", {})
    
    if provider_name not in providers:
        raise ValueError(f"Provider '{provider_name}' not found in config")
    
    return providers[provider_name]

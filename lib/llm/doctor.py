"""
LLM Configuration Doctor - Validates LLM configuration and provider availability.

Usage:
    python -m lib.llm.doctor --config config/llm.yaml
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from .config import LLMConfig, ProviderConfig, RoleConfig, load_config


def check_provider(provider_id: str, provider_cfg: ProviderConfig) -> Dict:
    """Check provider availability and configuration.

    Args:
        provider_id: Provider identifier
        provider_cfg: Provider configuration

    Returns:
        Dict with:
        - available: bool
        - error: str (if not available)
        - warnings: list of str
    """
    from .providers import get_provider

    result = {
        "available": False,
        "error": None,
        "warnings": []
    }

    try:
        # Get provider implementation by ID
        provider = get_provider(provider_id)
        if not provider:
            result["error"] = f"Unknown provider: {provider_id}"
            return result

        # Validate configuration
        provider.validate_config(provider_cfg.config)
        result["available"] = True

    except ValueError as e:
        result["error"] = str(e)
    except Exception as e:
        result["error"] = f"Unexpected error: {e}"

    return result


def check_role(role_name: str, role_cfg: RoleConfig, config: LLMConfig, provider_results: Dict) -> Dict:
    """Check role configuration.

    Args:
        role_name: Role name
        role_cfg: Role configuration
        config: Full LLM configuration
        provider_results: Results from provider checks

    Returns:
        Dict with:
        - valid: bool
        - error: str (if invalid)
        - warnings: list of str
    """
    result = {
        "valid": False,
        "error": None,
        "warnings": []
    }

    # Check provider reference exists
    if role_cfg.provider not in config.providers:
        result["error"] = f"Provider '{role_cfg.provider}' not found in configuration"
        return result

    # Check provider is available
    provider_result = provider_results.get(role_cfg.provider, {})
    if not provider_result.get("available"):
        result["error"] = f"Provider '{role_cfg.provider}' is not available"
        return result

    # Check model specified
    if not role_cfg.model:
        result["warnings"].append("No model specified")

    # Validate parameters
    if role_cfg.temperature is not None:
        if role_cfg.temperature < 0 or role_cfg.temperature > 1:
            result["warnings"].append(f"Temperature {role_cfg.temperature} outside normal range [0, 1]")

    if role_cfg.max_tokens is not None:
        if role_cfg.max_tokens <= 0:
            result["error"] = f"max_tokens must be positive, got {role_cfg.max_tokens}"
            return result

    result["valid"] = True
    return result


def check_config(config_path: str) -> Dict:
    """Validate LLM configuration.

    Args:
        config_path: Path to LLM configuration file

    Returns:
        Dict with:
        - valid: bool
        - providers: {provider_id: status}
        - roles: {role_name: status}
        - errors: [str]
        - warnings: [str]
    """
    import yaml
    from pathlib import Path

    result = {
        "valid": False,
        "providers": {},
        "roles": {},
        "errors": [],
        "warnings": []
    }

    # Load configuration - parse YAML directly to avoid validation errors
    try:
        config_file = Path(config_path)
        if not config_file.exists():
            result["errors"].append(f"Configuration file not found: {config_path}")
            return result

        with open(config_file) as f:
            data = yaml.safe_load(f)

        if not data or "llm" not in data:
            result["errors"].append("Configuration file missing 'llm' section")
            return result

        llm_config = data["llm"]

        # Build config objects manually (without validation)
        providers = {}
        for provider_id, provider_data in llm_config.get("providers", {}).items():
            if "type" not in provider_data:
                result["errors"].append(f"Provider '{provider_id}' missing 'type' field")
                continue
            providers[provider_id] = ProviderConfig(
                provider_id=provider_id,
                type=provider_data["type"],
                config=provider_data,
            )

        roles = {}
        for role_name, role_data in llm_config.get("roles", {}).items():
            if "provider" not in role_data:
                result["errors"].append(f"Role '{role_name}' missing 'provider' field")
                continue
            if "model" not in role_data:
                result["errors"].append(f"Role '{role_name}' missing 'model' field")
                continue
            roles[role_name] = RoleConfig(
                role=role_name,
                provider=role_data["provider"],
                model=role_data.get("model"),
                temperature=role_data.get("temperature", 0.2),
                max_tokens=role_data.get("max_tokens", 4000),
                timeout_s=role_data.get("timeout_s", 120),
                json_mode=role_data.get("json_mode", False),
            )

        config = LLMConfig(
            default_role=llm_config.get("default_role", "planner"),
            providers=providers,
            roles=roles,
        )

    except FileNotFoundError:
        result["errors"].append(f"Configuration file not found: {config_path}")
        return result
    except Exception as e:
        result["errors"].append(f"Failed to parse configuration: {e}")
        return result

    # Check providers
    for provider_id, provider_cfg in config.providers.items():
        provider_result = check_provider(provider_id, provider_cfg)
        result["providers"][provider_id] = provider_result

        if not provider_result["available"]:
            result["warnings"].append(
                f"Provider '{provider_id}' unavailable: {provider_result['error']}"
            )

    # Check roles
    for role_name, role_cfg in config.roles.items():
        role_result = check_role(role_name, role_cfg, config, result["providers"])
        result["roles"][role_name] = role_result

        if not role_result["valid"]:
            result["errors"].append(
                f"Role '{role_name}' invalid: {role_result['error']}"
            )

        result["warnings"].extend(role_result.get("warnings", []))

    # Overall validity
    result["valid"] = len(result["errors"]) == 0

    return result


def format_status(available: bool) -> str:
    """Format availability status with emoji."""
    return "✓" if available else "✗"


def print_report(config_path: str, check_result: Dict) -> None:
    """Print configuration validation report.

    Args:
        config_path: Path to configuration file
        check_result: Result from check_config()
    """
    print("LLM Configuration Doctor")
    print("=" * 40)
    print()
    print(f"Config: {config_path}")
    print()

    # Providers section
    print("Providers:")
    for provider_id, provider_result in check_result["providers"].items():
        available = provider_result.get("available", False)
        status = format_status(available)

        # Get provider type if available
        provider_type = ""
        if "providers" in check_result:
            # Load config to get type
            try:
                config = LLMConfig.from_yaml(config_path)
                provider_cfg = config.providers.get(provider_id)
                if provider_cfg:
                    provider_type = f" ({provider_cfg.type})"
            except Exception:
                pass

        print(f"  {status} {provider_id}{provider_type}", end="")

        if available:
            print(" - Available")
        else:
            error = provider_result.get("error", "Unknown error")
            print(f" - {error}")

    print()

    # Roles section
    print("Roles:")
    for role_name, role_result in check_result["roles"].items():
        valid = role_result.get("valid", False)
        status = format_status(valid)

        # Get provider reference
        provider_ref = ""
        try:
            config = load_config(config_path)
            role_cfg = config.roles.get(role_name)
            if role_cfg:
                provider_ref = f" -> {role_cfg.provider}"
        except Exception:
            pass

        print(f"  {status} {role_name}{provider_ref}", end="")

        if valid:
            print()
        else:
            error = role_result.get("error", "Unknown error")
            print(f" - {error}")

    print()

    # Warnings section
    if check_result["warnings"]:
        print("Warnings:")
        for warning in check_result["warnings"]:
            print(f"  - {warning}")
        print()

    # Overall status
    error_count = len(check_result["errors"])
    warning_count = len(check_result["warnings"])

    if check_result["valid"]:
        print("Status: ✓ VALID")
    elif error_count > 0 and warning_count > 0:
        print(f"Status: ✗ INVALID ({warning_count} warning(s), {error_count} error(s))")
    elif warning_count > 0:
        print(f"Status: ⚠ PARTIAL ({warning_count} warning(s))")
    else:
        print(f"Status: ✗ INVALID ({error_count} error(s))")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Validate LLM configuration and provider availability"
    )
    parser.add_argument(
        "--config",
        default="config/llm.yaml",
        help="Path to LLM configuration file (default: config/llm.yaml)"
    )

    args = parser.parse_args()

    # Check configuration
    result = check_config(args.config)

    # Print report
    print_report(args.config, result)

    # Exit with error code if invalid
    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()

"""
LLM Provider Health Checks - Test actual connectivity and responsiveness.

Usage:
    python -m lib.llm.health --config config/llm.yaml
    python -m lib.llm.health --provider openrouter
    python -m lib.llm.health --json
"""

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from lib.logger import get_logger

from .client import LLMClient
from .config import LLMConfig, load_config

logger = get_logger(__name__)


@dataclass
class ProviderHealth:
    """Health status for a provider."""

    provider_id: str
    provider_type: str
    healthy: bool
    latency_ms: int | None = None
    error: str | None = None
    model_tested: str | None = None
    timestamp: str | None = None


@dataclass
class HealthCheckResult:
    """Overall health check result."""

    config_path: str
    providers: list[ProviderHealth]
    overall_healthy: bool
    total_checks: int
    healthy_count: int
    unhealthy_count: int


def check_provider_health(
    provider_id: str,
    provider_type: str,
    model: str,
    client: LLMClient,
    timeout_s: int = 10,
) -> ProviderHealth:
    """Check provider health by making a minimal test request.

    Args:
        provider_id: Provider identifier
        provider_type: Provider type (e.g., "openrouter_http", "opencode_cli")
        model: Model to test with
        client: LLM client instance
        timeout_s: Request timeout in seconds

    Returns:
        ProviderHealth with status information
    """
    from datetime import datetime, timezone

    health = ProviderHealth(
        provider_id=provider_id,
        provider_type=provider_type,
        healthy=False,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    # Create a minimal test request
    test_messages = [
        {"role": "user", "content": "Respond with the single word: OK"}
    ]

    try:
        # Time the request
        start_time = time.time()

        # Create a test role for this provider
        from .config import RoleConfig

        test_role = RoleConfig(
            role=f"_health_check_{provider_id}",
            provider=provider_id,
            model=model,
            temperature=0.0,
            max_tokens=10,
            timeout_s=timeout_s,
            json_mode=False,
        )

        # Temporarily add test role to config
        client.config.roles[test_role.role] = test_role

        try:
            # Execute test request
            response = client.complete(
                role=test_role.role,
                messages=test_messages,
            )

            # Calculate latency
            elapsed_ms = int((time.time() - start_time) * 1000)

            # Check response is valid
            if response.text and len(response.text.strip()) > 0:
                health.healthy = True
                health.latency_ms = elapsed_ms
                health.model_tested = model
            else:
                health.error = "Empty response from provider"
                health.latency_ms = elapsed_ms

        finally:
            # Clean up test role
            del client.config.roles[test_role.role]

    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        health.error = str(e)
        health.latency_ms = elapsed_ms if elapsed_ms > 0 else None

    return health


def check_all_providers(
    config_path: str,
    specific_provider: str | None = None,
    timeout_s: int = 10,
) -> HealthCheckResult:
    """Check health of all configured providers.

    Args:
        config_path: Path to LLM configuration file
        specific_provider: If provided, only check this provider
        timeout_s: Request timeout in seconds

    Returns:
        HealthCheckResult with status for all providers
    """
    # Load configuration
    try:
        config = load_config(config_path)
    except Exception as e:
        # Return empty result with error
        return HealthCheckResult(
            config_path=config_path,
            providers=[],
            overall_healthy=False,
            total_checks=0,
            healthy_count=0,
            unhealthy_count=0,
        )

    # Create client
    client = LLMClient(config, workspace=None, config_path=config_path)

    # Collect providers to check
    providers_to_check = {}
    if specific_provider:
        if specific_provider in config.providers:
            providers_to_check[specific_provider] = config.providers[specific_provider]
        else:
            # Provider not found
            return HealthCheckResult(
                config_path=config_path,
                providers=[],
                overall_healthy=False,
                total_checks=0,
                healthy_count=0,
                unhealthy_count=0,
            )
    else:
        providers_to_check = config.providers

    # Check each provider
    health_results = []
    for provider_id, provider_cfg in providers_to_check.items():
        # Find a role that uses this provider to get model name
        model = None
        for role_name, role_cfg in config.roles.items():
            if role_cfg.provider == provider_id:
                model = role_cfg.model
                break

        if not model:
            # No role uses this provider, skip health check
            health = ProviderHealth(
                provider_id=provider_id,
                provider_type=provider_cfg.type,
                healthy=False,
                error="No role configured for this provider",
            )
        else:
            # Perform health check
            health = check_provider_health(
                provider_id=provider_id,
                provider_type=provider_cfg.type,
                model=model,
                client=client,
                timeout_s=timeout_s,
            )

        health_results.append(health)

    # Calculate summary
    total_checks = len(health_results)
    healthy_count = sum(1 for h in health_results if h.healthy)
    unhealthy_count = total_checks - healthy_count
    overall_healthy = unhealthy_count == 0

    return HealthCheckResult(
        config_path=config_path,
        providers=health_results,
        overall_healthy=overall_healthy,
        total_checks=total_checks,
        healthy_count=healthy_count,
        unhealthy_count=unhealthy_count,
    )


def format_health_status(healthy: bool) -> str:
    """Format health status with emoji."""
    return "✓" if healthy else "✗"


def print_health_report(result: HealthCheckResult) -> None:
    """Print health check report.

    Args:
        result: Health check result
    """
    print("LLM Provider Health Check")
    print("=" * 60)
    print()
    print(f"Config: {result.config_path}")
    print()

    if result.total_checks == 0:
        print("No providers configured or provider not found.")
        return

    # Providers section
    print("Providers:")
    for health in result.providers:
        status = format_health_status(health.healthy)

        print(f"  {status} {health.provider_id} ({health.provider_type})", end="")

        if health.healthy:
            latency = f"{health.latency_ms}ms" if health.latency_ms else "N/A"
            print(f" - Healthy (latency: {latency}, model: {health.model_tested})")
        else:
            error = health.error or "Unknown error"
            latency_info = f" (latency: {health.latency_ms}ms)" if health.latency_ms else ""
            print(f" - Unhealthy: {error}{latency_info}")

    print()

    # Summary
    print(f"Summary: {result.healthy_count}/{result.total_checks} providers healthy")

    if result.overall_healthy:
        print("Status: ✓ ALL HEALTHY")
    else:
        print(f"Status: ✗ {result.unhealthy_count} UNHEALTHY")


def print_health_json(result: HealthCheckResult) -> None:
    """Print health check result as JSON.

    Args:
        result: Health check result
    """
    # Convert to dict
    data = {
        "config_path": result.config_path,
        "overall_healthy": result.overall_healthy,
        "total_checks": result.total_checks,
        "healthy_count": result.healthy_count,
        "unhealthy_count": result.unhealthy_count,
        "providers": [asdict(h) for h in result.providers],
    }

    print(json.dumps(data, indent=2))


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Check health and connectivity of LLM providers"
    )
    parser.add_argument(
        "--config",
        default="config/llm.yaml",
        help="Path to LLM configuration file (default: config/llm.yaml)",
    )
    parser.add_argument(
        "--provider",
        help="Check only specific provider",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Request timeout in seconds (default: 10)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    # Run health checks
    result = check_all_providers(
        config_path=args.config,
        specific_provider=args.provider,
        timeout_s=args.timeout,
    )

    # Print report
    if args.json:
        print_health_json(result)
    else:
        print_health_report(result)

    # Exit with error code if any unhealthy
    sys.exit(0 if result.overall_healthy else 1)


if __name__ == "__main__":
    main()

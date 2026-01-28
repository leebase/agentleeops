"""Tests for LLM configuration loading and validation."""

import tempfile
from pathlib import Path

import pytest
import yaml

from lib.llm.config import (
    LLMConfig,
    compute_config_hash,
    load_config,
    resolve_role,
)


def create_test_config(content: dict) -> Path:
    """Create a temporary config file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(content, f)
        return Path(f.name)


def test_load_valid_config():
    """Test loading a valid configuration."""
    config_data = {
        "llm": {
            "default_role": "planner",
            "providers": {
                "test_provider": {
                    "type": "test",
                    "base_url": "http://localhost",
                }
            },
            "roles": {
                "planner": {
                    "provider": "test_provider",
                    "model": "test-model",
                    "temperature": 0.2,
                    "max_tokens": 1000,
                }
            },
        }
    }

    config_path = create_test_config(config_data)

    try:
        # With lazy validation, config should load successfully
        # Provider validation happens on first use in LLMClient.complete()
        config = load_config(config_path)
        assert config.default_role == "planner"
        assert "test_provider" in config.providers
        assert "planner" in config.roles
    finally:
        config_path.unlink()


def test_load_missing_file():
    """Test loading a non-existent config file."""
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path.yaml")


def test_load_missing_llm_section():
    """Test loading config without 'llm' section."""
    config_data = {"other": "data"}
    config_path = create_test_config(config_data)

    try:
        with pytest.raises(ValueError, match="missing 'llm' section"):
            load_config(config_path)
    finally:
        config_path.unlink()


def test_load_missing_providers():
    """Test loading config without 'providers' section."""
    config_data = {
        "llm": {
            "default_role": "planner",
            "roles": {},
        }
    }
    config_path = create_test_config(config_data)

    try:
        with pytest.raises(ValueError, match="missing 'providers' section"):
            load_config(config_path)
    finally:
        config_path.unlink()


def test_load_missing_roles():
    """Test loading config without 'roles' section."""
    config_data = {
        "llm": {
            "default_role": "planner",
            "providers": {},
        }
    }
    config_path = create_test_config(config_data)

    try:
        with pytest.raises(ValueError, match="missing 'roles' section"):
            load_config(config_path)
    finally:
        config_path.unlink()


def test_role_missing_provider():
    """Test role without provider field."""
    config_data = {
        "llm": {
            "default_role": "planner",
            "providers": {
                "test_provider": {"type": "test"}
            },
            "roles": {
                "planner": {
                    "model": "test-model",
                }
            },
        }
    }
    config_path = create_test_config(config_data)

    try:
        with pytest.raises(ValueError, match="missing 'provider' field"):
            load_config(config_path)
    finally:
        config_path.unlink()


def test_role_missing_model():
    """Test role without model field."""
    config_data = {
        "llm": {
            "default_role": "planner",
            "providers": {
                "test_provider": {"type": "test"}
            },
            "roles": {
                "planner": {
                    "provider": "test_provider",
                }
            },
        }
    }
    config_path = create_test_config(config_data)

    try:
        with pytest.raises(ValueError, match="missing 'model' field"):
            load_config(config_path)
    finally:
        config_path.unlink()


def test_role_unknown_provider():
    """Test role referencing non-existent provider."""
    config_data = {
        "llm": {
            "default_role": "planner",
            "providers": {
                "test_provider": {"type": "test"}
            },
            "roles": {
                "planner": {
                    "provider": "nonexistent",
                    "model": "test-model",
                }
            },
        }
    }
    config_path = create_test_config(config_data)

    try:
        with pytest.raises(ValueError, match="unknown provider 'nonexistent'"):
            load_config(config_path)
    finally:
        config_path.unlink()


def test_resolve_role():
    """Test role resolution."""
    from lib.llm.config import ProviderConfig, RoleConfig

    config = LLMConfig(
        default_role="planner",
        providers={
            "test_provider": ProviderConfig(
                provider_id="test_provider",
                type="test",
                config={"base_url": "http://localhost"},
            )
        },
        roles={
            "planner": RoleConfig(
                role="planner",
                provider="test_provider",
                model="test-model",
                temperature=0.2,
                max_tokens=1000,
            )
        },
    )

    role_cfg, provider_cfg = resolve_role("planner", config)

    assert role_cfg.role == "planner"
    assert role_cfg.provider == "test_provider"
    assert role_cfg.model == "test-model"
    assert provider_cfg.provider_id == "test_provider"


def test_resolve_unknown_role():
    """Test resolving non-existent role."""
    from lib.llm.config import ProviderConfig, RoleConfig

    config = LLMConfig(
        default_role="planner",
        providers={},
        roles={
            "planner": RoleConfig(
                role="planner",
                provider="test_provider",
                model="test-model",
            )
        },
    )

    with pytest.raises(ValueError, match="Role 'nonexistent' not found"):
        resolve_role("nonexistent", config)


def test_config_hash_stability():
    """Test that config hash is stable for same config."""
    from lib.llm.config import ProviderConfig, RoleConfig

    role_cfg = RoleConfig(
        role="planner",
        provider="test_provider",
        model="test-model",
        temperature=0.2,
        max_tokens=1000,
    )

    provider_cfg = ProviderConfig(
        provider_id="test_provider",
        type="test",
        config={"base_url": "http://localhost"},
    )

    hash1 = compute_config_hash(role_cfg, provider_cfg)
    hash2 = compute_config_hash(role_cfg, provider_cfg)

    assert hash1 == hash2


def test_config_hash_excludes_secrets():
    """Test that config hash excludes API keys and secrets."""
    from lib.llm.config import ProviderConfig, RoleConfig

    role_cfg = RoleConfig(
        role="planner",
        provider="test_provider",
        model="test-model",
    )

    provider_cfg1 = ProviderConfig(
        provider_id="test_provider",
        type="test",
        config={"base_url": "http://localhost", "api_key": "secret1"},
    )

    provider_cfg2 = ProviderConfig(
        provider_id="test_provider",
        type="test",
        config={"base_url": "http://localhost", "api_key": "secret2"},
    )

    hash1 = compute_config_hash(role_cfg, provider_cfg1)
    hash2 = compute_config_hash(role_cfg, provider_cfg2)

    # Hashes should be the same since API keys are excluded
    assert hash1 == hash2

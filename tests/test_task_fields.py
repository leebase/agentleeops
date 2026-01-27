"""Tests for task field parsing and validation."""
import pytest
from lib.task_fields import (
    parse_yaml_description,
    validate_task_fields,
    has_tag,
)


class TestParseYamlDescription:
    """Tests for YAML description parsing."""

    def test_extracts_dirname(self):
        """Should extract dirname from YAML."""
        desc = "dirname: my-project"
        fields = parse_yaml_description(desc)
        assert fields["dirname"] == "my-project"

    def test_extracts_context_mode(self):
        """Should extract and uppercase context_mode."""
        desc = "dirname: test\ncontext_mode: feature"
        fields = parse_yaml_description(desc)
        assert fields["context_mode"] == "FEATURE"

    def test_defaults_context_mode_to_new(self):
        """Should default context_mode to NEW."""
        desc = "dirname: test"
        fields = parse_yaml_description(desc)
        assert fields["context_mode"] == "NEW"

    def test_extracts_multiline_acceptance_criteria(self):
        """Should extract multiline acceptance criteria."""
        desc = """dirname: test
acceptance_criteria: |
  - First condition
  - Second condition
"""
        fields = parse_yaml_description(desc)
        assert "First condition" in fields["acceptance_criteria"]
        assert "Second condition" in fields["acceptance_criteria"]

    def test_extracts_complexity(self):
        """Should extract and uppercase complexity."""
        desc = "dirname: test\ncomplexity: m"
        fields = parse_yaml_description(desc)
        assert fields["complexity"] == "M"

    def test_empty_description_returns_empty_dict(self):
        """Should return minimal dict for empty description."""
        fields = parse_yaml_description("")
        assert fields.get("dirname") is None


class TestValidateTaskFields:
    """Tests for task field validation."""

    def test_valid_dirname_passes(self):
        """Valid dirname should pass validation."""
        is_valid, err = validate_task_fields({"dirname": "my-project"})
        assert is_valid
        assert err == ""

    def test_dirname_with_numbers_passes(self):
        """Dirname with numbers should pass."""
        is_valid, err = validate_task_fields({"dirname": "test123"})
        assert is_valid

    def test_missing_dirname_fails(self):
        """Missing dirname should fail."""
        is_valid, err = validate_task_fields({})
        assert not is_valid
        assert "dirname" in err.lower()

    def test_dirname_with_spaces_fails(self):
        """Dirname with spaces should fail."""
        is_valid, err = validate_task_fields({"dirname": "my project"})
        assert not is_valid

    def test_dirname_starting_with_dash_fails(self):
        """Dirname starting with dash should fail."""
        is_valid, err = validate_task_fields({"dirname": "-invalid"})
        assert not is_valid

    def test_dirname_with_dot_fails(self):
        """Dirname with dots should fail."""
        is_valid, err = validate_task_fields({"dirname": "has.dot"})
        assert not is_valid

    def test_dirname_with_slash_fails(self):
        """Dirname with slashes should fail."""
        is_valid, err = validate_task_fields({"dirname": "has/slash"})
        assert not is_valid

    def test_invalid_context_mode_fails(self):
        """Invalid context_mode should fail."""
        is_valid, err = validate_task_fields({
            "dirname": "test",
            "context_mode": "INVALID"
        })
        assert not is_valid
        assert "context_mode" in err.lower()

    def test_valid_context_modes_pass(self):
        """Both NEW and FEATURE should be valid."""
        is_valid, _ = validate_task_fields({"dirname": "test", "context_mode": "NEW"})
        assert is_valid
        is_valid, _ = validate_task_fields({"dirname": "test", "context_mode": "FEATURE"})
        assert is_valid

    def test_invalid_complexity_fails(self):
        """Invalid complexity should fail."""
        is_valid, err = validate_task_fields({
            "dirname": "test",
            "complexity": "HUGE"
        })
        assert not is_valid
        assert "complexity" in err.lower()

    def test_valid_complexities_pass(self):
        """S, M, L, XL should all be valid."""
        for size in ["S", "M", "L", "XL"]:
            is_valid, _ = validate_task_fields({"dirname": "test", "complexity": size})
            assert is_valid, f"Complexity {size} should be valid"


class TestHasTag:
    """Tests for tag checking."""

    def test_tag_present(self):
        """Should return True when tag is present."""
        assert has_tag(["foo", "bar"], "foo")

    def test_tag_absent(self):
        """Should return False when tag is absent."""
        assert not has_tag(["foo", "bar"], "baz")

    def test_empty_list(self):
        """Should return False for empty list."""
        assert not has_tag([], "foo")

"""Tests for workspace management."""
import pytest
import tempfile
from pathlib import Path
from lib.workspace import (
    get_workspace_path,
    safe_write_file,
    validate_dirname,
)
from lib.ratchet import lock_artifact


class TestGetWorkspacePath:
    """Tests for workspace path resolution."""

    def test_returns_projects_dir(self):
        """Should return path under ~/projects/."""
        path = get_workspace_path("test-project")
        assert "projects" in str(path)
        assert "test-project" in str(path)

    def test_uses_home_directory(self):
        """Should use user's home directory."""
        path = get_workspace_path("myproj")
        assert str(Path.home()) in str(path)


class TestSafeWriteFile:
    """Tests for ratchet-aware file writing."""

    @pytest.fixture
    def workspace(self):
        """Create a temporary workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_writes_new_file(self, workspace):
        """Should create new files successfully."""
        safe_write_file(workspace, "test.py", "# content")
        assert (workspace / "test.py").exists()
        assert (workspace / "test.py").read_text() == "# content"

    def test_creates_parent_directories(self, workspace):
        """Should create parent directories if needed."""
        safe_write_file(workspace, "src/module/test.py", "# nested")
        assert (workspace / "src" / "module" / "test.py").exists()

    def test_overwrites_unlocked_file(self, workspace):
        """Should overwrite files that aren't locked."""
        safe_write_file(workspace, "test.py", "# original")
        safe_write_file(workspace, "test.py", "# modified")
        assert (workspace / "test.py").read_text() == "# modified"

    def test_blocks_locked_file(self, workspace):
        """Should raise PermissionError for locked files."""
        safe_write_file(workspace, "test.py", "# original")
        lock_artifact(workspace, "test.py")

        with pytest.raises(PermissionError) as exc_info:
            safe_write_file(workspace, "test.py", "# modified")

        assert "RATCHET" in str(exc_info.value)
        # File should be unchanged
        assert (workspace / "test.py").read_text() == "# original"

    def test_force_bypasses_lock(self, workspace):
        """Force flag should bypass ratchet check."""
        safe_write_file(workspace, "test.py", "# original")
        lock_artifact(workspace, "test.py")

        # Force should allow write
        safe_write_file(workspace, "test.py", "# forced", force=True)
        assert (workspace / "test.py").read_text() == "# forced"


class TestValidateDirname:
    """Tests for dirname validation."""

    def test_valid_lowercase(self):
        """Lowercase letters should be valid."""
        assert validate_dirname("myproject")

    def test_valid_with_numbers(self):
        """Numbers should be valid."""
        assert validate_dirname("project123")

    def test_valid_with_dashes(self):
        """Dashes should be valid."""
        assert validate_dirname("my-project")

    def test_invalid_uppercase(self):
        """Uppercase letters should be invalid."""
        assert not validate_dirname("MyProject")

    def test_invalid_spaces(self):
        """Spaces should be invalid."""
        assert not validate_dirname("my project")

    def test_invalid_dots(self):
        """Dots should be invalid."""
        assert not validate_dirname("my.project")

    def test_invalid_leading_dot(self):
        """Leading dots should be invalid."""
        assert not validate_dirname(".hidden")

    def test_invalid_slashes(self):
        """Slashes should be invalid."""
        assert not validate_dirname("my/project")

    def test_invalid_empty(self):
        """Empty string should be invalid."""
        assert not validate_dirname("")

    def test_invalid_underscores(self):
        """Underscores should be invalid (per regex)."""
        assert not validate_dirname("my_project")

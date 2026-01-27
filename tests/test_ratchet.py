"""Tests for Ratchet governance system."""
import pytest
import tempfile
from pathlib import Path
from lib.ratchet import lock_artifact, verify_integrity, check_write_permission, calculate_hash


@pytest.fixture
def workspace():
    """Create a temporary workspace with a test file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Path(tmpdir)
        (ws / "test.py").write_text("# original content")
        yield ws


def test_lock_artifact_creates_hash(workspace):
    """Locking an artifact should create the ratchet manifest."""
    assert lock_artifact(workspace, "test.py")
    ratchet_file = workspace / ".agentleeops" / "ratchet.json"
    assert ratchet_file.exists()


def test_verify_integrity_passes_for_unchanged(workspace):
    """Integrity check should pass for unchanged files."""
    lock_artifact(workspace, "test.py")
    assert verify_integrity(workspace, "test.py")


def test_verify_integrity_fails_after_modification(workspace):
    """Integrity check should fail after file is modified."""
    lock_artifact(workspace, "test.py")
    (workspace / "test.py").write_text("# modified content")
    assert not verify_integrity(workspace, "test.py")


def test_check_write_permission_false_when_locked(workspace):
    """Write permission should be denied for locked files."""
    lock_artifact(workspace, "test.py")
    assert not check_write_permission(workspace, "test.py")


def test_untracked_file_is_writable(workspace):
    """Untracked files should be writable."""
    assert check_write_permission(workspace, "new_file.py")


def test_calculate_hash_returns_empty_for_missing_file(workspace):
    """Hash calculation should return empty string for missing files."""
    assert calculate_hash(workspace / "nonexistent.py") == ""


def test_lock_artifact_fails_for_missing_file(workspace):
    """Locking should fail for non-existent files."""
    assert not lock_artifact(workspace, "nonexistent.py")

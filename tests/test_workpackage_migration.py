"""Tests for legacy workspace migration into work packages."""

from hashlib import sha256
from pathlib import Path

from lib.workpackage import migrate_from_workspace


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _seed_workspace(workspace: Path) -> None:
    (workspace / "tests").mkdir(parents=True, exist_ok=True)
    (workspace / "src").mkdir(parents=True, exist_ok=True)
    (workspace / "DESIGN.md").write_text("# Design\n", encoding="utf-8")
    (workspace / "prd.json").write_text("{\"stories\": []}\n", encoding="utf-8")
    (workspace / "tests" / "TEST_PLAN_atomic-01.md").write_text("plan\n", encoding="utf-8")
    (workspace / "tests" / "test_atomic_01.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    (workspace / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")


def test_migrate_from_workspace_copies_expected_artifacts(tmp_path: Path):
    """Migration should copy known artifacts and write a migration report."""
    workspace = tmp_path / "legacy"
    base_dir = tmp_path / "work-packages"
    _seed_workspace(workspace)

    report = migrate_from_workspace(
        base_dir=base_dir,
        work_package_id="task-801",
        title="Migration Test",
        dirname="migration-test",
        context_mode="FEATURE",
        acceptance_criteria=["migrate"],
        workspace_dir=workspace,
    )
    work_package_dir = Path(report["work_package_dir"])

    assert (work_package_dir / "artifacts" / "design" / "DESIGN.md").exists()
    assert (work_package_dir / "artifacts" / "planning" / "prd.json").exists()
    assert (work_package_dir / "artifacts" / "tests" / "TEST_PLAN_atomic-01.md").exists()
    assert (work_package_dir / "artifacts" / "tests" / "test_atomic_01.py").exists()
    assert (work_package_dir / "artifacts" / "implementation" / "src" / "main.py").exists()
    assert (work_package_dir / "migration" / "migration-report.json").exists()


def test_migration_is_idempotent_and_preserves_source_tests(tmp_path: Path):
    """Repeated migration should keep source test files unchanged."""
    workspace = tmp_path / "legacy"
    base_dir = tmp_path / "work-packages"
    _seed_workspace(workspace)
    source_test = workspace / "tests" / "test_atomic_01.py"
    source_hash_before = _sha(source_test)

    first = migrate_from_workspace(
        base_dir=base_dir,
        work_package_id="task-802",
        title="Migration Test",
        dirname="migration-test-two",
        context_mode="FEATURE",
        acceptance_criteria=["migrate"],
        workspace_dir=workspace,
    )
    second = migrate_from_workspace(
        base_dir=base_dir,
        work_package_id="task-802",
        title="Migration Test",
        dirname="migration-test-two",
        context_mode="FEATURE",
        acceptance_criteria=["migrate"],
        workspace_dir=workspace,
    )

    assert first["copied_files"] == second["copied_files"]
    assert _sha(source_test) == source_hash_before

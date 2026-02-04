"""Deterministic code review suite with prioritized next steps."""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from pathlib import Path


SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


@dataclass
class Finding:
    """Single review finding."""

    id: str
    severity: str
    title: str
    details: str
    suggested_fix: str
    category: str
    file_path: str | None = None


@dataclass
class ReviewResult:
    """Result from one review module."""

    review_id: str
    summary: str
    status: str
    findings: list[Finding]


@dataclass
class ReviewSuiteResult:
    """Combined review output."""

    generated_at: str
    workspace: str
    overall_status: str
    reviews: list[ReviewResult]
    findings: list[Finding]


def _calculate_hash(path: Path) -> str:
    sha256 = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()


def _sort_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda item: (SEVERITY_ORDER.get(item.severity, 99), item.id))


def _pytest_review(workspace: Path) -> ReviewResult:
    tests_dir = workspace / "tests"
    if not tests_dir.exists():
        return ReviewResult(
            review_id="test_pass_review",
            summary="No tests directory found.",
            status="warn",
            findings=[
                Finding(
                    id="tests-missing",
                    severity="P1",
                    title="No tests directory present",
                    details="Code review could not validate behavior because tests/ is missing.",
                    suggested_fix="Add and run a targeted test suite before final approval.",
                    category="correctness",
                    file_path="tests/",
                )
            ],
        )

    python_cmd = workspace / ".venv" / "bin" / "python"
    if python_cmd.exists():
        cmd = [str(python_cmd), "-m", "pytest", "tests/", "-q"]
    else:
        cmd = ["python3", "-m", "pytest", "tests/", "-q"]

    result = subprocess.run(cmd, cwd=workspace, capture_output=True, text=True)
    if result.returncode == 0:
        return ReviewResult(
            review_id="test_pass_review",
            summary="All tests passed in review run.",
            status="pass",
            findings=[],
        )

    return ReviewResult(
        review_id="test_pass_review",
        summary="Test suite failed during review run.",
        status="fail",
        findings=[
            Finding(
                id="tests-failing",
                severity="P0",
                title="Tests are failing",
                details=(result.stdout + "\n" + result.stderr).strip()[-2000:],
                suggested_fix="Fix failing tests before moving forward.",
                category="correctness",
                file_path="tests/",
            )
        ],
    )


def _ratchet_integrity_review(workspace: Path) -> ReviewResult:
    ratchet_path = workspace / ".agentleeops" / "ratchet.json"
    if not ratchet_path.exists():
        return ReviewResult(
            review_id="ratchet_integrity_review",
            summary="Ratchet manifest not found.",
            status="warn",
            findings=[
                Finding(
                    id="ratchet-missing",
                    severity="P1",
                    title="Ratchet manifest missing",
                    details="No .agentleeops/ratchet.json found for artifact lock verification.",
                    suggested_fix="Run governance lock step before final approval.",
                    category="governance",
                    file_path=".agentleeops/ratchet.json",
                )
            ],
        )

    try:
        data = json.loads(ratchet_path.read_text())
    except json.JSONDecodeError as exc:
        return ReviewResult(
            review_id="ratchet_integrity_review",
            summary="Ratchet manifest is invalid JSON.",
            status="fail",
            findings=[
                Finding(
                    id="ratchet-invalid-json",
                    severity="P0",
                    title="Ratchet manifest is invalid",
                    details=str(exc),
                    suggested_fix="Repair .agentleeops/ratchet.json and re-run governance.",
                    category="governance",
                    file_path=".agentleeops/ratchet.json",
                )
            ],
        )

    findings: list[Finding] = []
    artifacts = data.get("artifacts", {})
    for rel_path, artifact in artifacts.items():
        if artifact.get("status") != "LOCKED":
            continue
        full_path = workspace / rel_path
        if not full_path.exists():
            findings.append(
                Finding(
                    id=f"locked-missing-{rel_path}",
                    severity="P0",
                    title="Locked artifact missing",
                    details=f"Locked artifact {rel_path} does not exist.",
                    suggested_fix="Restore missing locked artifact and rerun governance lock.",
                    category="governance",
                    file_path=rel_path,
                )
            )
            continue

        expected_hash = artifact.get("hash", "")
        current_hash = _calculate_hash(full_path)
        if expected_hash and expected_hash != current_hash:
            findings.append(
                Finding(
                    id=f"locked-hash-mismatch-{rel_path}",
                    severity="P0",
                    title="Locked artifact hash mismatch",
                    details=f"{rel_path} hash does not match ratchet manifest.",
                    suggested_fix="Move task back to draft lane for explicit re-approval, then relock.",
                    category="governance",
                    file_path=rel_path,
                )
            )

    if findings:
        return ReviewResult(
            review_id="ratchet_integrity_review",
            summary="One or more locked artifacts failed integrity checks.",
            status="fail",
            findings=findings,
        )

    return ReviewResult(
        review_id="ratchet_integrity_review",
        summary="Locked artifacts passed integrity checks.",
        status="pass",
        findings=[],
    )


def _git_hygiene_review(workspace: Path) -> ReviewResult:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ReviewResult(
            review_id="git_hygiene_review",
            summary="Could not read git status.",
            status="warn",
            findings=[
                Finding(
                    id="git-status-unavailable",
                    severity="P2",
                    title="Git status unavailable",
                    details=result.stderr.strip() or "Unknown git error",
                    suggested_fix="Ensure workspace is a valid git repository.",
                    category="operational",
                )
            ],
        )

    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        return ReviewResult(
            review_id="git_hygiene_review",
            summary="Working tree is clean.",
            status="pass",
            findings=[],
        )

    findings = []
    if any("tests/" in line for line in lines):
        findings.append(
            Finding(
                id="git-tests-dirty",
                severity="P1",
                title="Working tree has test changes",
                details="Uncommitted/staged test changes detected during review.",
                suggested_fix="Validate whether test changes are intentional and approved.",
                category="test_integrity",
                file_path="tests/",
            )
        )

    findings.append(
        Finding(
            id="git-tree-dirty",
            severity="P2",
            title="Working tree is not clean",
            details="\n".join(lines[:40]),
            suggested_fix="Commit or discard unrelated workspace changes before final approval.",
            category="operational",
        )
    )
    return ReviewResult(
        review_id="git_hygiene_review",
        summary="Working tree has uncommitted changes.",
        status="warn",
        findings=findings,
    )


def _artifact_presence_review(workspace: Path) -> ReviewResult:
    checks = [
        ("design", workspace / "DESIGN.md"),
        ("plan", workspace / "prd.json"),
        ("source", workspace / "src"),
    ]
    findings: list[Finding] = []
    for label, path in checks:
        if path.exists():
            continue
        findings.append(
            Finding(
                id=f"artifact-missing-{label}",
                severity="P1",
                title=f"Expected artifact missing: {label}",
                details=f"Required artifact not found at {path}",
                suggested_fix=f"Generate or restore the missing {label} artifact before approval.",
                category="maintainability",
                file_path=str(path.relative_to(workspace)),
            )
        )

    if findings:
        return ReviewResult(
            review_id="artifact_presence_review",
            summary="One or more expected artifacts are missing.",
            status="warn",
            findings=findings,
        )

    return ReviewResult(
        review_id="artifact_presence_review",
        summary="Expected project artifacts are present.",
        status="pass",
        findings=[],
    )


def run_review_suite(workspace: Path) -> ReviewSuiteResult:
    """Run the full code review set and return structured results."""
    reviews = [
        _pytest_review(workspace),
        _ratchet_integrity_review(workspace),
        _git_hygiene_review(workspace),
        _artifact_presence_review(workspace),
    ]

    findings: list[Finding] = []
    for review in reviews:
        findings.extend(review.findings)
    findings = _sort_findings(findings)

    if any(review.status == "fail" for review in reviews):
        overall_status = "fail"
    elif any(review.status == "warn" for review in reviews):
        overall_status = "warn"
    else:
        overall_status = "pass"

    return ReviewSuiteResult(
        generated_at=datetime.now(UTC).isoformat(),
        workspace=str(workspace),
        overall_status=overall_status,
        reviews=reviews,
        findings=findings,
    )


def to_json_dict(result: ReviewSuiteResult) -> dict:
    """Convert review suite result to JSON-serializable dict."""
    return {
        "generated_at": result.generated_at,
        "workspace": result.workspace,
        "overall_status": result.overall_status,
        "reviews": [
            {
                "review_id": review.review_id,
                "summary": review.summary,
                "status": review.status,
                "findings": [asdict(finding) for finding in review.findings],
            }
            for review in result.reviews
        ],
        "findings": [asdict(finding) for finding in result.findings],
    }


def to_prioritized_markdown(result: ReviewSuiteResult) -> str:
    """Render prioritized next steps from findings."""
    sections = {
        "Must Fix Before Final Review": [f for f in result.findings if f.severity == "P0"],
        "Should Fix Soon": [f for f in result.findings if f.severity == "P1"],
        "Can Defer": [f for f in result.findings if f.severity in ("P2", "P3")],
    }

    lines = [
        "# Code Review Next Steps",
        "",
        f"- Generated: {result.generated_at}",
        f"- Workspace: `{result.workspace}`",
        f"- Overall Status: **{result.overall_status.upper()}**",
        "",
    ]
    for title, findings in sections.items():
        lines.append(f"## {title}")
        if not findings:
            lines.append("- None")
            lines.append("")
            continue
        for index, finding in enumerate(findings, start=1):
            location = f" (`{finding.file_path}`)" if finding.file_path else ""
            lines.append(f"{index}. [{finding.severity}] {finding.title}{location}")
            lines.append(f"   - Category: {finding.category}")
            lines.append(f"   - Details: {finding.details}")
            lines.append(f"   - Suggested fix: {finding.suggested_fix}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"

"""CODE_REVIEW_AGENT for post-generation quality checks."""

import base64
import json
from pathlib import Path

from lib.code_review.suite import run_review_suite, to_json_dict, to_prioritized_markdown
from lib.workspace import get_workspace_path, safe_write_file


def run_code_review_agent(task_id: str, title: str, dirname: str, kb_client, project_id: int) -> dict:
    """
    Run deterministic code review modules and publish review artifacts.

    Artifacts:
    - reviews/CODE_REVIEW_REPORT.json
    - reviews/CODE_REVIEW_NEXT_STEPS.md
    """
    workspace = get_workspace_path(dirname)
    report_rel = "reviews/CODE_REVIEW_REPORT.json"
    next_steps_rel = "reviews/CODE_REVIEW_NEXT_STEPS.md"
    report_path = workspace / report_rel
    next_steps_path = workspace / next_steps_rel

    try:
        result = run_review_suite(workspace)
        report_json = json.dumps(to_json_dict(result), indent=2)
        next_steps_md = to_prioritized_markdown(result)
    except Exception as exc:
        return {"success": False, "error": f"Code review generation failed: {exc}"}

    try:
        safe_write_file(workspace, report_rel, report_json)
        safe_write_file(workspace, next_steps_rel, next_steps_md)
    except Exception as exc:
        return {"success": False, "error": f"Failed to write review artifacts: {exc}"}

    if kb_client:
        try:
            for filename, content in [
                (Path(report_rel).name, report_json),
                (Path(next_steps_rel).name, next_steps_md),
            ]:
                encoded = base64.b64encode(content.encode()).decode()
                kb_client.execute(
                    "createTaskFile",
                    project_id=project_id,
                    task_id=int(task_id),
                    filename=filename,
                    blob=encoded,
                )
        except Exception:
            pass

        try:
            kb_client.create_comment(
                task_id=int(task_id),
                content=(
                    f"**CODE_REVIEW_AGENT Completed**\n\n"
                    f"- Overall status: **{result.overall_status.upper()}**\n"
                    f"- Report: `{report_rel}`\n"
                    f"- Prioritized next steps: `{next_steps_rel}`"
                ),
            )
        except Exception:
            pass

    return {
        "success": True,
        "overall_status": result.overall_status,
        "report_path": str(report_path),
        "next_steps_path": str(next_steps_path),
        "finding_count": len(result.findings),
    }

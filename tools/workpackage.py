#!/usr/bin/env python3
"""CLI utilities for single-card work package bootstrap and validation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Support running as a standalone script from repo root.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lib.workpackage import (
    ManifestValidationError,
    refresh_dashboard,
    initialize_work_package,
    initialize_work_package_from_task,
    refresh_artifact_registry,
    replay_summary,
    transition_stage,
    load_manifest,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Work package CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize a work package")
    init_parser.add_argument("--base-dir", default="work-packages")
    init_parser.add_argument("--id", required=True, dest="work_package_id")
    init_parser.add_argument("--title", required=True)
    init_parser.add_argument("--dirname", required=True)
    init_parser.add_argument("--context-mode", required=True, choices=["NEW", "FEATURE"])
    init_parser.add_argument(
        "--acceptance",
        action="append",
        dest="acceptance_criteria",
        default=[],
        help="Acceptance criterion line (repeatable)",
    )

    init_task_parser = subparsers.add_parser(
        "init-from-task",
        help="Initialize from task fields",
    )
    init_task_parser.add_argument("--base-dir", default="work-packages")
    init_task_parser.add_argument("--task-id", required=True, type=int)
    init_task_parser.add_argument("--title", required=True)
    init_task_parser.add_argument("--dirname", required=True)
    init_task_parser.add_argument("--context-mode", required=True, choices=["NEW", "FEATURE"])
    init_task_parser.add_argument("--project-id", type=int, default=None)
    init_task_parser.add_argument("--provider", default="kanboard")
    init_task_parser.add_argument(
        "--acceptance",
        action="append",
        dest="acceptance_criteria",
        default=[],
        help="Acceptance criterion line (repeatable)",
    )

    validate_parser = subparsers.add_parser("validate", help="Validate a manifest")
    validate_parser.add_argument("--work-package-dir", required=True)

    transition_parser = subparsers.add_parser("transition", help="Transition to another stage")
    transition_parser.add_argument("--work-package-dir", required=True)
    transition_parser.add_argument("--to-stage", required=True)
    transition_parser.add_argument("--actor", default="system")
    transition_parser.add_argument("--reason", default="")

    history_parser = subparsers.add_parser("history", help="Print transition replay summary")
    history_parser.add_argument("--work-package-dir", required=True)

    refresh_parser = subparsers.add_parser(
        "refresh-artifacts",
        help="Recompute artifact hashes and freshness state",
    )
    refresh_parser.add_argument("--work-package-dir", required=True)

    dashboard_parser = subparsers.add_parser(
        "refresh-dashboard",
        help="Regenerate dashboard JSON and HTML output",
    )
    dashboard_parser.add_argument("--work-package-dir", required=True)

    return parser


def main() -> int:
    args = _parser().parse_args()

    try:
        if args.command == "init":
            target = initialize_work_package(
                base_dir=Path(args.base_dir),
                work_package_id=args.work_package_id,
                title=args.title,
                dirname=args.dirname,
                context_mode=args.context_mode,
                acceptance_criteria=args.acceptance_criteria,
            )
            print(f"initialized:{target}")
            return 0

        if args.command == "init-from-task":
            target = initialize_work_package_from_task(
                base_dir=Path(args.base_dir),
                task_id=args.task_id,
                title=args.title,
                dirname=args.dirname,
                context_mode=args.context_mode,
                acceptance_criteria=args.acceptance_criteria,
                project_id=args.project_id,
                provider=args.provider,
            )
            print(f"initialized:{target}")
            return 0

        if args.command == "validate":
            manifest = load_manifest(Path(args.work_package_dir))
            print(
                f"valid:{manifest['work_package']['id']}:{manifest['work_package']['current_stage']}"
            )
            return 0

        if args.command == "transition":
            result = transition_stage(
                work_package_dir=Path(args.work_package_dir),
                to_stage=args.to_stage,
                actor=args.actor,
                reason=args.reason,
            )
            print(
                "transition:"
                f"{result.transition_type}:"
                f"{result.from_stage}->{result.to_stage}:"
                f"{result.event_file}"
            )
            return 0

        if args.command == "history":
            for line in replay_summary(Path(args.work_package_dir)):
                print(line)
            return 0

        if args.command == "refresh-artifacts":
            state = refresh_artifact_registry(Path(args.work_package_dir))
            counts = state.get("counts", {})
            print(
                "artifacts:"
                f"draft={counts.get('draft', 0)}:"
                f"approved={counts.get('approved', 0)}:"
                f"stale={counts.get('stale', 0)}:"
                f"superseded={counts.get('superseded', 0)}"
            )
            return 0

        if args.command == "refresh-dashboard":
            data_path, html_path = refresh_dashboard(Path(args.work_package_dir))
            print(f"dashboard:{data_path}:{html_path}")
            return 0
    except ManifestValidationError as err:
        print(f"invalid:{err}", file=sys.stderr)
        return 2
    except Exception as err:
        print(f"error:{err}", file=sys.stderr)
        return 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

"""CLI surface for the Project Agent Factory.

Thin wrapper around `mcp_server`'s tool dispatch table: every subcommand
builds a `project_root` + tool-specific args dict and calls the same
`tool_*` function the MCP server calls for `tools/call`, so the CLI and
the MCP surface stay in lockstep by construction instead of duplicating
logic.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from . import runtime_identity, runtime_version
from .mcp_server import DISPATCH, TOOLS, serve
from .persistence import store_dir


def _root(value: str) -> Path:
    return Path(value).resolve()


def _emit(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def doctor(root: Path) -> dict[str, Any]:
    revision, dirty = runtime_identity()
    version = runtime_version()
    return {
        "version": version,
        "package_version": version.split("+", maxsplit=1)[0],
        "revision": revision,
        "dirty": dirty,
        "python": sys.version.split()[0],
        "root": str(root),
        "codex": shutil.which("codex") is not None,
        "claude": shutil.which("claude") is not None,
        "rtk": shutil.which("rtk") is not None,
        "codebase_memory_mcp": shutil.which("codebase-memory-mcp") is not None,
        "state": store_dir(root).exists(),
    }


def _call(tool_name: str, root: Path, **extra: Any) -> Any:
    args: dict[str, Any] = {"project_root": str(root)}
    args.update({key: value for key, value in extra.items() if value is not None})
    return DISPATCH[tool_name](args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qagents")
    parser.add_argument("--version", action="version", version=runtime_version())
    sub = parser.add_subparsers(dest="command", required=True)

    # `--project` is registered on every *leaf* subparser (via `parents=`)
    # rather than on group parsers like `agents`/`decisions`, so it can be
    # passed after the subcommand: `qagents agents list --project .` —
    # not just before it.
    project_parent = argparse.ArgumentParser(add_help=False)
    project_parent.add_argument("--project", default=".")

    def leaf(name: str) -> argparse.ArgumentParser:
        return sub.add_parser(name, parents=[project_parent])

    leaf("analyze")
    leaf("validate")
    leaf("diff")
    leaf("doctor")

    setup_p = leaf("setup")
    setup_p.add_argument("--providers", default="claude,codex")

    agents = sub.add_parser("agents")
    agents_sub = agents.add_subparsers(dest="agents_command", required=True)
    agents_sub.add_parser("list", parents=[project_parent])
    agents_sub.add_parser("generate", parents=[project_parent])

    skills = sub.add_parser("skills")
    skills.add_subparsers(dest="skills_command", required=True).add_parser(
        "generate", parents=[project_parent]
    )

    decisions = sub.add_parser("decisions")
    decisions_sub = decisions.add_subparsers(dest="decisions_command", required=True)
    dec_list = decisions_sub.add_parser("list", parents=[project_parent])
    dec_list.add_argument("--status")
    dec_list.add_argument("--scope")
    dec_record = decisions_sub.add_parser("record", parents=[project_parent])
    dec_record.add_argument("--id", required=True)
    dec_record.add_argument("--title", required=True)
    dec_record.add_argument("--value", default="{}")
    dec_record.add_argument("--reason", default="")
    dec_record.add_argument("--scope-paths", default="[]")
    dec_record.add_argument("--decision-scope", default="project_wide")
    dec_record.add_argument("--effects", default="{}")
    dec_reopen = decisions_sub.add_parser("reopen", parents=[project_parent])
    dec_reopen.add_argument("decision_id")
    dec_reopen.add_argument("--reason", required=True)

    task = sub.add_parser("task")
    task_sub = task.add_subparsers(dest="task_command", required=True)
    task_prepare = task_sub.add_parser("prepare", parents=[project_parent])
    task_prepare.add_argument("--task-id", required=True)
    task_prepare.add_argument("--goal", required=True)
    task_prepare.add_argument("--session-id", required=True)
    task_prepare.add_argument("--base-agent-ids", default="[]")

    swarm = sub.add_parser("swarm")
    swarm_sub = swarm.add_subparsers(dest="swarm_command", required=True)
    swarm_plan = swarm_sub.add_parser("plan", parents=[project_parent])
    swarm_plan.add_argument("--task-id", required=True)
    swarm_plan.add_argument("--goal", required=True)
    swarm_plan.add_argument("--agent-ids")
    swarm_plan.add_argument("--phases", default="{}")
    swarm_plan.add_argument("--depends-on", default="{}")
    swarm_plan.add_argument("--file-ownership", default="{}")

    interview = sub.add_parser("interview")
    interview_sub = interview.add_subparsers(dest="interview_command", required=True)
    iv_start = interview_sub.add_parser("start", parents=[project_parent])
    iv_start.add_argument("--session-id", required=True)
    iv_start.add_argument("--session-type", default="initial_setup")
    iv_start.add_argument("--goal")
    iv_start.add_argument("--base-agent-ids", default="[]")
    for name in ("state", "next", "answer", "summary", "confirm", "gaps", "conflicts"):
        p = interview_sub.add_parser(name, parents=[project_parent])
        p.add_argument("session_id")
        if name == "answer":
            p.add_argument("--answers", required=True)
    iv_resolve = interview_sub.add_parser("resolve", parents=[project_parent])
    iv_resolve.add_argument("--conflict-id", required=True)
    iv_resolve.add_argument("--resolution", required=True)

    mcp = sub.add_parser("mcp")
    mcp_sub = mcp.add_subparsers(dest="mcp_command", required=True)
    mcp_sub.add_parser("serve")
    mcp_sub.add_parser("list")

    return parser


_INTERVIEW_TOOL_BY_COMMAND = {
    "start": "start_project_interview",
    "state": "get_interview_state",
    "next": "get_next_questions",
    "answer": "submit_interview_answers",
    "summary": "review_interview_summary",
    "confirm": "confirm_interview_decisions",
    "gaps": "list_open_knowledge_gaps",
    "conflicts": "list_decision_conflicts",
    "resolve": "resolve_decision_conflict",
}


def _dispatch_decisions(args: argparse.Namespace, root: Path) -> Any:
    if args.decisions_command == "list":
        return _call("list_decisions", root, status=args.status, decision_scope=args.scope)
    if args.decisions_command == "record":
        return _call(
            "record_decision",
            root,
            id=args.id,
            title=args.title,
            value=args.value,
            reason=args.reason,
            scope_paths=args.scope_paths,
            decision_scope=args.decision_scope,
            effects=args.effects,
        )
    return _call("reopen_decision", root, decision_id=args.decision_id, reason=args.reason)


def _dispatch_interview(args: argparse.Namespace, root: Path) -> Any:
    tool_name = _INTERVIEW_TOOL_BY_COMMAND[args.interview_command]
    if args.interview_command == "start":
        return _call(
            tool_name,
            root,
            session_id=args.session_id,
            session_type=args.session_type,
            goal=args.goal,
            base_agent_ids=args.base_agent_ids,
        )
    if args.interview_command == "answer":
        return _call(tool_name, root, session_id=args.session_id, answers=args.answers)
    if args.interview_command == "resolve":
        return _call(tool_name, root, conflict_id=args.conflict_id, resolution=args.resolution)
    return _call(tool_name, root, session_id=args.session_id)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    root = _root(getattr(args, "project", "."))
    try:
        out: Any
        if args.command == "analyze":
            out = _call("analyze_project", root)
        elif args.command == "validate":
            out = _call("validate_generated_configuration", root)
        elif args.command == "diff":
            out = _call("show_generation_diff", root)
        elif args.command == "doctor":
            out = doctor(root)
        elif args.command == "setup":
            out = _call("setup", root, providers=args.providers.split(","))
        elif args.command == "agents":
            tool = "list_agents" if args.agents_command == "list" else "generate_agents"
            out = _call(tool, root)
        elif args.command == "skills":
            out = _call("generate_skills", root)
        elif args.command == "decisions":
            out = _dispatch_decisions(args, root)
        elif args.command == "task":
            out = _call(
                "prepare_task",
                root,
                task_id=args.task_id,
                goal=args.goal,
                session_id=args.session_id,
                base_agent_ids=args.base_agent_ids,
            )
        elif args.command == "swarm":
            out = _call(
                "generate_swarm_plan",
                root,
                task_id=args.task_id,
                goal=args.goal,
                agent_ids=args.agent_ids,
                phases=args.phases,
                depends_on=args.depends_on,
                file_ownership=args.file_ownership,
            )
        elif args.command == "interview":
            out = _dispatch_interview(args, root)
        elif args.command == "mcp" and args.mcp_command == "serve":
            return serve()
        elif args.command == "mcp":
            out = {"tools": TOOLS}
        else:
            out = {"command": args.command, "status": "unknown"}
        _emit(out)
        return 0 if not isinstance(out, dict) or out.get("valid", True) else 1
    except Exception as exc:  # noqa: BLE001
        _emit({"error": str(exc)})
        return 2

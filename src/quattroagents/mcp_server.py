"""MCP server for the Project Agent Factory.

One JSON-RPC request per line on stdin, one response per line on stdout.
Every tool takes an explicit `project_root` argument and never blocks on
interactive stdin — the interview flow is a sequence of discrete
`tools/call`s (start -> get_next_questions -> submit_interview_answers ->
... -> confirm_interview_decisions), not a blocking prompt loop.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, cast

from . import runtime_version
from .adapters.claude import render_claude
from .adapters.codex import render_codex
from .analysis import detect_changes, scan_repository
from .domain import (
    AgentDefinition,
    Decision,
    DecisionScope,
    DecisionSource,
    DecisionSourceType,
    DecisionStatus,
    InterviewSession,
    ProjectProfile,
    SessionStatus,
    SessionType,
)
from .formatting import agent_display_description, agent_file_stem, render_agent_display
from .generation.agents import select_agents
from .generation.skills import select_skills
from .generation.swarm import build_swarm_plan, render_swarm_plan_text
from .generation.task_synthesis import synthesize_task_agent
from .interview.conflicts import resolve_conflict
from .interview.engine import InterviewEngine, RawAnswer
from .persistence import AgentFactoryStore, GeneratedFileGuard, read_json, write_json
from .validation import validate_generated_configuration

TOOLS = [
    "analyze_project",
    "setup",
    "get_project_profile",
    "list_decisions",
    "record_decision",
    "reopen_decision",
    "list_agents",
    "generate_agents",
    "generate_skills",
    "prepare_task",
    "generate_swarm_plan",
    "validate_generated_configuration",
    "show_generation_diff",
    "start_project_interview",
    "get_interview_state",
    "get_next_questions",
    "submit_interview_answers",
    "review_interview_summary",
    "confirm_interview_decisions",
    "list_open_knowledge_gaps",
    "list_decision_conflicts",
    "resolve_decision_conflict",
]
INPUT_SCHEMA = {"type": "object", "additionalProperties": True}


def _coerce_json(value: Any) -> Any:
    """Parse JSON-encoded object/array arguments some MCP clients stringify."""
    if isinstance(value, str):
        return json.loads(value)
    return value


def _root(args: dict[str, Any]) -> Path:
    return Path(args["project_root"]).resolve()


def _store(args: dict[str, Any]) -> AgentFactoryStore:
    return AgentFactoryStore(_root(args))


def _require_session(store: AgentFactoryStore, session_id: str) -> InterviewSession:
    session = store.load_session(session_id)
    if session is None:
        raise KeyError(f"unknown interview session: {session_id}")
    return session


def _require_profile(store: AgentFactoryStore, root: Path) -> ProjectProfile:
    profile = store.load_profile()
    if profile is None:
        profile = scan_repository(root)
        store.save_profile(profile)
    return profile


def _generated_agents(store: AgentFactoryStore) -> list[AgentDefinition]:
    manifest = store.load_generated_manifest()
    if manifest is None:
        return []
    return [AgentDefinition.from_dict(d) for d in manifest.get("agents", [])]


def _agent_output_dict(agent: AgentDefinition) -> dict[str, Any]:
    """Agent JSON for MCP tool responses: raw fields plus what render would produce.

    `to_dict()` stays raw (it also backs manifest persistence, which must
    round-trip through `agent_display_description`/`agent_file_stem` again
    at render time rather than store their output). These two extra keys
    are purely informational, for a human or orchestrator reading tool
    output to see the same `qag-`/`(model)` tags the rendered files carry.
    """
    return {
        **agent.to_dict(),
        "rendered_name": agent_file_stem(agent.id),
        "rendered_description": agent_display_description(agent),
    }


class DryRunFileGuard:
    """Reports what a real GeneratedFileGuard.write() would do, without touching disk."""

    def __init__(self, store: AgentFactoryStore):
        self._real = store.file_guard()

    def write(self, relative_path: str, content: str) -> Any:
        target = self._real.root / relative_path
        record = read_json(self._real._record_path(relative_path), None)  # noqa: SLF001
        import hashlib

        new_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if not target.exists():
            status = "would_create"
        else:
            on_disk_hash = hashlib.sha256(
                target.read_text(encoding="utf-8").encode("utf-8")
            ).hexdigest()
            if on_disk_hash == new_hash:
                status = "unchanged"
            elif record is not None and on_disk_hash != record["last_generated_hash"]:
                status = "conflict_manual_edit"
            else:
                status = "would_update"
        return {"relative_path": relative_path, "status": status}


# --------------------------------------------------------------------------
# Tool implementations
# --------------------------------------------------------------------------


def tool_analyze_project(args: dict[str, Any]) -> Any:
    root = _root(args)
    store = _store(args)
    previous = store.load_profile()
    profile = scan_repository(root)
    store.save_profile(profile)
    return {"profile": profile.to_dict(), "changes": detect_changes(previous, profile)}


def tool_get_project_profile(args: dict[str, Any]) -> Any:
    store = _store(args)
    profile = store.load_profile()
    return {"profile": profile.to_dict() if profile else None}


def tool_list_decisions(args: dict[str, Any]) -> Any:
    store = _store(args)
    status = DecisionStatus(args["status"]) if args.get("status") else None
    scope = DecisionScope(args["decision_scope"]) if args.get("decision_scope") else None
    decisions = store.list_decisions(status=status, decision_scope=scope)
    return {"decisions": [d.to_dict() for d in decisions]}


def tool_record_decision(args: dict[str, Any]) -> Any:
    store = _store(args)
    decision = Decision(
        id=args["id"],
        title=args["title"],
        value=_coerce_json(args.get("value", {})),
        source=DecisionSource(type=DecisionSourceType.USER),
        reason=args.get("reason", ""),
        scope_paths=_coerce_json(args.get("scope_paths", [])),
        decision_scope=DecisionScope(args.get("decision_scope", "project_wide")),
        effects=_coerce_json(args.get("effects", {})),
    )
    store.save_decision(decision)
    return {"decision": decision.to_dict()}


def tool_reopen_decision(args: dict[str, Any]) -> Any:
    store = _store(args)
    decision = store.reopen_decision(args["decision_id"], args["reason"])
    return {"decision": decision.to_dict()}


def tool_list_agents(args: dict[str, Any]) -> Any:
    store = _store(args)
    return {"agents": [_agent_output_dict(a) for a in _generated_agents(store)]}


def tool_generate_agents(args: dict[str, Any]) -> Any:
    root = _root(args)
    store = _store(args)
    profile = _require_profile(store, root)
    decisions = store.list_decisions(status=DecisionStatus.ACTIVE)
    agents = select_agents(profile, decisions)
    manifest = store.load_generated_manifest() or {}
    manifest["agents"] = [a.to_dict() for a in agents]
    store.save_generated_manifest(manifest)
    return {"agents": [_agent_output_dict(a) for a in agents]}


def tool_generate_skills(args: dict[str, Any]) -> Any:
    store = _store(args)
    agents = _generated_agents(store)
    decisions = store.list_decisions(status=DecisionStatus.ACTIVE)
    skills = select_skills(agents, decisions)
    manifest = store.load_generated_manifest() or {}
    manifest["skills"] = [s.to_dict() for s in skills]
    store.save_generated_manifest(manifest)
    return {"skills": [s.to_dict() for s in skills]}


def tool_setup(args: dict[str, Any]) -> Any:
    root = _root(args)
    store = _store(args)
    providers = _coerce_json(args.get("providers", ["claude", "codex"]))
    profile = scan_repository(root)
    store.save_profile(profile)
    decisions = store.list_decisions(status=DecisionStatus.ACTIVE)
    agents = select_agents(profile, decisions)
    skills = select_skills(agents, decisions)
    guard = store.file_guard()
    results = []
    if "claude" in providers:
        results += [r.__dict__ for r in render_claude(root, agents, skills, guard)]
    if "codex" in providers:
        results += [r.__dict__ for r in render_codex(root, agents, skills, guard)]
    store.save_generated_manifest(
        {"agents": [a.to_dict() for a in agents], "skills": [s.to_dict() for s in skills]}
    )
    return {"agents": [a.id for a in agents], "skills": [s.id for s in skills], "files": results}


def tool_prepare_task(args: dict[str, Any]) -> Any:
    """Synthesize an ad-hoc task agent from a confirmed task_preparation interview.

    Requires `session_id` to reference a CONFIRMED session of type
    `task_preparation` (see `start_project_interview` with
    `session_type=task_preparation`, `goal`, and optionally
    `base_agent_ids`) — the proposal must be grounded in answers about
    scope, outcome, and permissions, not just the raw goal string. Both a
    human and a self-interviewing Claude answer through the same
    start/get_next_questions/submit_interview_answers/confirm flow.
    """
    store = _store(args)
    task_id = args["task_id"]
    goal = args["goal"]
    session = _require_session(store, args["session_id"])
    if session.type != SessionType.TASK_PREPARATION:
        raise ValueError(
            f"session '{session.id}' is a {session.type.value} session, not task_preparation"
        )
    if session.status != SessionStatus.CONFIRMED:
        raise ValueError(
            f"session '{session.id}' is not confirmed yet (status={session.status.value}); "
            "answer its questions and call confirm_interview_decisions first"
        )

    base_agent_ids = _coerce_json(args.get("base_agent_ids", []))
    agents_by_id = {a.id: a for a in _generated_agents(store)}
    reused = [agents_by_id[i] for i in base_agent_ids if i in agents_by_id]

    session_decisions = [
        d
        for d in store.list_decisions(status=DecisionStatus.ACTIVE)
        if d.source.interview_session == session.id
    ]
    task_agent = synthesize_task_agent(task_id, goal, session_decisions, reused)
    return {
        "task_agent": _agent_output_dict(task_agent),
        "reused_agents": [_agent_output_dict(a) for a in reused],
        "display": render_agent_display(task_agent),
    }


def tool_generate_swarm_plan(args: dict[str, Any]) -> Any:
    store = _store(args)
    agents_by_id = {a.id: a for a in _generated_agents(store)}
    requested_ids = _coerce_json(args.get("agent_ids", list(agents_by_id.keys())))
    agents = [agents_by_id[i] for i in requested_ids if i in agents_by_id]
    decisions = store.list_decisions(status=DecisionStatus.ACTIVE)
    plan = build_swarm_plan(
        task_id=args["task_id"],
        goal=args["goal"],
        agents=agents,
        phases=_coerce_json(args.get("phases", {})),
        depends_on=_coerce_json(args.get("depends_on", {})),
        file_ownership=_coerce_json(args.get("file_ownership", {})),
        decisions=decisions,
    )
    return {"plan": plan.to_dict(), "text": render_swarm_plan_text(plan, agents_by_id)}


def tool_validate_generated_configuration(args: dict[str, Any]) -> Any:
    store = _store(args)
    manifest = store.load_generated_manifest() or {}
    agents = [AgentDefinition.from_dict(d) for d in manifest.get("agents", [])]
    from .domain import SkillDefinition

    skills = [SkillDefinition.from_dict(d) for d in manifest.get("skills", [])]
    profile = store.load_profile()
    available_tool_ids = (
        {t.id for t in profile.tools if t.availability == "available"} if profile else None
    )
    result = validate_generated_configuration(agents, skills, None, available_tool_ids)
    return {
        "valid": result.valid,
        "violations": [
            {"code": v.code, "message": v.message, "path": v.path} for v in result.violations
        ],
    }


def tool_show_generation_diff(args: dict[str, Any]) -> Any:
    root = _root(args)
    store = _store(args)
    profile = _require_profile(store, root)
    decisions = store.list_decisions(status=DecisionStatus.ACTIVE)
    agents = select_agents(profile, decisions)
    skills = select_skills(agents, decisions)
    dry_guard = cast(GeneratedFileGuard, DryRunFileGuard(store))
    results = render_claude(root, agents, skills, dry_guard) + render_codex(
        root, agents, skills, dry_guard
    )
    return {"files": results}


def tool_start_project_interview(args: dict[str, Any]) -> Any:
    root = _root(args)
    store = _store(args)
    profile = _require_profile(store, root)
    engine = InterviewEngine(store)
    session_type = SessionType(args.get("session_type", "initial_setup"))
    session = engine.start_session(
        session_type,
        profile,
        session_id=args["session_id"],
        goal=args.get("goal"),
        base_agent_ids=_coerce_json(args.get("base_agent_ids", [])),
    )
    return {"session": session.to_dict()}


def tool_get_interview_state(args: dict[str, Any]) -> Any:
    store = _store(args)
    session = _require_session(store, args["session_id"])
    return {"session": session.to_dict()}


def tool_get_next_questions(args: dict[str, Any]) -> Any:
    store = _store(args)
    session = _require_session(store, args["session_id"])
    engine = InterviewEngine(store)
    questions = engine.get_next_questions(session)
    return {"questions": [q.to_dict() for q in questions]}


def tool_submit_interview_answers(args: dict[str, Any]) -> Any:
    store = _store(args)
    session = _require_session(store, args["session_id"])
    engine = InterviewEngine(store)
    raw_answers = []
    for a in _coerce_json(args["answers"]):
        if "value" not in a:
            raise ValueError(
                f"answer for question '{a.get('question_id', '?')}' is missing required "
                f"field 'value' (got keys: {sorted(a.keys())}) — the answer value must be "
                "submitted under the key 'value', not e.g. 'answer'"
            )
        raw_answers.append(
            RawAnswer(
                question_id=a["question_id"],
                value=a["value"],
                free_text=a.get("free_text", ""),
                repository_contradicts=a.get("repository_contradicts", False),
            )
        )
    session, follow_ups = engine.submit_answers(session, raw_answers)
    return {"session": session.to_dict(), "follow_up_questions": [q.to_dict() for q in follow_ups]}


def tool_review_interview_summary(args: dict[str, Any]) -> Any:
    store = _store(args)
    session = _require_session(store, args["session_id"])
    engine = InterviewEngine(store)
    return engine.review_summary(session)


def tool_confirm_interview_decisions(args: dict[str, Any]) -> Any:
    store = _store(args)
    session = _require_session(store, args["session_id"])
    engine = InterviewEngine(store)
    session, decisions = engine.confirm_decisions(session)
    return {"session": session.to_dict(), "decisions": [d.to_dict() for d in decisions]}


def tool_list_open_knowledge_gaps(args: dict[str, Any]) -> Any:
    store = _store(args)
    session = _require_session(store, args["session_id"])
    engine = InterviewEngine(store)
    return {"gaps": [g.to_dict() for g in engine.list_open_knowledge_gaps(session)]}


def _conflicts_path(store: AgentFactoryStore) -> Path:
    return store.base / "generated" / "conflicts.json"


def tool_list_decision_conflicts(args: dict[str, Any]) -> Any:
    root = _root(args)
    store = _store(args)
    session = _require_session(store, args["session_id"])
    profile = _require_profile(store, root)
    engine = InterviewEngine(store)
    conflicts = engine.list_decision_conflicts(session, profile)
    write_json(_conflicts_path(store), [c.to_dict() for c in conflicts])
    return {"conflicts": [c.to_dict() for c in conflicts]}


_SUPERSEDE_OTHERS_RESOLUTION = "keep the most recent decision and supersede the others"


def tool_resolve_decision_conflict(args: dict[str, Any]) -> Any:
    from .domain import ConflictRecord, ConflictType

    store = _store(args)
    raw = read_json(_conflicts_path(store), [])
    conflicts = [ConflictRecord.from_dict(c) for c in raw]
    target = next((c for c in conflicts if c.id == args["conflict_id"]), None)
    if target is None:
        raise KeyError(f"unknown conflict id: {args['conflict_id']}")
    resolved = resolve_conflict(target, args["resolution"])
    conflicts = [resolved if c.id == resolved.id else c for c in conflicts]
    write_json(_conflicts_path(store), [c.to_dict() for c in conflicts])

    superseded: list[str] = []
    if (
        resolved.type == ConflictType.USER_VS_USER
        and resolved.resolution == _SUPERSEDE_OTHERS_RESOLUTION
    ):
        losing_ids = [entry.split(": ", 1)[0] for entry in resolved.evidence]
        losers = store.supersede_by_existing(
            losing_ids,
            resolved.decision_id,
            reason=f"superseded by '{resolved.decision_id}' resolving conflict '{resolved.id}'",
        )
        superseded = [d.id for d in losers]

    return {"conflict": resolved.to_dict(), "superseded_decisions": superseded}


DISPATCH = {
    "analyze_project": tool_analyze_project,
    "setup": tool_setup,
    "get_project_profile": tool_get_project_profile,
    "list_decisions": tool_list_decisions,
    "record_decision": tool_record_decision,
    "reopen_decision": tool_reopen_decision,
    "list_agents": tool_list_agents,
    "generate_agents": tool_generate_agents,
    "generate_skills": tool_generate_skills,
    "prepare_task": tool_prepare_task,
    "generate_swarm_plan": tool_generate_swarm_plan,
    "validate_generated_configuration": tool_validate_generated_configuration,
    "show_generation_diff": tool_show_generation_diff,
    "start_project_interview": tool_start_project_interview,
    "get_interview_state": tool_get_interview_state,
    "get_next_questions": tool_get_next_questions,
    "submit_interview_answers": tool_submit_interview_answers,
    "review_interview_summary": tool_review_interview_summary,
    "confirm_interview_decisions": tool_confirm_interview_decisions,
    "list_open_knowledge_gaps": tool_list_open_knowledge_gaps,
    "list_decision_conflicts": tool_list_decision_conflicts,
    "resolve_decision_conflict": tool_resolve_decision_conflict,
}


def serve() -> int:
    for raw in sys.stdin:
        request: dict[str, Any] | None = None
        try:
            request = json.loads(raw)
            method = request.get("method")
            params: dict[str, Any] = request.get("params", {})
            if "id" not in request:
                continue
            if method == "initialize":
                result: Any = {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "quattroagents-agent-factory",
                        "version": runtime_version(),
                    },
                    "capabilities": {"tools": {}},
                }
            elif method == "tools/list":
                result = {
                    "tools": [
                        {
                            "name": name,
                            "description": name.replace("_", " "),
                            "inputSchema": INPUT_SCHEMA,
                        }
                        for name in TOOLS
                    ]
                }
            elif method == "tools/call":
                name, args = params["name"], params.get("arguments", {})
                handler = DISPATCH.get(name)
                out = handler(args) if handler is not None else {"error": f"unknown tool: {name}"}
                result = {"content": [{"type": "text", "text": json.dumps(out)}]}
            else:
                result = {}
            print(
                json.dumps({"jsonrpc": "2.0", "id": request.get("id"), "result": result}),
                flush=True,
            )
        except Exception as exc:
            request_id = request.get("id") if isinstance(request, dict) else None
            print(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32000, "message": str(exc)},
                    }
                ),
                flush=True,
            )
    return 0

from __future__ import annotations

from typing import Any


def build_interview_brief(analysis: dict[str, object]) -> dict[str, Any]:
    """Turn brownfield facts into the user-intent questions required before planning."""
    return {
        "schema_version": 1,
        "stage": "intent_before_planning",
        "analysis": {
            "languages": analysis.get("languages", []),
            "ci": analysis.get("ci", []),
            "codex": analysis.get("codex", False),
            "claude": analysis.get("claude", False),
        },
        "questions": [
            {
                "id": "INTENT-1",
                "required": True,
                "question": "What outcome should this change deliver for the user or project?",
            },
            {
                "id": "INTENT-2",
                "required": True,
                "question": "What is explicitly in scope and out of scope for this task?",
            },
            {
                "id": "INTENT-3",
                "required": True,
                "question": "What acceptance evidence proves the outcome is correct?",
            },
            {
                "id": "INTENT-4",
                "required": True,
                "question": "Which files, subsystems, safety constraints, or approvals must be respected?",
            },
            {
                "id": "INTENT-5",
                "required": True,
                "question": "Which work can be safely parallelized, and which parts require review or a human decision?",
            },
        ],
        "handoff": [
            "Record confirmed answers in the task contract.",
            "Run swarm planning only after the task contract has an objective, scope, evidence, and boundaries.",
            "Use user-approved work items to shape bounded worker packets.",
        ],
        "boundaries": [
            "The interview command does not infer user intent from source code.",
            "The interview command does not create agents, tasks, or configuration.",
        ],
    }


def render_interview_brief_markdown(brief: dict[str, Any]) -> str:
    """Render the deterministic user-intent interview for a brownfield project."""
    languages = ", ".join(brief["analysis"]["languages"]) or "not detected"
    ci = ", ".join(brief["analysis"]["ci"]) or "not detected"
    lines = [
        "# User-intent interview",
        "",
        "Complete this after repository analysis and before creating worker packets.",
        "",
        "## Brownfield facts",
        "",
        f"- Languages: {languages}",
        f"- CI: {ci}",
        "",
        "## Required answers",
        "",
    ]
    lines.extend(f"- {item['id']}: {item['question']}" for item in brief["questions"])
    lines.extend(["", "## Handoff", ""])
    lines.extend(f"- {item}" for item in brief["handoff"])
    lines.append("")
    return "\n".join(lines)


def _string_list(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field} must be a list of strings")
    return sorted(set(value))


def _requirement_ids(payload: dict[str, Any]) -> list[str]:
    requirements = payload.get("requirements", [])
    if not isinstance(requirements, list):
        raise ValueError("requirements must be a list")
    identifiers: list[str] = []
    for requirement in requirements:
        if not isinstance(requirement, dict) or not isinstance(requirement.get("id"), str):
            raise ValueError("requirement must define a string id")
        identifiers.append(requirement["id"])
    return identifiers


def _work_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    configured = payload.get("swarm_work_items", [])
    if configured == []:
        objective = payload.get("objective", "")
        if not isinstance(objective, str) or not objective:
            raise ValueError("task objective must be a non-empty string")
        return [
            {
                "id": "worker-1",
                "objective": objective,
                "requirements": _requirement_ids(payload),
                "allowed_files": _string_list(payload.get("allowed_files", []), "allowed_files"),
                "context_refs": _string_list(payload.get("context_refs", []), "context_refs"),
                "depends_on": [],
            }
        ]
    if not isinstance(configured, list) or not configured:
        raise ValueError("swarm_work_items must be a non-empty list")
    items: list[dict[str, Any]] = []
    for item in configured:
        if not isinstance(item, dict):
            raise ValueError("swarm work item must be an object")
        identifier = item.get("id")
        objective = item.get("objective")
        if not isinstance(identifier, str) or not identifier:
            raise ValueError("swarm work item id must be a non-empty string")
        if not isinstance(objective, str) or not objective:
            raise ValueError("swarm work item objective must be a non-empty string")
        items.append(
            {
                "id": identifier,
                "objective": objective,
                "requirements": _string_list(item.get("requirements", []), "requirements"),
                "allowed_files": _string_list(item.get("allowed_files", []), "allowed_files"),
                "context_refs": _string_list(item.get("context_refs", []), "context_refs"),
                "depends_on": _string_list(item.get("depends_on", []), "depends_on"),
            }
        )
    if len({item["id"] for item in items}) != len(items):
        raise ValueError("swarm work item ids must be unique")
    return sorted(items, key=lambda item: item["id"])


def _context_summary(payload: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    _requirement_ids(payload)
    requirements = {
        requirement["id"]: requirement["text"]
        for requirement in payload["requirements"]
        if isinstance(requirement, dict)
        and isinstance(requirement.get("id"), str)
        and isinstance(requirement.get("text"), str)
    }
    unknown = set(item["requirements"]) - requirements.keys()
    if unknown:
        raise ValueError(f"unknown swarm requirement: {sorted(unknown)[0]}")
    acceptance_commands = _string_list(
        payload.get("acceptance_commands", []), "acceptance_commands"
    )
    return {
        "objective": item["objective"],
        "requirements": [
            {"id": identifier, "text": requirements[identifier]}
            for identifier in item["requirements"]
        ],
        "allowed_files": item["allowed_files"],
        "context_refs": item["context_refs"],
        "acceptance_commands": acceptance_commands,
        "tooling": [
            "Use Codebase Memory MCP for code discovery.",
            "Use Context7 only for external library or API documentation.",
            "Use RTK only when installed and concise diagnostics are useful.",
        ],
    }


def _files_overlap(first: set[str], second: set[str]) -> bool:
    for left in first:
        for right in second:
            left_path = left.rstrip("/")
            right_path = right.rstrip("/")
            if (
                left_path == "*"
                or right_path == "*"
                or left_path == right_path
                or left_path.startswith(right_path + "/")
                or right_path.startswith(left_path + "/")
            ):
                return True
    return False


def _waves(items: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    by_id = {item["id"]: item for item in items}
    for item in items:
        unknown = set(item["depends_on"]) - by_id.keys()
        if unknown:
            raise ValueError(f"unknown swarm dependency: {sorted(unknown)[0]}")
        if item["id"] in item["depends_on"]:
            raise ValueError("swarm work item cannot depend on itself")
    completed: set[str] = set()
    waves: list[list[dict[str, Any]]] = []
    while len(completed) < len(items):
        ready = [
            item
            for item in items
            if item["id"] not in completed and set(item["depends_on"]).issubset(completed)
        ]
        if not ready:
            raise ValueError("swarm dependencies contain a cycle")
        selected: list[dict[str, Any]] = []
        claimed_files: set[str] = set()
        for item in ready:
            files = set(item["allowed_files"])
            if not _files_overlap(claimed_files, files):
                selected.append(item)
                claimed_files.update(files)
        completed.update(item["id"] for item in selected)
        waves.append(selected)
    return waves


def build_swarm_plan(task: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic, plan-only swarm handoff from a stored task contract."""
    payload = task["payload"]
    if not isinstance(payload, dict):
        raise ValueError("task payload must be an object")
    task_id = task.get("id")
    if not isinstance(task_id, str) or not task_id:
        raise ValueError("task id must be a non-empty string")
    items = _work_items(payload)
    waves = _waves(items)
    worker_packets = {
        item["id"]: {
            "id": item["id"],
            "role": "bounded_worker",
            "depends_on": item["depends_on"],
            "context_summary": _context_summary(payload, item),
        }
        for item in items
    }
    return {
        "schema_version": 1,
        "mode": "plan_only",
        "task_id": task_id,
        "milestone": task.get("milestone") or payload.get("milestone"),
        "coordinator": {
            "role": "coordinator",
            "responsibilities": [
                "Assign only the generated work packets.",
                "Do not launch agents or modify files automatically.",
                "Require acceptance evidence before independent review.",
            ],
        },
        "waves": [
            {
                "id": f"wave-{index}",
                "parallel": len(wave) > 1,
                "workers": [worker_packets[item["id"]] for item in wave],
            }
            for index, wave in enumerate(waves, start=1)
        ],
        "review": {
            "role": "independent_reviewer",
            "depends_on": [item["id"] for item in items],
            "instructions": "Review artifacts and gate evidence after every worker wave completes.",
        },
        "boundaries": [
            "This plan does not launch agents or subagents.",
            "This plan does not create immutable run snapshots.",
            "This plan does not activate configuration changes.",
        ],
    }


def render_swarm_plan_markdown(plan: dict[str, Any]) -> str:
    """Render a compact deterministic plan suitable for a human coordinator."""
    lines = [
        f"# Swarm plan: {plan['task_id']}",
        "",
        "Plan only: no agent or subagent is launched by this command.",
        "",
        "## Waves",
        "",
    ]
    for wave in plan["waves"]:
        lines.extend([f"### {wave['id']}", ""])
        for worker in wave["workers"]:
            context = worker["context_summary"]
            files = ", ".join(context["allowed_files"]) or "none"
            refs = ", ".join(context["context_refs"]) or "none"
            lines.append(f"- `{worker['id']}` ({worker['role']}): {context['objective']}")
            lines.append(f"  - allowed files: {files}")
            lines.append(f"  - context refs: {refs}")
        lines.append("")
    review = plan["review"]
    lines.extend(
        [
            "## Review",
            "",
            f"- `{review['role']}` after: {', '.join(review['depends_on'])}",
            f"- {review['instructions']}",
            "",
        ]
    )
    return "\n".join(lines)

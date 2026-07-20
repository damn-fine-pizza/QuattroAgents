from __future__ import annotations

import sys
from typing import Any

_BASE_QUESTIONS = (
    {
        "id": "SETUP-1",
        "required": True,
        "question": (
            "What is this project's primary purpose, and what should generated agents optimize for?"
        ),
    },
    {
        "id": "SETUP-2",
        "required": True,
        "question": (
            "Should generated workers default to small bounded changes, "
            "or is broader autonomous work acceptable?"
        ),
    },
    {
        "id": "SETUP-3",
        "required": True,
        "question": (
            "Which external tools (e.g. rtk, codebase-memory-mcp) should generated agents "
            "be instructed to use?"
        ),
    },
)


def build_setup_interview_brief(
    analysis: dict[str, Any], history: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Turn project analysis and prior setup history into project-scoped setup questions."""
    languages = analysis.get("languages", [])
    ci = analysis.get("ci", [])
    questions = [dict(item) for item in _BASE_QUESTIONS]
    for language in languages:
        questions.append(
            {
                "id": f"SETUP-LANG-{language}",
                "required": False,
                "question": (
                    f"Any {language}-specific conventions (test runner, lint, build) "
                    "generated agents should follow?"
                ),
            }
        )
    if history:
        questions.append(
            {
                "id": "SETUP-HISTORY",
                "required": False,
                "question": "Anything from the previous setup that should change this time?",
            }
        )
    return {
        "schema_version": 1,
        "stage": "project_setup",
        "analysis": {"languages": languages, "ci": ci},
        "history_considered": [record.get("recorded_at") for record in (history or [])],
        "questions": questions,
        "boundaries": [
            "The setup interview does not infer answers from source code.",
            "The setup interview only informs agent/skill synthesis; it does not itself write files.",
        ],
    }


def render_setup_interview_brief_markdown(brief: dict[str, Any]) -> str:
    """Render the deterministic project-setup interview brief."""
    languages = ", ".join(brief["analysis"]["languages"]) or "not detected"
    ci = ", ".join(brief["analysis"]["ci"]) or "not detected"
    lines = [
        "# Project setup interview",
        "",
        "Complete this before generating agents and skills.",
        "",
        "## Project facts",
        "",
        f"- Languages: {languages}",
        f"- CI: {ci}",
        "",
        "## Questions",
        "",
    ]
    for item in brief["questions"]:
        suffix = "" if item["required"] else " (optional)"
        lines.append(f"- {item['id']}{suffix}: {item['question']}")
    lines.append("")
    return "\n".join(lines)


def _required_ids(brief: dict[str, Any]) -> tuple[str, ...]:
    return tuple(item["id"] for item in brief["questions"] if item["required"])


def confirm_setup_interview(brief: dict[str, Any], answers: dict[str, str]) -> dict[str, Any]:
    """Validate a user's answers and return a setup-history-ready interview record."""
    confirmed: dict[str, str] = {}
    for identifier in _required_ids(brief):
        answer = answers.get(identifier)
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError(f"missing confirmed answer: {identifier}")
        confirmed[identifier] = answer.strip()
    for item in brief["questions"]:
        if item["required"]:
            continue
        answer = answers.get(item["id"])
        if isinstance(answer, str) and answer.strip():
            confirmed[item["id"]] = answer.strip()
    return {
        "schema_version": 1,
        "status": "confirmed",
        "answers": confirmed,
        "analysis": brief["analysis"],
        "source": "interactive",
    }


def conduct_setup_interview(brief: dict[str, Any]) -> dict[str, Any]:
    """Prompt a terminal user for setup answers without storing them."""
    answers: dict[str, str] = {}
    for item in brief["questions"]:
        marker = "" if item["required"] else " (optional)"
        print(f"{item['id']}{marker} — {item['question']}\n> ", end="", file=sys.stderr, flush=True)
        answers[item["id"]] = input()
    return confirm_setup_interview(brief, answers)


def default_setup_interview(brief: dict[str, Any]) -> dict[str, Any]:
    """A non-blocking baseline record used when no interactive/history answers are available."""
    return {
        "schema_version": 1,
        "status": "default",
        "answers": {},
        "analysis": brief["analysis"],
        "source": "baseline",
    }


def carry_forward_setup_interview(previous_interview: dict[str, Any]) -> dict[str, Any]:
    """Reuse a previous confirmed/default interview record for a new setup run."""
    return {**previous_interview, "status": "carried_forward", "source": "history"}

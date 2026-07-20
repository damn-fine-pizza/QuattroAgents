from __future__ import annotations

import copy
from typing import Any

from .models import Tier

_TIER_VALUES = {tier.value for tier in Tier}

DEFAULT_MANIFEST: dict[str, Any] = {
    "schema_version": 1,
    "roles": [
        {
            "name": "bounded-worker",
            "tier": "small",
            "source": "fleet-default",
            "description": "Implements explicitly scoped, low-risk changes.",
            "instructions": (
                "Work only from the Codex coordinator's assigned packet. Claim and lease the "
                "assigned contract, implement only that bounded task, preserve unrelated "
                "changes, and report the packet's result envelope with changed files and "
                "verification."
            ),
            "claude_model": "sonnet",
            "claude_max_turns": 12,
        },
        {
            "name": "semantic-reviewer",
            "tier": "medium",
            "source": "fleet-default",
            "description": "Reviews behavioral correctness, compatibility, and test coverage.",
            "instructions": (
                "Independently review a final diff and its acceptance evidence for work you "
                "did not implement. Check behavioral correctness, compatibility, claims and "
                "lease discipline, and test coverage. Do not modify files; report actionable "
                "findings with evidence."
            ),
            "claude_model": "sonnet",
            "claude_max_turns": 20,
        },
        {
            "name": "architecture-adjudicator",
            "tier": "large",
            "source": "fleet-default",
            "description": "Reviews architectural trade-offs and protected-boundary impact.",
            "instructions": (
                "Assess architectural trade-offs and protected-boundary impact before "
                "implementation. Do not modify files; identify recommended decisions and "
                "approvals required for protected changes."
            ),
            "claude_model": "opus",
            "claude_max_turns": 24,
        },
    ],
    "skills": [
        {"name": "qagents-bootstrap", "source": "fleet-default", "body": None},
        {"name": "qagents-plan", "source": "fleet-default", "body": None},
        {"name": "qagents-execute", "source": "fleet-default", "body": None},
        {"name": "qagents-review", "source": "fleet-default", "body": None},
        {"name": "qagents-reconfigure", "source": "fleet-default", "body": None},
        {"name": "qagents-benchmark", "source": "fleet-default", "body": None},
        {"name": "qagents-orchestrate", "source": "fleet-default", "body": None},
    ],
    "rationale": {
        "languages_considered": [],
        "interview_answers_used": [],
        "history_reused": [],
    },
}


def _validate_tier(tier: str) -> str:
    if tier not in _TIER_VALUES:
        raise ValueError(f"invalid tier: {tier}")
    return tier


def _skill_body(name: str, description: str, body: str) -> str:
    header = f"---\nname: {name}\ndescription: {description}\n---\n\n"
    return header + body


def synthesize(
    analysis: dict[str, Any],
    interview: dict[str, Any],
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Produce a role/skill manifest from project analysis, interview answers, and history.

    With no confirmed interview answers (the baseline/default case), this reproduces
    DEFAULT_MANIFEST's roles and skills unchanged, so a non-interactive `setup --yes`
    run stays content-equivalent to the prior fixed-template behavior.
    """
    manifest = copy.deepcopy(DEFAULT_MANIFEST)
    for role in manifest["roles"]:
        _validate_tier(role["tier"])

    languages = list(analysis.get("languages", []))
    answers = interview.get("answers") or {}
    answers_used: list[str] = []

    tool_answer = answers.get("SETUP-3")
    if tool_answer:
        manifest["skills"].append(
            {
                "name": "qagents-tooling",
                "source": "adhoc",
                "body": _skill_body(
                    "qagents-tooling",
                    "Project-specific tooling guidance",
                    "Use the following tools as directed by the project setup interview: "
                    f"{tool_answer}\n",
                ),
            }
        )
        answers_used.append("SETUP-3")

    for language in languages:
        language_answer = answers.get(f"SETUP-LANG-{language}")
        if language_answer:
            skill_name = f"qagents-{language}-conventions"
            manifest["skills"].append(
                {
                    "name": skill_name,
                    "source": "adhoc",
                    "body": _skill_body(
                        skill_name,
                        f"{language} conventions for generated agents",
                        f"{language_answer}\n",
                    ),
                }
            )
            answers_used.append(f"SETUP-LANG-{language}")

    purpose_answer = answers.get("SETUP-1")
    scope_answer = answers.get("SETUP-2")
    if purpose_answer or scope_answer:
        extra = []
        if purpose_answer:
            extra.append(f"Project purpose: {purpose_answer}")
            answers_used.append("SETUP-1")
        if scope_answer:
            extra.append(f"Scope guidance: {scope_answer}")
            answers_used.append("SETUP-2")
        addendum = "\n\n" + " ".join(extra)
        for role in manifest["roles"]:
            role["instructions"] = role["instructions"] + addendum
            role["source"] = "adhoc"

    manifest["rationale"] = {
        "languages_considered": languages,
        "interview_answers_used": sorted(set(answers_used)),
        "history_reused": [
            record["_filename"] for record in (history or []) if record.get("_filename")
        ],
    }
    return manifest

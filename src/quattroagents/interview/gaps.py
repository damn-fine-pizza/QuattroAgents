"""Knowledge gap detection for the Interview Engine.

Surfaces only gaps for things the repository cannot tell us directly.
All gap detection is deterministic with no randomness.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quattroagents.domain import Decision, ProjectProfile

from quattroagents.domain import (
    DecisionStatus,
    GapStatus,
    GapType,
    KnowledgeGap,
    Priority,
)


def detect_knowledge_gaps(
    profile: ProjectProfile, active_decisions: list[Decision]
) -> list[KnowledgeGap]:
    """Detect knowledge gaps from repository profile and active decisions.

    Only surfaces gaps for things the repository cannot tell us. Generates gaps
    from deterministic, concrete triggers with no randomness.

    Args:
        profile: The analyzed project profile.
        active_decisions: List of currently active decisions.

    Returns:
        List of detected KnowledgeGap objects with OPEN status and current timestamp.
    """
    gaps: list[KnowledgeGap] = []

    # Compute timestamp once for all gaps in this batch
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1. Legacy/duplicate ambiguity
    for index, risk in enumerate(profile.risks):
        if risk.startswith("duplicate implementation name"):
            name_match = re.search(r"'([^']*)'", risk)
            duplicate_name = name_match.group(1) if name_match else f"item-{index}"
            gap = KnowledgeGap(
                id=f"legacy-authority-{index}",
                topic=f"legacy/duplicate implementations: {duplicate_name}",
                description=f"Multiple implementations were found: {risk}. Which one should be considered authoritative for new work?",
                gap_type=GapType.AMBIGUOUS_ARCHITECTURE,
                evidence=[risk],
                impact={
                    "agents": "high",
                    "skills": "low",
                    "swarm": "medium",
                    "permissions": "low",
                },
                confidence=0.6,
                priority=Priority.HIGH,
                status=GapStatus.OPEN,
                created_at=timestamp,
                updated_at=timestamp,
            )
            gaps.append(gap)

    # 2. Legacy area ownership
    if profile.legacy_areas:
        gap = KnowledgeGap(
            id="legacy-area-ownership",
            topic="legacy code ownership",
            description=f"{len(profile.legacy_areas)} file(s) appear to be legacy/deprecated. Should generated agents avoid modifying these unless explicitly instructed?",
            gap_type=GapType.MISSING_OWNERSHIP,
            evidence=list(profile.legacy_areas[:5]),
            impact={
                "agents": "medium",
                "skills": "low",
                "swarm": "low",
                "permissions": "high",
            },
            confidence=0.5,
            priority=Priority.MEDIUM,
            status=GapStatus.OPEN,
            created_at=timestamp,
            updated_at=timestamp,
        )
        gaps.append(gap)

    # 3. Missing test policy
    if not profile.test_frameworks:
        gap = KnowledgeGap(
            id="missing-test-policy",
            topic="test coverage policy",
            description="No test framework was detected. Should generated agents be required to add tests for new behavior, or is this project validated some other way?",
            gap_type=GapType.MISSING_VALIDATION_RULE,
            evidence=[],
            impact={
                "agents": "high",
                "skills": "medium",
                "swarm": "low",
                "permissions": "low",
            },
            confidence=0.7,
            priority=Priority.HIGH,
            status=GapStatus.OPEN,
            created_at=timestamp,
            updated_at=timestamp,
        )
        gaps.append(gap)

    # 4. Multiple languages, no stated priority
    if len(profile.languages) >= 2:
        gap = KnowledgeGap(
            id="multi-language-priority",
            topic="primary language",
            description=f"Multiple languages were detected ({', '.join(profile.languages)}). Is one of them primary for new agent-generated work, or should agents treat them equally?",
            gap_type=GapType.MISSING_PRIORITY,
            evidence=list(profile.languages),
            impact={
                "agents": "medium",
                "skills": "medium",
                "swarm": "low",
                "permissions": "low",
            },
            confidence=0.6,
            priority=Priority.MEDIUM,
            status=GapStatus.OPEN,
            created_at=timestamp,
            updated_at=timestamp,
        )
        gaps.append(gap)

    # 5. Unavailable-but-referenced tools
    for tool in profile.tools:
        if tool.availability == "unavailable" and tool.id in ("rtk", "codebase-memory-mcp"):
            gap = KnowledgeGap(
                id=f"tool-policy-{tool.id}",
                topic=f"{tool.id} usage policy",
                description=f"'{tool.id}' is not installed. Should generated agents assume it may become available later, or should all references to it be omitted?",
                gap_type=GapType.MISSING_TOOL_POLICY,
                evidence=[f"{tool.id}: unavailable"],
                impact={
                    "agents": "low",
                    "skills": "medium",
                    "swarm": "low",
                    "permissions": "low",
                },
                confidence=0.4,
                priority=Priority.LOW,
                status=GapStatus.OPEN,
                created_at=timestamp,
                updated_at=timestamp,
            )
            gaps.append(gap)

    # 6. No write-permission policy stated
    has_autonomy_decision = any(
        "autonomy" in decision.title.lower() or "write permission" in decision.title.lower()
        for decision in active_decisions
    )
    if not has_autonomy_decision:
        gap = KnowledgeGap(
            id="agent-autonomy-level",
            topic="agent autonomy",
            description="What level of autonomy should generated agents have — can they modify code directly, or should they limit themselves to analysis and review?",
            gap_type=GapType.MISSING_PRIORITY,
            evidence=[],
            impact={
                "agents": "high",
                "skills": "medium",
                "swarm": "medium",
                "permissions": "high",
            },
            confidence=0.5,
            priority=Priority.HIGH,
            status=GapStatus.OPEN,
            created_at=timestamp,
            updated_at=timestamp,
        )
        gaps.append(gap)

    return gaps


def find_stale_decisions(
    active_decisions: list[Decision], profile: ProjectProfile
) -> list[KnowledgeGap]:
    """Find decisions scoped to subsystems that no longer exist in the profile.

    For each ACTIVE decision, checks whether all scope_paths still exist as
    subsystems in the current profile. If a decision was scoped to a subsystem
    that no longer exists, returns a STALE_DECISION gap.

    Args:
        active_decisions: List of decisions to check (typically filtered to ACTIVE status).
        profile: The current analyzed project profile.

    Returns:
        List of KnowledgeGap objects with gap_type=STALE_DECISION for decisions
        whose scoped subsystems no longer exist.
    """
    gaps: list[KnowledgeGap] = []

    # Compute timestamp once for all gaps in this batch
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    subsystem_set = set(profile.subsystems)

    for decision in active_decisions:
        if decision.status != DecisionStatus.ACTIVE:
            continue

        # Check if any scope path is not in current subsystems
        for scope_path in decision.scope_paths:
            if scope_path not in subsystem_set:
                gap = KnowledgeGap(
                    id=f"stale-{decision.id}",
                    topic=f"stale decision: {decision.title}",
                    description=f"Decision '{decision.title}' was scoped to {decision.scope_paths}, but the repository no longer shows that subsystem. Is this decision still valid?",
                    gap_type=GapType.STALE_DECISION,
                    evidence=list(decision.scope_paths),
                    impact={
                        "agents": "medium",
                        "skills": "low",
                        "swarm": "low",
                        "permissions": "low",
                    },
                    confidence=0.5,
                    priority=Priority.MEDIUM,
                    status=GapStatus.OPEN,
                    created_at=timestamp,
                    updated_at=timestamp,
                )
                gaps.append(gap)
                break  # Only one gap per decision

    return gaps

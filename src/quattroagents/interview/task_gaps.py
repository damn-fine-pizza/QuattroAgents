"""Task-scoped knowledge gap detection for TASK_PREPARATION interview sessions.

`gaps.py`'s `detect_knowledge_gaps` surfaces only what a *repository* cannot
tell us about project-wide policy. An ad-hoc, single-task agent request is
different: its scope, its definition of "done", and its permission needs
can never be inferred from the repository at all — they're intrinsic to the
request itself and must come from whoever is making it, whether that's a
human answering interactively or Claude running a self-interview over the
same tool surface (`start_project_interview` -> `get_next_questions` ->
`submit_interview_answers` -> `confirm_interview_decisions`). So, unlike
`detect_knowledge_gaps`, these gaps are not conditional on profile state —
they are always asked, once per task.
"""

from __future__ import annotations

from datetime import UTC, datetime

from quattroagents.domain import GapStatus, GapType, KnowledgeGap, Priority

TASK_SCOPE_BOUNDARY_TOPIC = "task scope boundary"
TASK_COMPLETION_OUTCOME_TOPIC = "task completion outcome"
TASK_WRITE_PERMISSION_TOPIC = "task write permission"
TASK_REUSE_TOPIC = "task reuse vs new agent"


def detect_task_gaps(goal: str, base_agent_ids: list[str]) -> list[KnowledgeGap]:
    """Detect the fixed set of knowledge gaps intrinsic to any ad-hoc task request.

    Args:
        goal: The task's stated goal, as given to `prepare_task`.
        base_agent_ids: Existing generated agent ids offered for reuse.

    Returns:
        List of OPEN KnowledgeGap objects, always non-empty for a non-empty goal.
    """
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    gaps = [
        KnowledgeGap(
            id="task-scope-boundary",
            topic=TASK_SCOPE_BOUNDARY_TOPIC,
            description=(
                f"For the task '{goal}': what exactly is in scope, and what "
                "should the agent explicitly avoid touching?"
            ),
            gap_type=GapType.MISSING_CONSTRAINT,
            evidence=[goal],
            impact={"agents": "high", "skills": "low", "swarm": "low", "permissions": "medium"},
            confidence=0.2,
            priority=Priority.HIGH,
            status=GapStatus.OPEN,
            created_at=timestamp,
            updated_at=timestamp,
        ),
        KnowledgeGap(
            id="task-completion-outcome",
            topic=TASK_COMPLETION_OUTCOME_TOPIC,
            description=(
                f"For the task '{goal}': what concrete, verifiable outcome means this task is done?"
            ),
            gap_type=GapType.MISSING_FACT,
            evidence=[goal],
            impact={"agents": "high", "skills": "low", "swarm": "low", "permissions": "low"},
            confidence=0.2,
            priority=Priority.HIGH,
            status=GapStatus.OPEN,
            created_at=timestamp,
            updated_at=timestamp,
        ),
        KnowledgeGap(
            id="task-write-permission",
            topic=TASK_WRITE_PERMISSION_TOPIC,
            description=(
                f"Does completing '{goal}' require writing/modifying files, "
                "or is it read-only analysis/review?"
            ),
            gap_type=GapType.MISSING_PRIORITY,
            evidence=[goal],
            impact={"agents": "high", "skills": "low", "swarm": "low", "permissions": "high"},
            confidence=0.2,
            priority=Priority.HIGH,
            status=GapStatus.OPEN,
            created_at=timestamp,
            updated_at=timestamp,
        ),
    ]

    if base_agent_ids:
        gaps.append(
            KnowledgeGap(
                id="task-reuse-check",
                topic=TASK_REUSE_TOPIC,
                description=(
                    f"Should this task reuse capabilities from existing agents "
                    f"({', '.join(base_agent_ids)}) instead of a new ad-hoc one, "
                    "or is a dedicated ad-hoc agent still needed?"
                ),
                gap_type=GapType.MISSING_FACT,
                evidence=list(base_agent_ids),
                impact={"agents": "medium", "skills": "low", "swarm": "low", "permissions": "low"},
                confidence=0.3,
                priority=Priority.MEDIUM,
                status=GapStatus.OPEN,
                created_at=timestamp,
                updated_at=timestamp,
            )
        )

    return gaps

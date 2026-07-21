"""Ad-hoc task agent synthesis grounded in a confirmed TASK_PREPARATION interview.

Unlike the archetype catalog (`archetypes.py`), a task agent is a one-off
`AgentDefinition` scoped to a single ad-hoc request (e.g. "generate a
minimal agent to refactor this specific type of error"). It must still be
grounded in real answers about scope, outcome, and permissions rather than
fabricated from the goal string alone — the same commitment the archetype
system makes to defining what an agent actually does before generating its
instructions. Those answers arrive as `Decision` records produced by
confirming a `task_preparation`-type interview session (see
`interview/task_gaps.py` and `interview/engine.py`), matched back to their
originating gap by `Decision.title`, which `answer_to_decision` always sets
to `KnowledgeGap.topic`.
"""

from __future__ import annotations

from ..domain import (
    AgentDefinition,
    AgentLifetime,
    AgentMode,
    AgentPermissions,
    Decision,
    DefinitionSource,
    Model,
)
from ..interview.task_gaps import (
    TASK_COMPLETION_OUTCOME_TOPIC,
    TASK_SCOPE_BOUNDARY_TOPIC,
    TASK_WRITE_PERMISSION_TOPIC,
)

_AFFIRMATIVE_PREFIXES = ("yes", "y", "true", "write", "needs write", "requires write")


def _decision_text(decision: Decision | None) -> str:
    if decision is None:
        return ""
    detail = str(decision.value.get("detail", "")).strip()
    if detail:
        return detail
    return str(decision.value.get("answer", "")).strip()


def _looks_affirmative(text: str) -> bool:
    normalized = text.strip().lower()
    return normalized.startswith(_AFFIRMATIVE_PREFIXES)


def synthesize_task_agent(
    task_id: str,
    goal: str,
    decisions: list[Decision],
    reused_agents: list[AgentDefinition],
) -> AgentDefinition:
    """Build a one-off AgentDefinition for an ad-hoc task from confirmed interview decisions.

    Args:
        task_id: Unique task identifier.
        goal: The task's stated goal.
        decisions: Decisions confirmed for this task's `task_preparation`
            interview session (already filtered to that session by the caller).
        reused_agents: Existing generated agents offered for reuse, used to
            note what this task agent should defer to instead of duplicating.

    Returns:
        A fully-specified, task-scoped AgentDefinition.
    """
    by_topic = {d.title: d for d in decisions}

    scope_text = _decision_text(by_topic.get(TASK_SCOPE_BOUNDARY_TOPIC))
    outcome_text = _decision_text(by_topic.get(TASK_COMPLETION_OUTCOME_TOPIC))
    wants_write = _looks_affirmative(_decision_text(by_topic.get(TASK_WRITE_PERMISSION_TOPIC)))

    responsibilities = [goal]
    if scope_text:
        responsibilities.append(f"Stay within: {scope_text}")
    if reused_agents:
        responsibilities.append(
            "Defer to existing agents for anything already covered by: "
            + ", ".join(a.id for a in reused_agents)
        )

    completion_criteria = (
        [outcome_text] if outcome_text else ["requested behavior for this task is covered"]
    )

    return AgentDefinition(
        id=f"task-{task_id}",
        description=f"Ad-hoc agent prepared for task '{task_id}': {goal}",
        responsibilities=responsibilities,
        scope=scope_text or goal,
        when_to_use=f"For this task only: {goal}",
        when_not_to_use=(
            f"Outside the declared scope boundary: {scope_text}"
            if scope_text
            else "Outside this task's declared goal"
        ),
        mode=AgentMode.WRITE if wants_write else AgentMode.READ_ONLY,
        permissions=AgentPermissions(can_read_files=True, can_write_files=wants_write),
        lifetime=AgentLifetime.TASK_TEMPORARY,
        source=DefinitionSource.TASK_TEMPORARY,
        preferred_model=Model.SONNET,
        completion_criteria=completion_criteria,
    )

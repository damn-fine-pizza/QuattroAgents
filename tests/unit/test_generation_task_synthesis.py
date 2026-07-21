"""Tests for ad-hoc task agent synthesis (generation/task_synthesis.py)."""

from quattroagents.domain import (
    AgentDefinition,
    AgentLifetime,
    AgentMode,
    Decision,
    DecisionScope,
    DecisionSource,
    DecisionSourceType,
    DecisionStatus,
    DefinitionSource,
)
from quattroagents.generation.task_synthesis import synthesize_task_agent
from quattroagents.interview.task_gaps import (
    TASK_COMPLETION_OUTCOME_TOPIC,
    TASK_SCOPE_BOUNDARY_TOPIC,
    TASK_WRITE_PERMISSION_TOPIC,
)


def _decision(title: str, answer: str, detail: str = "") -> Decision:
    return Decision(
        id=f"decision-{title}",
        title=title,
        value={"question": title, "answer": answer, "detail": detail, "classification": []},
        source=DecisionSource(type=DecisionSourceType.USER, interview_session="task-session-1"),
        reason=detail or answer,
        decision_scope=DecisionScope.PROJECT_WIDE,
        status=DecisionStatus.ACTIVE,
    )


def test_synthesize_task_agent_with_no_decisions_falls_back_to_goal() -> None:
    """With no confirmed decisions, scope/completion criteria fall back to the goal."""
    agent = synthesize_task_agent("task1", "Fix the flaky retry test", [], [])

    assert agent.id == "task-task1"
    assert agent.scope == "Fix the flaky retry test"
    assert agent.completion_criteria == ["requested behavior for this task is covered"]
    assert agent.lifetime == AgentLifetime.TASK_TEMPORARY
    assert agent.source == DefinitionSource.TASK_TEMPORARY


def test_synthesize_task_agent_uses_scope_and_outcome_decisions() -> None:
    """Confirmed scope/outcome decisions populate scope and completion_criteria."""
    decisions = [
        _decision(TASK_SCOPE_BOUNDARY_TOPIC, "in-scope", "Only cli.py's release subcommand."),
        _decision(
            TASK_COMPLETION_OUTCOME_TOPIC,
            "outcome",
            "Dry-run prints planned changes without writing anything.",
        ),
    ]

    agent = synthesize_task_agent("task1", "Add a --dry-run flag", decisions, [])

    assert agent.scope == "Only cli.py's release subcommand."
    assert agent.completion_criteria == ["Dry-run prints planned changes without writing anything."]
    assert "Stay within: Only cli.py's release subcommand." in agent.responsibilities


def test_synthesize_task_agent_write_permission_yes_sets_write_mode() -> None:
    """An affirmative write-permission answer sets WRITE mode and can_write_files."""
    decisions = [_decision(TASK_WRITE_PERMISSION_TOPIC, "yes", "Needs write access to cli.py.")]

    agent = synthesize_task_agent("task1", "Add a flag", decisions, [])

    assert agent.mode == AgentMode.WRITE
    assert agent.permissions.can_write_files is True
    assert agent.permissions.can_read_files is True


def test_synthesize_task_agent_write_permission_no_sets_read_only_mode() -> None:
    """A negative write-permission answer keeps READ_ONLY mode."""
    decisions = [_decision(TASK_WRITE_PERMISSION_TOPIC, "no", "Read-only, just analyze the logic.")]

    agent = synthesize_task_agent("task1", "Review the logic", decisions, [])

    assert agent.mode == AgentMode.READ_ONLY
    assert agent.permissions.can_write_files is False


def test_synthesize_task_agent_notes_reused_agents_in_responsibilities() -> None:
    """Reused agents are noted in responsibilities so the task agent defers to them."""
    reused = [AgentDefinition(id="implementation-agent-sonnet", description="Implements changes")]

    agent = synthesize_task_agent("task1", "Add a flag", [], reused)

    assert any("implementation-agent-sonnet" in r for r in agent.responsibilities)


def test_synthesize_task_agent_ignores_decisions_from_unrelated_topics() -> None:
    """Decisions whose title doesn't match a known task-gap topic are ignored."""
    decisions = [_decision("some unrelated decision", "value", "detail")]

    agent = synthesize_task_agent("task1", "Do the thing", decisions, [])

    assert agent.scope == "Do the thing"
    assert agent.completion_criteria == ["requested behavior for this task is covered"]

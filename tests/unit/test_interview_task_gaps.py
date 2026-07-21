"""Tests for task-scoped knowledge gap detection (interview/task_gaps.py)."""

from quattroagents.domain import GapStatus, GapType
from quattroagents.interview.task_gaps import (
    TASK_COMPLETION_OUTCOME_TOPIC,
    TASK_REUSE_TOPIC,
    TASK_SCOPE_BOUNDARY_TOPIC,
    TASK_WRITE_PERMISSION_TOPIC,
    detect_task_gaps,
)


def test_detect_task_gaps_always_includes_scope_outcome_permission() -> None:
    """The three core task gaps are always present, regardless of goal content."""
    gaps = detect_task_gaps("Fix the flaky retry test", [])
    gap_ids = {gap.id for gap in gaps}

    assert gap_ids == {"task-scope-boundary", "task-completion-outcome", "task-write-permission"}
    assert all(gap.status == GapStatus.OPEN for gap in gaps)


def test_detect_task_gaps_includes_goal_in_description() -> None:
    """Each gap's description references the given goal for context."""
    goal = "Add a --dry-run flag to the release command"
    gaps = detect_task_gaps(goal, [])

    for gap in gaps:
        assert goal in gap.description


def test_detect_task_gaps_with_base_agent_ids_adds_reuse_gap() -> None:
    """Passing base_agent_ids adds a reuse-check gap referencing them."""
    gaps = detect_task_gaps(
        "Refactor error handling", ["implementation-agent-sonnet", "test-agent-haiku"]
    )
    gap_ids = {gap.id for gap in gaps}

    assert "task-reuse-check" in gap_ids
    reuse_gap = next(g for g in gaps if g.id == "task-reuse-check")
    assert "implementation-agent-sonnet" in reuse_gap.description
    assert "test-agent-haiku" in reuse_gap.description
    assert reuse_gap.evidence == ["implementation-agent-sonnet", "test-agent-haiku"]


def test_detect_task_gaps_without_base_agent_ids_omits_reuse_gap() -> None:
    """No base_agent_ids means no reuse-check gap."""
    gaps = detect_task_gaps("Refactor error handling", [])
    gap_ids = {gap.id for gap in gaps}

    assert "task-reuse-check" not in gap_ids
    assert len(gaps) == 3


def test_task_gap_topics_are_stable_identifiers_used_by_synthesis() -> None:
    """The topic constants match each gap's actual topic field (contract with task_synthesis.py)."""
    gaps = detect_task_gaps("Some goal", ["agent-x"])
    topics_by_id = {gap.id: gap.topic for gap in gaps}

    assert topics_by_id["task-scope-boundary"] == TASK_SCOPE_BOUNDARY_TOPIC
    assert topics_by_id["task-completion-outcome"] == TASK_COMPLETION_OUTCOME_TOPIC
    assert topics_by_id["task-write-permission"] == TASK_WRITE_PERMISSION_TOPIC
    assert topics_by_id["task-reuse-check"] == TASK_REUSE_TOPIC


def test_detect_task_gaps_gap_types_are_valid() -> None:
    """Every task gap has a valid GapType so question_for_gap can render it."""
    gaps = detect_task_gaps("Some goal", ["agent-x"])

    for gap in gaps:
        assert isinstance(gap.gap_type, GapType)

"""Unit tests for swarm plan generation (build_swarm_plan, render_swarm_plan_text)."""

import pytest

from quattroagents.domain import (
    AgentDefinition,
    AgentMode,
    Decision,
    DecisionSource,
    DecisionSourceType,
    Model,
    SwarmDefinition,
)
from quattroagents.generation.swarm import build_swarm_plan, render_swarm_plan_text


def test_two_independent_agents_same_wave_can_run_parallel() -> None:
    """Two independent agents (no deps, non-overlapping file_ownership) should be in the same wave."""
    agent_a = AgentDefinition(id="agent-a", description="Does something")
    agent_b = AgentDefinition(id="agent-b", description="Does something else")

    plan = build_swarm_plan(
        task_id="test-task",
        goal="Test goal",
        agents=[agent_a, agent_b],
        phases={"agent-a": "phase1", "agent-b": "phase1"},
        depends_on={},
        file_ownership={},
        decisions=[],
    )

    # Should have exactly 1 wave with both agents
    assert len(plan.agents) == 2

    # Both agents should have the same parallel_group
    step_a = next(s for s in plan.agents if s.agent_id == "agent-a")
    step_b = next(s for s in plan.agents if s.agent_id == "agent-b")

    assert step_a.parallel_group is not None
    assert step_a.parallel_group == step_b.parallel_group

    # Each should list the other in can_run_parallel_with
    assert "agent-b" in step_a.can_run_parallel_with
    assert "agent-a" in step_b.can_run_parallel_with


def test_overlapping_file_ownership_different_waves() -> None:
    """Two agents with overlapping file_ownership paths should be in different waves."""
    agent_a = AgentDefinition(id="agent-a", description="Does something")
    agent_b = AgentDefinition(id="agent-b", description="Does something else")

    plan = build_swarm_plan(
        task_id="test-task",
        goal="Test goal",
        agents=[agent_a, agent_b],
        phases={"agent-a": "phase1", "agent-b": "phase1"},
        depends_on={},
        file_ownership={"agent-a": ["src/foo"], "agent-b": ["src/foo"]},
        decisions=[],
    )

    # Should have 2 agents
    assert len(plan.agents) == 2

    step_a = next(s for s in plan.agents if s.agent_id == "agent-a")
    step_b = next(s for s in plan.agents if s.agent_id == "agent-b")

    # They should have different parallel_groups or at least one should be None
    if step_a.parallel_group is not None and step_b.parallel_group is not None:
        assert step_a.parallel_group != step_b.parallel_group

    # Neither should list the other in can_run_parallel_with
    assert "agent-b" not in step_a.can_run_parallel_with
    assert "agent-a" not in step_b.can_run_parallel_with


def test_overlapping_file_ownership_directory_prefix() -> None:
    """File ownership overlap detection should work with directory prefixes."""
    agent_a = AgentDefinition(id="agent-a", description="Does something")
    agent_b = AgentDefinition(id="agent-b", description="Does something else")

    plan = build_swarm_plan(
        task_id="test-task",
        goal="Test goal",
        agents=[agent_a, agent_b],
        phases={"agent-a": "phase1", "agent-b": "phase1"},
        depends_on={},
        file_ownership={"agent-a": ["src/foo"], "agent-b": ["src/foo/bar"]},
        decisions=[],
    )

    # Should have 2 agents
    assert len(plan.agents) == 2

    step_a = next(s for s in plan.agents if s.agent_id == "agent-a")
    step_b = next(s for s in plan.agents if s.agent_id == "agent-b")

    # They should not be in the same wave
    if step_a.parallel_group is not None and step_b.parallel_group is not None:
        assert step_a.parallel_group != step_b.parallel_group

    # Neither should list the other in can_run_parallel_with
    assert "agent-b" not in step_a.can_run_parallel_with
    assert "agent-a" not in step_b.can_run_parallel_with


def test_explicit_dependency_puts_dependent_in_later_wave() -> None:
    """An explicit dependency (B depends on A) puts B in a later wave than A."""
    agent_a = AgentDefinition(id="agent-a", description="Does something")
    agent_b = AgentDefinition(id="agent-b", description="Does something else")

    plan = build_swarm_plan(
        task_id="test-task",
        goal="Test goal",
        agents=[agent_a, agent_b],
        phases={"agent-a": "phase1", "agent-b": "phase2"},
        depends_on={"agent-b": ["agent-a"]},
        file_ownership={},
        decisions=[],
    )

    # Should have exactly 2 agents
    assert len(plan.agents) == 2

    step_b = next(s for s in plan.agents if s.agent_id == "agent-b")

    # agent-b should depend on agent-a
    assert "agent-a" in step_b.depends_on

    # agent-b should not have agent-a in can_run_parallel_with
    assert "agent-a" not in step_b.can_run_parallel_with


def test_phases_reflected_in_swarm_agent_steps() -> None:
    """The phases mapping should be reflected in each SwarmAgentStep.phase."""
    agent_a = AgentDefinition(id="agent-a", description="Does something")
    agent_b = AgentDefinition(id="agent-b", description="Does something else")
    agent_c = AgentDefinition(id="agent-c", description="Does yet another thing")

    plan = build_swarm_plan(
        task_id="test-task",
        goal="Test goal",
        agents=[agent_a, agent_b, agent_c],
        phases={"agent-a": "discovery", "agent-b": "implementation", "agent-c": "testing"},
        depends_on={},
        file_ownership={},
        decisions=[],
    )

    # Check that phases are correctly assigned
    step_a = next(s for s in plan.agents if s.agent_id == "agent-a")
    step_b = next(s for s in plan.agents if s.agent_id == "agent-b")
    step_c = next(s for s in plan.agents if s.agent_id == "agent-c")

    assert step_a.phase == "discovery"
    assert step_b.phase == "implementation"
    assert step_c.phase == "testing"


def test_unknown_agent_in_phases_raises_value_error() -> None:
    """An agent_id in phases that isn't in agents should raise ValueError."""
    agent_a = AgentDefinition(id="agent-a", description="Does something")

    with pytest.raises(ValueError, match="unknown agent in swarm plan"):
        build_swarm_plan(
            task_id="test-task",
            goal="Test goal",
            agents=[agent_a],
            phases={"agent-a": "phase1", "unknown-agent": "phase2"},
            depends_on={},
            file_ownership={},
            decisions=[],
        )


def test_unknown_agent_in_depends_on_raises_value_error() -> None:
    """An agent_id in depends_on that isn't in agents should raise ValueError."""
    agent_a = AgentDefinition(id="agent-a", description="Does something")

    with pytest.raises(ValueError, match="unknown agent in swarm plan"):
        build_swarm_plan(
            task_id="test-task",
            goal="Test goal",
            agents=[agent_a],
            phases={},
            depends_on={"unknown-agent": ["agent-a"]},
            file_ownership={},
            decisions=[],
        )


def test_unknown_agent_in_file_ownership_raises_value_error() -> None:
    """An agent_id in file_ownership that isn't in agents should raise ValueError."""
    agent_a = AgentDefinition(id="agent-a", description="Does something")

    with pytest.raises(ValueError, match="unknown agent in swarm plan"):
        build_swarm_plan(
            task_id="test-task",
            goal="Test goal",
            agents=[agent_a],
            phases={},
            depends_on={},
            file_ownership={"unknown-agent": ["src/foo"]},
            decisions=[],
        )


def test_unknown_dependency_target_raises_value_error() -> None:
    """A dependency target not in agents should raise ValueError."""
    agent_a = AgentDefinition(id="agent-a", description="Does something")

    try:
        build_swarm_plan(
            task_id="test-task",
            goal="Test goal",
            agents=[agent_a],
            phases={},
            depends_on={"agent-a": ["unknown-target"]},
            file_ownership={},
            decisions=[],
        )
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        assert "unknown swarm dependency" in str(e)


def test_agent_depending_on_itself_raises_value_error() -> None:
    """An agent depending on itself should raise ValueError."""
    agent_a = AgentDefinition(id="agent-a", description="Does something")

    try:
        build_swarm_plan(
            task_id="test-task",
            goal="Test goal",
            agents=[agent_a],
            phases={},
            depends_on={"agent-a": ["agent-a"]},
            file_ownership={},
            decisions=[],
        )
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        assert "cannot depend on itself" in str(e)


def test_circular_dependency_raises_value_error() -> None:
    """A circular dependency (A depends on B, B depends on A) should raise ValueError."""
    agent_a = AgentDefinition(id="agent-a", description="Does something")
    agent_b = AgentDefinition(id="agent-b", description="Does something else")

    try:
        build_swarm_plan(
            task_id="test-task",
            goal="Test goal",
            agents=[agent_a, agent_b],
            phases={},
            depends_on={"agent-a": ["agent-b"], "agent-b": ["agent-a"]},
            file_ownership={},
            decisions=[],
        )
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        assert "cycle" in str(e).lower()


def test_required_review_agents_from_read_only_mode() -> None:
    """required_review_agents should include all agents with mode=READ_ONLY."""
    agent_a = AgentDefinition(id="agent-a", description="Does something", mode=AgentMode.READ_ONLY)
    agent_b = AgentDefinition(id="agent-b", description="Does something else", mode=AgentMode.WRITE)
    agent_c = AgentDefinition(
        id="agent-c", description="Does yet another thing", mode=AgentMode.READ_ONLY
    )

    plan = build_swarm_plan(
        task_id="test-task",
        goal="Test goal",
        agents=[agent_a, agent_b, agent_c],
        phases={},
        depends_on={},
        file_ownership={},
        decisions=[],
    )

    assert sorted(plan.required_review_agents) == ["agent-a", "agent-c"]


def test_required_review_agents_from_decision_mandatory_review() -> None:
    """Decisions with mandatory_review flag should add agents to required_review_agents."""
    agent_a = AgentDefinition(id="agent-a", description="Does something", mode=AgentMode.WRITE)
    agent_b = AgentDefinition(id="agent-b", description="Does something else", mode=AgentMode.WRITE)
    agent_c = AgentDefinition(
        id="agent-c", description="Does yet another thing", mode=AgentMode.READ_ONLY
    )

    decision = Decision(
        id="dec-1",
        title="Test decision",
        value={"mandatory_review": True},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Testing",
        effects={"agents": ["agent-a", "agent-b"]},
    )

    plan = build_swarm_plan(
        task_id="test-task",
        goal="Test goal",
        agents=[agent_a, agent_b, agent_c],
        phases={},
        depends_on={},
        file_ownership={},
        decisions=[decision],
    )

    # Should include agent-c (READ_ONLY) and agent-a, agent-b (from decision)
    assert sorted(plan.required_review_agents) == ["agent-a", "agent-b", "agent-c"]


def test_required_review_agents_deduped() -> None:
    """required_review_agents should be deduped."""
    agent_a = AgentDefinition(id="agent-a", description="Does something", mode=AgentMode.READ_ONLY)

    decision = Decision(
        id="dec-1",
        title="Test decision",
        value={"mandatory_review": True},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Testing",
        effects={"agents": ["agent-a"]},
    )

    plan = build_swarm_plan(
        task_id="test-task",
        goal="Test goal",
        agents=[agent_a],
        phases={},
        depends_on={},
        file_ownership={},
        decisions=[decision],
    )

    # Should only have agent-a once
    assert plan.required_review_agents == ["agent-a"]


def test_completion_criteria_default_entries() -> None:
    """completion_criteria should start with 3 default entries."""
    agent_a = AgentDefinition(id="agent-a", description="Does something")

    plan = build_swarm_plan(
        task_id="test-task",
        goal="Test goal",
        agents=[agent_a],
        phases={},
        depends_on={},
        file_ownership={},
        decisions=[],
    )

    # Check that the 3 default entries are present in order
    expected_defaults = [
        "build passes",
        "tests pass",
        "requested behavior is covered",
    ]

    for i, expected in enumerate(expected_defaults):
        assert plan.completion_criteria[i] == expected


def test_completion_criteria_extended_by_decisions() -> None:
    """completion_criteria should be extended by decision values."""
    agent_a = AgentDefinition(id="agent-a", description="Does something")

    decision1 = Decision(
        id="dec-1",
        title="Test decision 1",
        value={"completion_criteria": ["custom criteria 1", "custom criteria 2"]},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Testing",
    )

    decision2 = Decision(
        id="dec-2",
        title="Test decision 2",
        value={"completion_criteria": ["custom criteria 3"]},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Testing",
    )

    plan = build_swarm_plan(
        task_id="test-task",
        goal="Test goal",
        agents=[agent_a],
        phases={},
        depends_on={},
        file_ownership={},
        decisions=[decision1, decision2],
    )

    # Should have defaults + custom criteria
    expected = [
        "build passes",
        "tests pass",
        "requested behavior is covered",
        "custom criteria 1",
        "custom criteria 2",
        "custom criteria 3",
    ]

    assert plan.completion_criteria == expected


def test_completion_criteria_deduped_preserves_order() -> None:
    """completion_criteria should be deduped while preserving order."""
    agent_a = AgentDefinition(id="agent-a", description="Does something")

    decision1 = Decision(
        id="dec-1",
        title="Test decision 1",
        value={"completion_criteria": ["build passes", "custom criteria 1"]},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Testing",
    )

    plan = build_swarm_plan(
        task_id="test-task",
        goal="Test goal",
        agents=[agent_a],
        phases={},
        depends_on={},
        file_ownership={},
        decisions=[decision1],
    )

    # Should not duplicate "build passes"
    expected = [
        "build passes",
        "tests pass",
        "requested behavior is covered",
        "custom criteria 1",
    ]

    assert plan.completion_criteria == expected


def test_render_swarm_plan_text_groups_by_phase() -> None:
    """render_swarm_plan_text should group agents by phase in first-seen order."""
    agent_a = AgentDefinition(
        id="agent-a", description="Analyzes the repository", preferred_model=Model.HAIKU
    )
    agent_b = AgentDefinition(
        id="agent-b", description="Implements changes", preferred_model=Model.SONNET
    )
    agent_c = AgentDefinition(
        id="agent-c", description="Reviews implementation", preferred_model=Model.OPUS
    )

    plan = build_swarm_plan(
        task_id="test-task",
        goal="Test goal",
        agents=[agent_a, agent_b, agent_c],
        phases={"agent-a": "discovery", "agent-b": "implementation", "agent-c": "discovery"},
        depends_on={},
        file_ownership={},
        decisions=[],
    )

    agents_by_id = {"agent-a": agent_a, "agent-b": agent_b, "agent-c": agent_c}
    text = render_swarm_plan_text(plan, agents_by_id)

    # discovery should come first (first-seen order)
    lines = text.split("\n")

    # Should have phase headers
    assert any("discovery:" in line for line in lines)
    assert any("implementation:" in line for line in lines)

    # discovery should appear before implementation in the output
    discovery_idx = next(i for i, line in enumerate(lines) if "discovery:" in line)
    implementation_idx = next(i for i, line in enumerate(lines) if "implementation:" in line)
    assert discovery_idx < implementation_idx


def test_render_swarm_plan_text_uses_render_agent_display() -> None:
    """render_swarm_plan_text should use render_agent_display for each agent line."""
    agent_a = AgentDefinition(
        id="agent-a", description="Analyzes the repository", preferred_model=Model.HAIKU
    )

    plan = build_swarm_plan(
        task_id="test-task",
        goal="Test goal",
        agents=[agent_a],
        phases={"agent-a": "discovery"},
        depends_on={},
        file_ownership={},
        decisions=[],
    )

    agents_by_id = {"agent-a": agent_a}
    text = render_swarm_plan_text(plan, agents_by_id)

    # Should contain the rendered agent line
    # Format is: <agent-name> [<model>] <description>
    expected_line = "agent-a [haiku] Analyzes the repository"
    assert expected_line in text


def test_render_swarm_plan_text_review_required_line() -> None:
    """render_swarm_plan_text should include 'Review required: ...' line when needed."""
    agent_a = AgentDefinition(
        id="agent-a", description="Analyzes the repository", mode=AgentMode.READ_ONLY
    )
    agent_b = AgentDefinition(id="agent-b", description="Implements changes", mode=AgentMode.WRITE)

    plan = build_swarm_plan(
        task_id="test-task",
        goal="Test goal",
        agents=[agent_a, agent_b],
        phases={"agent-a": "review", "agent-b": "implementation"},
        depends_on={},
        file_ownership={},
        decisions=[],
    )

    agents_by_id = {"agent-a": agent_a, "agent-b": agent_b}
    text = render_swarm_plan_text(plan, agents_by_id)

    # Should have "Review required:" line
    assert "Review required: agent-a" in text


def test_render_swarm_plan_text_no_review_required_line_when_empty() -> None:
    """render_swarm_plan_text should NOT include 'Review required: ...' line when required_review_agents is empty."""
    agent_a = AgentDefinition(id="agent-a", description="Implements changes", mode=AgentMode.WRITE)

    plan = build_swarm_plan(
        task_id="test-task",
        goal="Test goal",
        agents=[agent_a],
        phases={"agent-a": "implementation"},
        depends_on={},
        file_ownership={},
        decisions=[],
    )

    agents_by_id = {"agent-a": agent_a}
    text = render_swarm_plan_text(plan, agents_by_id)

    # Should NOT have "Review required:" line
    assert "Review required:" not in text


def test_render_swarm_plan_text_completion_criteria_line() -> None:
    """render_swarm_plan_text should include 'Completion criteria: ...' line with '; ' separator."""
    agent_a = AgentDefinition(id="agent-a", description="Does something")

    decision = Decision(
        id="dec-1",
        title="Test decision",
        value={"completion_criteria": ["custom criteria 1"]},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Testing",
    )

    plan = build_swarm_plan(
        task_id="test-task",
        goal="Test goal",
        agents=[agent_a],
        phases={"agent-a": "phase1"},
        depends_on={},
        file_ownership={},
        decisions=[decision],
    )

    agents_by_id = {"agent-a": agent_a}
    text = render_swarm_plan_text(plan, agents_by_id)

    # Should have "Completion criteria:" line with criteria separated by "; "
    lines = text.split("\n")
    criteria_line = next(line for line in lines if "Completion criteria:" in line)

    assert (
        "build passes; tests pass; requested behavior is covered; custom criteria 1"
        in criteria_line
    )


def test_render_swarm_plan_text_empty_completion_criteria_still_appears() -> None:
    """render_swarm_plan_text should include 'Completion criteria: ...' even with just defaults."""
    agent_a = AgentDefinition(id="agent-a", description="Does something")

    plan = build_swarm_plan(
        task_id="test-task",
        goal="Test goal",
        agents=[agent_a],
        phases={"agent-a": "phase1"},
        depends_on={},
        file_ownership={},
        decisions=[],
    )

    agents_by_id = {"agent-a": agent_a}
    text = render_swarm_plan_text(plan, agents_by_id)

    # Should have "Completion criteria:" line
    assert "Completion criteria: build passes; tests pass; requested behavior is covered" in text


def test_render_swarm_plan_text_multiple_reviewers() -> None:
    """render_swarm_plan_text should list multiple review agents separated by ', '."""
    agent_a = AgentDefinition(id="agent-a", description="Analyzes", mode=AgentMode.READ_ONLY)
    agent_b = AgentDefinition(id="agent-b", description="Implements", mode=AgentMode.READ_ONLY)
    agent_c = AgentDefinition(id="agent-c", description="Does something", mode=AgentMode.WRITE)

    plan = build_swarm_plan(
        task_id="test-task",
        goal="Test goal",
        agents=[agent_a, agent_b, agent_c],
        phases={"agent-a": "review", "agent-b": "review", "agent-c": "implementation"},
        depends_on={},
        file_ownership={},
        decisions=[],
    )

    agents_by_id = {"agent-a": agent_a, "agent-b": agent_b, "agent-c": agent_c}
    text = render_swarm_plan_text(plan, agents_by_id)

    # Should have review agents listed with comma separation
    assert "Review required: agent-a, agent-b" in text


def test_build_swarm_plan_returns_swarm_definition() -> None:
    """build_swarm_plan should return a SwarmDefinition object."""
    agent_a = AgentDefinition(id="agent-a", description="Does something")

    result = build_swarm_plan(
        task_id="test-task",
        goal="Test goal",
        agents=[agent_a],
        phases={},
        depends_on={},
        file_ownership={},
        decisions=[],
    )

    assert isinstance(result, SwarmDefinition)
    assert result.task_id == "test-task"
    assert result.goal == "Test goal"
    assert len(result.agents) == 1


def test_complex_multi_wave_scheduling() -> None:
    """Test a complex scenario with multiple waves and dependencies."""
    agent_a = AgentDefinition(id="agent-a", description="Phase 1", mode=AgentMode.READ_ONLY)
    agent_b = AgentDefinition(id="agent-b", description="Phase 2")
    agent_c = AgentDefinition(id="agent-c", description="Phase 2")
    agent_d = AgentDefinition(id="agent-d", description="Phase 3")

    plan = build_swarm_plan(
        task_id="test-task",
        goal="Test goal",
        agents=[agent_a, agent_b, agent_c, agent_d],
        phases={
            "agent-a": "phase1",
            "agent-b": "phase2",
            "agent-c": "phase2",
            "agent-d": "phase3",
        },
        depends_on={
            "agent-b": ["agent-a"],
            "agent-c": ["agent-a"],
            "agent-d": ["agent-b", "agent-c"],
        },
        file_ownership={},
        decisions=[],
    )

    # Verify wave structure
    assert len(plan.agents) == 4

    step_b = next(s for s in plan.agents if s.agent_id == "agent-b")
    step_c = next(s for s in plan.agents if s.agent_id == "agent-c")
    step_d = next(s for s in plan.agents if s.agent_id == "agent-d")

    # agent-b and agent-c should depend on agent-a
    assert "agent-a" in step_b.depends_on
    assert "agent-a" in step_c.depends_on

    # agent-d should depend on both agent-b and agent-c
    assert "agent-b" in step_d.depends_on
    assert "agent-c" in step_d.depends_on

    # agent-b and agent-c should be able to run parallel (no file conflicts)
    assert "agent-c" in step_b.can_run_parallel_with or "agent-b" in step_c.can_run_parallel_with

    # agent-a should be a mandatory reviewer (READ_ONLY)
    assert "agent-a" in plan.required_review_agents


def test_wildcard_file_ownership() -> None:
    """File ownership with "*" should conflict with all other agents."""
    agent_a = AgentDefinition(id="agent-a", description="Does something")
    agent_b = AgentDefinition(id="agent-b", description="Does something else")

    plan = build_swarm_plan(
        task_id="test-task",
        goal="Test goal",
        agents=[agent_a, agent_b],
        phases={"agent-a": "phase1", "agent-b": "phase1"},
        depends_on={},
        file_ownership={"agent-a": ["*"], "agent-b": ["src/foo"]},
        decisions=[],
    )

    # Should have 2 agents in different parallel groups
    step_a = next(s for s in plan.agents if s.agent_id == "agent-a")
    step_b = next(s for s in plan.agents if s.agent_id == "agent-b")

    # They should not be in the same wave
    if step_a.parallel_group is not None and step_b.parallel_group is not None:
        assert step_a.parallel_group != step_b.parallel_group


def test_file_ownership_trailing_slash() -> None:
    """File ownership matching should handle trailing slashes."""
    agent_a = AgentDefinition(id="agent-a", description="Does something")
    agent_b = AgentDefinition(id="agent-b", description="Does something else")

    plan = build_swarm_plan(
        task_id="test-task",
        goal="Test goal",
        agents=[agent_a, agent_b],
        phases={"agent-a": "phase1", "agent-b": "phase1"},
        depends_on={},
        file_ownership={"agent-a": ["src/foo/"], "agent-b": ["src/foo"]},
        decisions=[],
    )

    # Should recognize overlap even with trailing slash
    step_a = next(s for s in plan.agents if s.agent_id == "agent-a")
    step_b = next(s for s in plan.agents if s.agent_id == "agent-b")

    # They should not be in the same wave
    if step_a.parallel_group is not None and step_b.parallel_group is not None:
        assert step_a.parallel_group != step_b.parallel_group


def test_decision_without_mandatory_review_ignored() -> None:
    """Decisions without mandatory_review flag should not add to required_review_agents."""
    agent_a = AgentDefinition(id="agent-a", description="Does something", mode=AgentMode.WRITE)

    decision = Decision(
        id="dec-1",
        title="Test decision",
        value={},  # No mandatory_review flag
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Testing",
        effects={"agents": ["agent-a"]},
    )

    plan = build_swarm_plan(
        task_id="test-task",
        goal="Test goal",
        agents=[agent_a],
        phases={},
        depends_on={},
        file_ownership={},
        decisions=[decision],
    )

    # Should not include agent-a in required_review_agents
    assert "agent-a" not in plan.required_review_agents


def test_decision_with_no_agents_effects_ignored() -> None:
    """Decisions without 'agents' effects should not add to required_review_agents."""
    agent_a = AgentDefinition(id="agent-a", description="Does something", mode=AgentMode.WRITE)

    decision = Decision(
        id="dec-1",
        title="Test decision",
        value={"mandatory_review": True},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Testing",
        effects={},  # No 'agents' key
    )

    plan = build_swarm_plan(
        task_id="test-task",
        goal="Test goal",
        agents=[agent_a],
        phases={},
        depends_on={},
        file_ownership={},
        decisions=[decision],
    )

    # Should not include agent-a in required_review_agents
    assert "agent-a" not in plan.required_review_agents


def test_decision_completion_criteria_not_list_ignored() -> None:
    """Decisions with non-list completion_criteria values should be ignored."""
    agent_a = AgentDefinition(id="agent-a", description="Does something")

    decision = Decision(
        id="dec-1",
        title="Test decision",
        value={"completion_criteria": "not a list"},  # Invalid: not a list
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Testing",
    )

    plan = build_swarm_plan(
        task_id="test-task",
        goal="Test goal",
        agents=[agent_a],
        phases={},
        depends_on={},
        file_ownership={},
        decisions=[decision],
    )

    # Should only have default criteria
    expected = [
        "build passes",
        "tests pass",
        "requested behavior is covered",
    ]

    assert plan.completion_criteria == expected

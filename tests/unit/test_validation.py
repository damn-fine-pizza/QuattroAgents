"""Tests for configuration validation module."""

import json

import pytest

from quattroagents.domain import (
    AgentDefinition,
    AgentMode,
    Model,
    SkillDefinition,
    SwarmAgentStep,
    SwarmDefinition,
)
from quattroagents.validation import (
    ConfigValidationResult,
    ConfigViolation,
    render_validation_report,
    validate_generated_configuration,
)


def test_validate_fully_valid_configuration() -> None:
    """A fully valid configuration returns valid=True with no violations."""
    agents = [
        AgentDefinition(
            id="agent-1",
            description="Test agent one",
            completion_criteria=["Task complete"],
        ),
        AgentDefinition(
            id="agent-2",
            description="Another agent",
            completion_criteria=["Work done"],
        ),
    ]
    skills = [
        SkillDefinition(
            id="skill-1",
            trigger="when needed",
            usable_by_agents=["agent-1"],
        ),
    ]

    result = validate_generated_configuration(agents, skills)

    assert result.valid is True
    assert result.violations == []


def test_validate_duplicate_agent_ids() -> None:
    """Duplicate agent ids trigger duplicate_agent_id violation."""
    agents = [
        AgentDefinition(
            id="agent-1",
            description="First test agent",
            completion_criteria=["Done"],
        ),
        AgentDefinition(
            id="agent-1",
            description="Duplicate agent",
            completion_criteria=["Also done"],
        ),
    ]

    result = validate_generated_configuration(agents, [])

    assert result.valid is False
    assert len(result.violations) == 1
    assert result.violations[0].code == "duplicate_agent_id"
    assert "agent-1" in result.violations[0].message


def test_validate_duplicate_skill_ids() -> None:
    """Duplicate skill ids trigger duplicate_skill_id violation."""
    agents = [
        AgentDefinition(
            id="agent-1",
            description="Test agent description",
            completion_criteria=["Done"],
        ),
    ]
    skills = [
        SkillDefinition(id="skill-1", trigger="trigger1", usable_by_agents=["agent-1"]),
        SkillDefinition(id="skill-1", trigger="trigger2", usable_by_agents=["agent-1"]),
    ]

    result = validate_generated_configuration(agents, skills)

    assert result.valid is False
    assert len(result.violations) == 1
    assert result.violations[0].code == "duplicate_skill_id"
    assert "skill-1" in result.violations[0].message


def test_validate_agent_missing_completion_criteria() -> None:
    """An agent with empty completion_criteria triggers violation."""
    agents = [
        AgentDefinition(
            id="agent-1",
            description="Agent without completion criteria",
            completion_criteria=[],
        ),
    ]

    result = validate_generated_configuration(agents, [])

    assert result.valid is False
    assert len(result.violations) == 1
    assert result.violations[0].code == "agent_missing_completion_criteria"
    assert "agent-1" in result.violations[0].message


def test_validate_skill_missing_trigger_and_workflow() -> None:
    """A skill with no trigger, no workflow, and no body triggers violation."""
    agents = [
        AgentDefinition(
            id="agent-1",
            description="Test agent description",
            completion_criteria=["Done"],
        ),
    ]
    skills = [
        SkillDefinition(
            id="skill-1",
            trigger="",
            workflow=[],
            body=None,
            usable_by_agents=["agent-1"],
        ),
    ]

    result = validate_generated_configuration(agents, skills)

    assert result.valid is False
    assert len(result.violations) == 1
    assert result.violations[0].code == "skill_missing_trigger_or_workflow"
    assert "skill-1" in result.violations[0].message


def test_validate_skill_with_trigger_is_valid() -> None:
    """A skill with a trigger does not trigger violation."""
    agents = [
        AgentDefinition(
            id="agent-1",
            description="Test agent description",
            completion_criteria=["Done"],
        ),
    ]
    skills = [
        SkillDefinition(
            id="skill-1",
            trigger="  valid trigger  ",
            workflow=[],
            body=None,
            usable_by_agents=["agent-1"],
        ),
    ]

    result = validate_generated_configuration(agents, skills)

    assert result.valid is True
    assert result.violations == []


def test_validate_skill_with_workflow_is_valid() -> None:
    """A skill with a workflow does not trigger violation."""
    agents = [
        AgentDefinition(
            id="agent-1",
            description="Test agent description",
            completion_criteria=["Done"],
        ),
    ]
    skills = [
        SkillDefinition(
            id="skill-1",
            trigger="",
            workflow=["step1"],
            body=None,
            usable_by_agents=["agent-1"],
        ),
    ]

    result = validate_generated_configuration(agents, skills)

    assert result.valid is True
    assert result.violations == []


def test_validate_skill_with_body_is_valid() -> None:
    """A skill with a body does not trigger violation."""
    agents = [
        AgentDefinition(
            id="agent-1",
            description="Test agent description",
            completion_criteria=["Done"],
        ),
    ]
    skills = [
        SkillDefinition(
            id="skill-1",
            trigger="",
            workflow=[],
            body="some body content",
            usable_by_agents=["agent-1"],
        ),
    ]

    result = validate_generated_configuration(agents, skills)

    assert result.valid is True
    assert result.violations == []


def test_validate_write_agent_without_limits() -> None:
    """A write-mode agent without relevant_paths or constraints triggers violation."""
    agents = [
        AgentDefinition(
            id="write-agent",
            description="Write-mode agent",
            completion_criteria=["Done"],
            mode=AgentMode.WRITE,
            relevant_paths=[],
            constraints=[],
        ),
    ]

    result = validate_generated_configuration(agents, [])

    assert result.valid is False
    assert len(result.violations) == 1
    assert result.violations[0].code == "write_agent_without_limits"
    assert "write-agent" in result.violations[0].message


def test_validate_write_agent_with_relevant_paths_is_valid() -> None:
    """A write-mode agent with relevant_paths does NOT trigger violation."""
    agents = [
        AgentDefinition(
            id="write-agent",
            description="Write-mode agent",
            completion_criteria=["Done"],
            mode=AgentMode.WRITE,
            relevant_paths=["/path/to/write"],
            constraints=[],
        ),
    ]

    result = validate_generated_configuration(agents, [])

    assert result.valid is True
    assert result.violations == []


def test_validate_write_agent_with_constraints_is_valid() -> None:
    """A write-mode agent with constraints does NOT trigger violation."""
    agents = [
        AgentDefinition(
            id="write-agent",
            description="Write-mode agent",
            completion_criteria=["Done"],
            mode=AgentMode.WRITE,
            relevant_paths=[],
            constraints=["Don't delete files"],
        ),
    ]

    result = validate_generated_configuration(agents, [])

    assert result.valid is True
    assert result.violations == []


def test_validate_read_only_agent_without_limits_is_valid() -> None:
    """A read-only agent without limits does NOT trigger violation."""
    agents = [
        AgentDefinition(
            id="read-agent",
            description="Read-only agent",
            completion_criteria=["Done"],
            mode=AgentMode.READ_ONLY,
            relevant_paths=[],
            constraints=[],
        ),
    ]

    result = validate_generated_configuration(agents, [])

    assert result.valid is True
    assert result.violations == []


def test_validate_skill_references_unknown_agent() -> None:
    """A skill referencing an unknown agent triggers violation."""
    agents = [
        AgentDefinition(
            id="agent-1",
            description="Agent under test",
            completion_criteria=["Done"],
        ),
    ]
    skills = [
        SkillDefinition(
            id="skill-1",
            trigger="trigger",
            usable_by_agents=["unknown-agent"],
        ),
    ]

    result = validate_generated_configuration(agents, skills)

    assert result.valid is False
    assert len(result.violations) == 1
    assert result.violations[0].code == "skill_references_unknown_agent"
    assert "skill-1" in result.violations[0].message
    assert "unknown-agent" in result.violations[0].message


def test_validate_skill_with_multiple_agents_mixed() -> None:
    """A skill referencing both known and unknown agents triggers violation."""
    agents = [
        AgentDefinition(
            id="agent-1",
            description="Agent under test",
            completion_criteria=["Done"],
        ),
    ]
    skills = [
        SkillDefinition(
            id="skill-1",
            trigger="trigger",
            usable_by_agents=["agent-1", "unknown-agent"],
        ),
    ]

    result = validate_generated_configuration(agents, skills)

    assert result.valid is False
    assert len(result.violations) == 1
    assert result.violations[0].code == "skill_references_unknown_agent"


def test_validate_swarm_step_references_unknown_agent() -> None:
    """A swarm step referencing an unknown agent triggers violation."""
    agents = [
        AgentDefinition(
            id="agent-1",
            description="Agent under test",
            completion_criteria=["Done"],
        ),
    ]
    swarm = SwarmDefinition(
        task_id="task-1",
        goal="Do something",
        agents=[
            SwarmAgentStep(agent_id="unknown-agent", phase="phase-1"),
        ],
    )

    result = validate_generated_configuration(agents, [], swarm=swarm)

    assert result.valid is False
    assert len(result.violations) == 1
    assert result.violations[0].code == "swarm_references_unknown_agent"
    assert "unknown-agent" in result.violations[0].message


def test_validate_swarm_required_review_agents_unknown() -> None:
    """A swarm with unknown agent in required_review_agents triggers violation."""
    agents = [
        AgentDefinition(
            id="agent-1",
            description="Agent under test",
            completion_criteria=["Done"],
        ),
    ]
    swarm = SwarmDefinition(
        task_id="task-1",
        goal="Do something",
        agents=[],
        required_review_agents=["unknown-reviewer"],
    )

    result = validate_generated_configuration(agents, [], swarm=swarm)

    assert result.valid is False
    assert len(result.violations) == 1
    assert result.violations[0].code == "swarm_references_unknown_agent"
    assert "unknown-reviewer" in result.violations[0].message


def test_validate_swarm_dependency_cycle() -> None:
    """A swarm with a circular dependency in agent steps triggers violation."""
    agents = [
        AgentDefinition(
            id="agent-a",
            description="Agent A description",
            completion_criteria=["Done"],
        ),
        AgentDefinition(
            id="agent-b",
            description="Agent B description",
            completion_criteria=["Done"],
        ),
    ]
    # Create a cycle: A depends on B, B depends on A
    swarm = SwarmDefinition(
        task_id="task-1",
        goal="Do something",
        agents=[
            SwarmAgentStep(agent_id="agent-a", phase="phase-1", depends_on=["agent-b"]),
            SwarmAgentStep(agent_id="agent-b", phase="phase-1", depends_on=["agent-a"]),
        ],
    )

    result = validate_generated_configuration(agents, [], swarm=swarm)

    assert result.valid is False
    assert len(result.violations) == 1
    assert result.violations[0].code == "swarm_dependency_cycle"


def test_validate_swarm_three_way_dependency_cycle() -> None:
    """A swarm with a three-way circular dependency triggers violation."""
    agents = [
        AgentDefinition(
            id="agent-a", description="Agent A description", completion_criteria=["Done"]
        ),
        AgentDefinition(
            id="agent-b", description="Agent B description", completion_criteria=["Done"]
        ),
        AgentDefinition(
            id="agent-c", description="Agent C description", completion_criteria=["Done"]
        ),
    ]
    # Create cycle: A -> B -> C -> A
    swarm = SwarmDefinition(
        task_id="task-1",
        goal="Do something",
        agents=[
            SwarmAgentStep(agent_id="agent-a", phase="p1", depends_on=["agent-c"]),
            SwarmAgentStep(agent_id="agent-b", phase="p1", depends_on=["agent-a"]),
            SwarmAgentStep(agent_id="agent-c", phase="p1", depends_on=["agent-b"]),
        ],
    )

    result = validate_generated_configuration(agents, [], swarm=swarm)

    assert result.valid is False
    assert len(result.violations) == 1
    assert result.violations[0].code == "swarm_dependency_cycle"


def test_validate_swarm_valid_dependencies() -> None:
    """A swarm with valid (non-cyclic) dependencies is accepted."""
    agents = [
        AgentDefinition(
            id="agent-a", description="Agent A description", completion_criteria=["Done"]
        ),
        AgentDefinition(
            id="agent-b", description="Agent B description", completion_criteria=["Done"]
        ),
        AgentDefinition(
            id="agent-c", description="Agent C description", completion_criteria=["Done"]
        ),
    ]
    # Valid dependencies: A -> B -> C (acyclic)
    swarm = SwarmDefinition(
        task_id="task-1",
        goal="Do something",
        agents=[
            SwarmAgentStep(agent_id="agent-a", phase="p1", depends_on=[]),
            SwarmAgentStep(agent_id="agent-b", phase="p1", depends_on=["agent-a"]),
            SwarmAgentStep(agent_id="agent-c", phase="p1", depends_on=["agent-b"]),
        ],
    )

    result = validate_generated_configuration(agents, [], swarm=swarm)

    assert result.valid is True
    assert result.violations == []


def test_validate_agent_requires_unavailable_tool() -> None:
    """An agent with mandatory_tools not in available_tool_ids triggers violation."""
    agents = [
        AgentDefinition(
            id="agent-1",
            description="Agent under test",
            completion_criteria=["Done"],
            mandatory_tools=["tool-x"],
        ),
    ]
    available_tool_ids = {"tool-a", "tool-b"}

    result = validate_generated_configuration(agents, [], available_tool_ids=available_tool_ids)

    assert result.valid is False
    assert len(result.violations) == 1
    assert result.violations[0].code == "agent_requires_unavailable_tool"
    assert "agent-1" in result.violations[0].message
    assert "tool-x" in result.violations[0].message


def test_validate_agent_with_available_tools_is_valid() -> None:
    """An agent with mandatory_tools in available_tool_ids is valid."""
    agents = [
        AgentDefinition(
            id="agent-1",
            description="Agent under test",
            completion_criteria=["Done"],
            mandatory_tools=["tool-a", "tool-b"],
        ),
    ]
    available_tool_ids = {"tool-a", "tool-b", "tool-c"}

    result = validate_generated_configuration(agents, [], available_tool_ids=available_tool_ids)

    assert result.valid is True
    assert result.violations == []


def test_validate_no_tool_check_when_available_tool_ids_is_none() -> None:
    """When available_tool_ids is None, no tool availability check happens."""
    agents = [
        AgentDefinition(
            id="agent-1",
            description="Agent under test",
            completion_criteria=["Done"],
            mandatory_tools=["tool-x"],
        ),
    ]

    result = validate_generated_configuration(agents, [], available_tool_ids=None)

    assert result.valid is True
    assert result.violations == []


def test_validate_agent_handoff_direct_cycle() -> None:
    """Two agents whose expected_inputs/expected_outputs form a direct cycle trigger a violation."""
    agents = [
        AgentDefinition(
            id="agent-a",
            description="Agent A",
            completion_criteria=["Done"],
            expected_inputs=["artifact-b: produced by agent b"],
            expected_outputs=["artifact-a: produced by agent a"],
        ),
        AgentDefinition(
            id="agent-b",
            description="Agent B",
            completion_criteria=["Done"],
            expected_inputs=["artifact-a: produced by agent a"],
            expected_outputs=["artifact-b: produced by agent b"],
        ),
    ]

    result = validate_generated_configuration(agents, [])

    assert result.valid is False
    violation = next(v for v in result.violations if v.code == "agent_handoff_cycle")
    assert "agent-a" in violation.message
    assert "agent-b" in violation.message


def test_validate_agent_handoff_acyclic_chain_is_valid() -> None:
    """A linear producer/consumer chain across agents is accepted."""
    agents = [
        AgentDefinition(
            id="agent-a",
            description="Agent A",
            completion_criteria=["Done"],
            expected_outputs=["repo-map.json: directory tree summary"],
        ),
        AgentDefinition(
            id="agent-b",
            description="Agent B",
            completion_criteria=["Done"],
            expected_inputs=["repo-map.json: directory tree summary"],
            expected_outputs=["test-report.json: pass/fail counts"],
        ),
        AgentDefinition(
            id="agent-c",
            description="Agent C",
            completion_criteria=["Done"],
            expected_inputs=["test-report.json: pass/fail counts"],
        ),
    ]

    result = validate_generated_configuration(agents, [])

    assert result.valid is True
    assert result.violations == []


def test_validate_agent_handoff_no_producer_for_input_is_valid() -> None:
    """An agent declaring an input that no other agent produces is not a cycle violation."""
    agents = [
        AgentDefinition(
            id="agent-a",
            description="Agent A",
            completion_criteria=["Done"],
            expected_inputs=["external-file.json: not produced by any agent"],
        ),
    ]

    result = validate_generated_configuration(agents, [])

    assert result.valid is True
    assert result.violations == []


def test_validate_agent_id_already_prefixed_is_a_violation() -> None:
    """An agent id that already carries the qag- render prefix triggers a violation."""
    agents = [
        AgentDefinition(
            id="qag-agent-1",
            description="Agent whose id was mistakenly pre-prefixed",
            completion_criteria=["Done"],
        ),
    ]

    result = validate_generated_configuration(agents, [])

    assert result.valid is False
    codes = [v.code for v in result.violations]
    assert "agent_id_already_prefixed" in codes
    violation = next(v for v in result.violations if v.code == "agent_id_already_prefixed")
    assert "qag-agent-1" in violation.message


def test_validate_agent_id_unprefixed_is_valid() -> None:
    """A normal, unprefixed agent id does not trigger the prefix check."""
    agents = [
        AgentDefinition(
            id="agent-1",
            description="Normal agent",
            completion_criteria=["Done"],
        ),
    ]

    result = validate_generated_configuration(agents, [])

    assert result.valid is True
    assert result.violations == []


def test_validate_agent_description_with_manual_model_tag_is_a_violation() -> None:
    """A description that already carries a hand-authored (word) tag triggers a violation."""
    agents = [
        AgentDefinition(
            id="agent-1",
            description="(sonnet) Hand-authored description with its own tag",
            preferred_model=Model.HAIKU,
            completion_criteria=["Done"],
        ),
    ]

    result = validate_generated_configuration(agents, [])

    assert result.valid is False
    codes = [v.code for v in result.violations]
    assert "agent_description_has_manual_model_tag" in codes
    violation = next(
        v for v in result.violations if v.code == "agent_description_has_manual_model_tag"
    )
    assert "agent-1" in violation.message


def test_validate_agent_description_untagged_is_valid() -> None:
    """A normal, untagged description does not trigger the manual-tag check."""
    agents = [
        AgentDefinition(
            id="agent-1",
            description="Plain description with no tag",
            preferred_model=Model.SONNET,
            completion_criteria=["Done"],
        ),
    ]

    result = validate_generated_configuration(agents, [])

    assert result.valid is True
    assert result.violations == []


def test_render_validation_report_text_valid() -> None:
    """Rendering a valid result as text returns exact message."""
    result = ConfigValidationResult(valid=True, violations=[])

    report = render_validation_report(result, format="text")

    assert report == "Configuration is valid."


def test_render_validation_report_text_invalid() -> None:
    """Rendering an invalid result as text includes violation count and details."""
    violations = [
        ConfigViolation(code="duplicate_agent_id", message="agent 'x' duplicated"),
        ConfigViolation(code="agent_missing_completion_criteria", message="agent 'y' missing"),
    ]
    result = ConfigValidationResult(valid=False, violations=violations)

    report = render_validation_report(result, format="text")

    assert "Configuration validation failed (2 issue(s)):" in report
    assert "- duplicate_agent_id: agent 'x' duplicated" in report
    assert "- agent_missing_completion_criteria: agent 'y' missing" in report


def test_render_validation_report_json_valid() -> None:
    """Rendering as JSON produces valid JSON with ok status."""
    result = ConfigValidationResult(valid=True, violations=[])

    report = render_validation_report(result, format="json")

    data = json.loads(report)
    assert data["status"] == "ok"
    assert data["violations"] == []


def test_render_validation_report_json_invalid() -> None:
    """Rendering as JSON produces valid JSON with error status and violations."""
    violations = [
        ConfigViolation(
            code="duplicate_agent_id",
            message="agent 'x' duplicated",
            path="x",
        ),
    ]
    result = ConfigValidationResult(valid=False, violations=violations)

    report = render_validation_report(result, format="json")

    data = json.loads(report)
    assert data["status"] == "error"
    assert len(data["violations"]) == 1
    assert data["violations"][0]["code"] == "duplicate_agent_id"
    assert data["violations"][0]["message"] == "agent 'x' duplicated"
    assert data["violations"][0]["path"] == "x"


def test_render_validation_report_unknown_format_raises() -> None:
    """An unknown format raises ValueError."""
    result = ConfigValidationResult(valid=True, violations=[])

    with pytest.raises(ValueError, match="unknown format"):
        render_validation_report(result, format="unknown")

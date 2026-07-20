"""Tests for skills catalog and selection logic.

Tests cover:
- DEFAULT_SKILLS catalog structure and contents
- select_skills filtering by agent capabilities
- Ad-hoc skill creation from workflow-related decisions
- Deduplication and sorting behavior
- Deep-copy verification to prevent catalog mutation
"""

import copy

from quattroagents.domain import (
    AgentDefinition,
    Decision,
    DecisionSource,
    DecisionSourceType,
    DecisionStatus,
    DefinitionSource,
)
from quattroagents.generation.skills import DEFAULT_SKILLS, select_skills


def test_default_skills_has_exactly_seven_entries() -> None:
    """DEFAULT_SKILLS catalog contains exactly 7 entries."""
    assert len(DEFAULT_SKILLS) == 7


def test_default_skills_entries_have_required_fields() -> None:
    """Each DEFAULT_SKILLS entry has non-empty workflow, inputs, outputs, validation_criteria."""
    required_skills = [
        "implement-feature",
        "fix-bug",
        "review-change",
        "update-documentation",
        "run-regression-analysis",
        "prepare-release",
        "update-dependencies",
    ]

    for skill_id in required_skills:
        assert skill_id in DEFAULT_SKILLS, f"Missing skill: {skill_id}"

        skill = DEFAULT_SKILLS[skill_id]
        assert skill.id == skill_id
        assert skill.trigger, f"Skill {skill_id} has empty trigger"
        assert len(skill.workflow) > 0, f"Skill {skill_id} has empty workflow"
        assert len(skill.inputs) > 0, f"Skill {skill_id} has empty inputs"
        assert len(skill.outputs) > 0, f"Skill {skill_id} has empty outputs"
        assert len(skill.validation_criteria) > 0, f"Skill {skill_id} has empty validation_criteria"


def test_select_skills_with_empty_agents_and_no_decisions_returns_empty() -> None:
    """select_skills with empty agent list and no decisions returns empty list."""
    result = select_skills([], [])
    assert result == []


def test_select_skills_filters_by_agent_capabilities() -> None:
    """select_skills includes only skills usable by provided agents."""
    implementation_agent = AgentDefinition(
        id="implementation-agent", description="Implements features and fixes bugs"
    )

    result = select_skills([implementation_agent], [])

    # Should include skills usable by implementation-agent
    skill_ids = {skill.id for skill in result}
    assert "implement-feature" in skill_ids
    assert "fix-bug" in skill_ids

    # Should exclude skills not usable by implementation-agent
    assert "prepare-release" not in skill_ids  # only for release-agent
    assert "documentation-agent" not in {s for skill in result for s in skill.usable_by_agents}


def test_select_skills_excludes_skills_not_applicable_to_agents() -> None:
    """select_skills excludes default skills whose usable_by_agents don't intersect."""
    release_agent = AgentDefinition(id="release-agent", description="Prepares releases")

    result = select_skills([release_agent], [])

    # Should only include prepare-release
    skill_ids = {skill.id for skill in result}
    assert "prepare-release" in skill_ids
    assert "implement-feature" not in skill_ids
    assert "fix-bug" not in skill_ids


def test_select_skills_with_multiple_agents() -> None:
    """select_skills works correctly with multiple agents."""
    implementation_agent = AgentDefinition(
        id="implementation-agent", description="Implements features"
    )
    code_reviewer = AgentDefinition(id="code-reviewer", description="Reviews code")

    result = select_skills([implementation_agent, code_reviewer], [])

    skill_ids = {skill.id for skill in result}
    # Both agents' skills should be included
    assert "implement-feature" in skill_ids
    assert "fix-bug" in skill_ids
    assert "review-change" in skill_ids


def test_active_decision_with_workflow_in_title_creates_adhoc_skill() -> None:
    """ACTIVE decision with 'workflow' in title creates ad-hoc skill."""
    decision = Decision(
        id="dec-1",
        title="Set up workflow for CI/CD",
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Enable automated testing",
        status=DecisionStatus.ACTIVE,
        effects={"agents": ["implementation-agent"]},
    )

    result = select_skills([], [decision])

    assert len(result) == 1
    skill = result[0]
    assert skill.id.startswith("custom-")
    assert skill.source == DefinitionSource.ADHOC
    assert skill.trigger == "Set up workflow for CI/CD"


def test_adhoc_skill_id_uses_slugified_title() -> None:
    """Ad-hoc skill id is derived from slugified title."""
    decision = Decision(
        id="dec-1",
        title="Enable Feature Workflow Processing",
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="",
        status=DecisionStatus.ACTIVE,
        effects={},
    )

    result = select_skills([], [decision])

    assert len(result) == 1
    # Title slugifies to: lowercase, non-alphanumeric→hyphens, collapse, strip
    # "Enable Feature Workflow Processing" -> "enable-feature-workflow-processing"
    assert result[0].id == "custom-enable-feature-workflow-processing"


def test_slugify_handles_special_characters() -> None:
    """Slugified skill id collapses repeated hyphens and strips leading/trailing."""
    decision = Decision(
        id="dec-1",
        title="Implement!!!Feature...Workflow",
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="",
        status=DecisionStatus.ACTIVE,
        effects={},
    )

    result = select_skills([], [decision])

    assert len(result) == 1
    # Multiple special chars should collapse to single hyphen
    # No leading or trailing hyphens
    skill_id = result[0].id
    assert skill_id.startswith("custom-")
    assert not skill_id.endswith("-")
    assert "--" not in skill_id


def test_decision_with_workflow_classification_creates_adhoc_skill() -> None:
    """Decision with 'workflow' in classification creates ad-hoc skill."""
    decision = Decision(
        id="dec-1",
        title="Custom Task Execution",
        value={"classification": ["workflow"]},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Custom workflow needed",
        status=DecisionStatus.ACTIVE,
        effects={},
    )

    result = select_skills([], [decision])

    assert len(result) == 1
    assert result[0].source == DefinitionSource.ADHOC


def test_decision_with_workflow_classification_and_title_creates_one_skill() -> None:
    """Decision with both workflow classification and title is handled correctly."""
    decision = Decision(
        id="dec-1",
        title="Workflow Processing Task",
        value={"classification": ["workflow"]},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="",
        status=DecisionStatus.ACTIVE,
        effects={},
    )

    result = select_skills([], [decision])

    assert len(result) == 1
    assert result[0].source == DefinitionSource.ADHOC


def test_inactive_decision_does_not_create_adhoc_skill() -> None:
    """Non-ACTIVE decision does not create ad-hoc skill."""
    superseded_decision = Decision(
        id="dec-1",
        title="Workflow Something",
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="",
        status=DecisionStatus.SUPERSEDED,
        effects={},
    )

    uncertain_decision = Decision(
        id="dec-2",
        title="Workflow Something Else",
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="",
        status=DecisionStatus.UNCERTAIN,
        effects={},
    )

    result = select_skills([], [superseded_decision, uncertain_decision])

    assert len(result) == 0


def test_decision_without_workflow_does_not_create_adhoc_skill() -> None:
    """Decision without 'workflow' title or classification creates no skill."""
    decision = Decision(
        id="dec-1",
        title="Some Other Task",
        value={"classification": ["fact", "preference"]},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="",
        status=DecisionStatus.ACTIVE,
        effects={},
    )

    result = select_skills([], [decision])

    assert len(result) == 0


def test_workflow_title_matching_is_case_insensitive() -> None:
    """'workflow' in title is case-insensitive."""
    decisions = [
        Decision(
            id="dec-1",
            title="WORKFLOW Processing",
            value={},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="",
            status=DecisionStatus.ACTIVE,
            effects={},
        ),
        Decision(
            id="dec-2",
            title="Some Workflow Task",
            value={},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="",
            status=DecisionStatus.ACTIVE,
            effects={},
        ),
        Decision(
            id="dec-3",
            title="Workflow-Implementation",
            value={},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="",
            status=DecisionStatus.ACTIVE,
            effects={},
        ),
    ]

    result = select_skills([], decisions)

    # All three should be detected as workflow decisions
    assert len(result) == 3
    ids = {skill.id for skill in result}
    assert "custom-workflow-processing" in ids
    assert "custom-some-workflow-task" in ids
    assert "custom-workflow-implementation" in ids


def test_duplicate_slugified_ids_deduplicate_keeping_first() -> None:
    """Duplicate ad-hoc skill ids deduplicate, keeping first occurrence."""
    # Both decisions will slugify to same id
    decision1 = Decision(
        id="dec-1",
        title="Process Workflow Task",
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="First one",
        status=DecisionStatus.ACTIVE,
        effects={},
    )

    decision2 = Decision(
        id="dec-2",
        title="Process-Workflow-Task",  # Same after slugification
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Second one",
        status=DecisionStatus.ACTIVE,
        effects={},
    )

    result = select_skills([], [decision1, decision2])

    assert len(result) == 1
    assert result[0].trigger == "Process Workflow Task"  # From first decision


def test_returned_list_is_sorted_by_id() -> None:
    """Returned skill list is sorted by id."""
    impl_agent = AgentDefinition(id="implementation-agent", description="Impl")
    reviewer = AgentDefinition(id="code-reviewer", description="Review")

    # Get default skills for these agents
    default_result = select_skills([impl_agent, reviewer], [])

    # Verify sorted
    ids = [skill.id for skill in default_result]
    assert ids == sorted(ids)


def test_returned_list_with_adhoc_and_default_skills_is_sorted() -> None:
    """Combined default and ad-hoc skills are sorted by id."""
    impl_agent = AgentDefinition(id="implementation-agent", description="Impl")

    decision = Decision(
        id="dec-1",
        title="Awesome Workflow",
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="",
        status=DecisionStatus.ACTIVE,
        effects={},
    )

    result = select_skills([impl_agent], [decision])

    # Should have default skills (fix-bug, implement-feature) and custom-awesome-workflow
    ids = [skill.id for skill in result]
    assert ids == sorted(ids)
    assert "custom-awesome-workflow" in ids


def test_select_skills_does_not_mutate_default_skills() -> None:
    """select_skills does not mutate the DEFAULT_SKILLS catalog."""
    # Deep copy the catalog before calling select_skills
    catalog_before = copy.deepcopy(DEFAULT_SKILLS)

    impl_agent = AgentDefinition(id="implementation-agent", description="Impl")

    decision = Decision(
        id="dec-1",
        title="Workflow Modification",
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="",
        status=DecisionStatus.ACTIVE,
        effects={},
    )

    _ = select_skills([impl_agent], [decision])

    # Verify catalog unchanged
    assert DEFAULT_SKILLS == catalog_before
    for skill_id, skill_before in catalog_before.items():
        skill_after = DEFAULT_SKILLS[skill_id]
        assert skill_before.workflow == skill_after.workflow
        assert skill_before.inputs == skill_after.inputs
        assert skill_before.outputs == skill_after.outputs


def test_returned_skills_are_deep_copies_of_defaults() -> None:
    """Returned default skills are deep copies, not references."""
    impl_agent = AgentDefinition(id="implementation-agent", description="Impl")

    result = select_skills([impl_agent], [])

    for skill in result:
        # Modify the returned skill
        skill.workflow.append("Modified workflow step")

    # Verify original DEFAULT_SKILLS is unchanged
    original = DEFAULT_SKILLS["implement-feature"]
    assert "Modified workflow step" not in original.workflow


def test_adhoc_skill_with_reason_uses_reason_as_workflow() -> None:
    """Ad-hoc skill uses decision reason as workflow if available."""
    decision = Decision(
        id="dec-1",
        title="Workflow Task",
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Execute this specific workflow step",
        status=DecisionStatus.ACTIVE,
        effects={},
    )

    result = select_skills([], [decision])

    assert len(result) == 1
    assert result[0].workflow == ["Execute this specific workflow step"]


def test_adhoc_skill_without_reason_uses_title_as_workflow() -> None:
    """Ad-hoc skill uses decision title as workflow if reason is empty."""
    decision = Decision(
        id="dec-1",
        title="Workflow Task",
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="",
        status=DecisionStatus.ACTIVE,
        effects={},
    )

    result = select_skills([], [decision])

    assert len(result) == 1
    assert result[0].workflow == ["Workflow Task"]


def test_adhoc_skill_usable_by_agents_from_effects() -> None:
    """Ad-hoc skill usable_by_agents comes from decision effects."""
    decision = Decision(
        id="dec-1",
        title="Workflow Task",
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="",
        status=DecisionStatus.ACTIVE,
        effects={"agents": ["agent-1", "agent-2"]},
    )

    result = select_skills([], [decision])

    assert len(result) == 1
    assert set(result[0].usable_by_agents) == {"agent-1", "agent-2"}


def test_adhoc_skill_validation_criteria_from_value() -> None:
    """Ad-hoc skill validation_criteria comes from decision value."""
    decision = Decision(
        id="dec-1",
        title="Workflow Task",
        value={"validation_criteria": ["Check result", "Verify output"]},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="",
        status=DecisionStatus.ACTIVE,
        effects={},
    )

    result = select_skills([], [decision])

    assert len(result) == 1
    assert result[0].validation_criteria == ["Check result", "Verify output"]


def test_adhoc_skill_default_validation_criteria_if_missing() -> None:
    """Ad-hoc skill has default validation_criteria if not in value."""
    decision = Decision(
        id="dec-1",
        title="Workflow Task",
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="",
        status=DecisionStatus.ACTIVE,
        effects={},
    )

    result = select_skills([], [decision])

    assert len(result) == 1
    assert result[0].validation_criteria == ["manual review"]


def test_adhoc_skill_required_tools_from_value() -> None:
    """Ad-hoc skill required_tools comes from decision value."""
    decision = Decision(
        id="dec-1",
        title="Workflow Task",
        value={"mandatory_tools": ["tool-a", "tool-b"]},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="",
        status=DecisionStatus.ACTIVE,
        effects={},
    )

    result = select_skills([], [decision])

    assert len(result) == 1
    assert result[0].required_tools == ["tool-a", "tool-b"]


def test_adhoc_skill_empty_inputs_and_outputs() -> None:
    """Ad-hoc skill has empty inputs and outputs by default."""
    decision = Decision(
        id="dec-1",
        title="Workflow Task",
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="",
        status=DecisionStatus.ACTIVE,
        effects={},
    )

    result = select_skills([], [decision])

    assert len(result) == 1
    assert result[0].inputs == []
    assert result[0].outputs == []


def test_complex_scenario_default_plus_adhoc_plus_dedup() -> None:
    """Complex scenario: default skills, ad-hoc skills, and deduplication."""
    impl_agent = AgentDefinition(id="implementation-agent", description="Impl")
    reviewer = AgentDefinition(id="code-reviewer", description="Review")

    decisions = [
        Decision(
            id="dec-1",
            title="Implement Workflow Changes",
            value={},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="",
            status=DecisionStatus.ACTIVE,
            effects={},
        ),
        Decision(
            id="dec-2",
            title="Implement-Workflow-Changes",  # Duplicate, should be skipped
            value={},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="",
            status=DecisionStatus.ACTIVE,
            effects={},
        ),
        Decision(
            id="dec-3",
            title="Review Workflow Updates",
            value={},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="",
            status=DecisionStatus.ACTIVE,
            effects={},
        ),
    ]

    result = select_skills([impl_agent, reviewer], decisions)

    # Default skills: implement-feature, fix-bug, review-change
    # Ad-hoc skills: custom-implement-workflow-changes, custom-review-workflow-updates
    # (second decision deduplicated)
    ids = {skill.id for skill in result}
    assert "implement-feature" in ids
    assert "fix-bug" in ids
    assert "review-change" in ids
    assert "custom-implement-workflow-changes" in ids
    assert "custom-review-workflow-updates" in ids

    # Verify sorted and no duplicates
    id_list = [skill.id for skill in result]
    assert len(id_list) == len(set(id_list))
    assert id_list == sorted(id_list)

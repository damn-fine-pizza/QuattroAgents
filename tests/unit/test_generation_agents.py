"""Tests for the archetype catalog and selection logic.

Covers ARCHETYPES catalog validation, select_agents() behavior (both tier
variants of every selected archetype, decision-driven attribute injection
matched by archetype_id), and attach_orchestrator_roster() with multiple
project-orchestrator variants.
"""

import copy

from quattroagents.domain import (
    Decision,
    DecisionSource,
    DecisionSourceType,
    DecisionStatus,
    DefinitionSource,
    ProjectProfile,
)
from quattroagents.generation.agents import (
    attach_orchestrator_roster,
    select_agents,
)
from quattroagents.generation.archetypes import ARCHETYPES


def test_archetypes_has_exactly_13_entries() -> None:
    """ARCHETYPES catalog must have exactly 13 archetype entries."""
    assert len(ARCHETYPES) == 13


def test_every_archetype_has_both_tier_variants() -> None:
    """Every archetype must define exactly a haiku and a sonnet variant."""
    for archetype_id, variants in ARCHETYPES.items():
        assert set(variants.keys()) == {"haiku", "sonnet"}, (
            f"Archetype {archetype_id} must have exactly haiku and sonnet variants"
        )


def test_every_archetype_variant_id_and_archetype_id_are_consistent() -> None:
    """Each variant's id is '{archetype_id}-{tier}' and archetype_id matches the catalog key."""
    for archetype_id, variants in ARCHETYPES.items():
        for tier, agent in variants.items():
            assert agent.id == f"{archetype_id}-{tier}"
            assert agent.archetype_id == archetype_id


def test_every_archetype_variant_has_non_empty_completion_criteria() -> None:
    """Every archetype variant must have completion_criteria for downstream validation."""
    for archetype_id, variants in ARCHETYPES.items():
        for tier, agent in variants.items():
            assert agent.completion_criteria, (
                f"Agent {archetype_id}/{tier} has empty completion_criteria; "
                "downstream validation requires non-empty list"
            )
            assert isinstance(agent.completion_criteria, list), (
                f"Agent {archetype_id}/{tier} completion_criteria must be a list"
            )
            assert all(isinstance(c, str) for c in agent.completion_criteria), (
                f"Agent {archetype_id}/{tier} completion_criteria must contain only strings"
            )


def test_minimal_profile_with_no_decisions_selects_core_agents() -> None:
    """Minimal ProjectProfile (empty everything) selects core archetypes only."""
    profile = ProjectProfile(fingerprint="test")
    decisions: list[Decision] = []

    selected = select_agents(profile, decisions)
    selected_archetype_ids = {a.archetype_id for a in selected}

    # Always-included archetypes
    assert "project-orchestrator" in selected_archetype_ids
    assert "repository-cartographer" in selected_archetype_ids
    assert "code-reviewer" in selected_archetype_ids
    assert "implementation-agent" in selected_archetype_ids
    assert "documentation-agent" in selected_archetype_ids

    # Decision-gated archetypes (not included without decisions)
    assert "bdd-feature-agent" not in selected_archetype_ids
    assert "performance-agent" not in selected_archetype_ids
    assert "security-reviewer" not in selected_archetype_ids
    assert "release-agent" not in selected_archetype_ids

    # Profile-gated archetypes (not included with empty profile)
    assert "architecture-guardian" not in selected_archetype_ids
    assert "test-agent" not in selected_archetype_ids
    assert "dependency-agent" not in selected_archetype_ids
    assert "ci-build-agent" not in selected_archetype_ids


def test_every_selected_archetype_yields_both_tier_variants() -> None:
    """Each selected archetype instantiates both its haiku and sonnet variant."""
    profile = ProjectProfile(fingerprint="test", test_frameworks=["pytest"])
    decisions: list[Decision] = []

    selected = select_agents(profile, decisions)
    selected_ids = {a.id for a in selected}

    assert "implementation-agent-haiku" in selected_ids
    assert "implementation-agent-sonnet" in selected_ids
    assert "test-agent-haiku" in selected_ids
    assert "test-agent-sonnet" in selected_ids


def test_subsystems_3_or_more_selects_architecture_guardian() -> None:
    """Architecture-guardian selected when profile.subsystems has 3+ entries."""
    profile = ProjectProfile(fingerprint="test", subsystems=["core", "auth", "api"])
    decisions: list[Decision] = []

    selected = select_agents(profile, decisions)
    selected_archetype_ids = {a.archetype_id for a in selected}

    assert "architecture-guardian" in selected_archetype_ids


def test_subsystems_less_than_3_without_risks_does_not_select_architecture_guardian() -> None:
    """Architecture-guardian NOT selected when subsystems < 3 and no risks/legacy_areas."""
    profile = ProjectProfile(
        fingerprint="test",
        subsystems=["core", "auth"],  # Only 2
    )
    decisions: list[Decision] = []

    selected = select_agents(profile, decisions)
    selected_archetype_ids = {a.archetype_id for a in selected}

    assert "architecture-guardian" not in selected_archetype_ids


def test_subsystems_less_than_3_with_risks_selects_architecture_guardian() -> None:
    """Architecture-guardian selected when risks present, even with < 3 subsystems."""
    profile = ProjectProfile(
        fingerprint="test", subsystems=["core"], risks=["SQL injection vulnerability in auth layer"]
    )
    decisions: list[Decision] = []

    selected = select_agents(profile, decisions)
    selected_archetype_ids = {a.archetype_id for a in selected}

    assert "architecture-guardian" in selected_archetype_ids


def test_subsystems_less_than_3_with_legacy_areas_selects_architecture_guardian() -> None:
    """Architecture-guardian selected when legacy_areas present, even with < 3 subsystems."""
    profile = ProjectProfile(
        fingerprint="test", subsystems=["core"], legacy_areas=["Payment processor from 2015"]
    )
    decisions: list[Decision] = []

    selected = select_agents(profile, decisions)
    selected_archetype_ids = {a.archetype_id for a in selected}

    assert "architecture-guardian" in selected_archetype_ids


def test_empty_test_frameworks_does_not_select_test_agent() -> None:
    """Test-agent NOT selected when profile.test_frameworks is empty."""
    profile = ProjectProfile(fingerprint="test", test_frameworks=[])
    decisions: list[Decision] = []

    selected = select_agents(profile, decisions)
    selected_archetype_ids = {a.archetype_id for a in selected}

    assert "test-agent" not in selected_archetype_ids


def test_non_empty_test_frameworks_selects_test_agent() -> None:
    """Test-agent selected when profile.test_frameworks has entries."""
    profile = ProjectProfile(fingerprint="test", test_frameworks=["pytest"])
    decisions: list[Decision] = []

    selected = select_agents(profile, decisions)
    selected_archetype_ids = {a.archetype_id for a in selected}

    assert "test-agent" in selected_archetype_ids


def test_empty_build_systems_does_not_select_dependency_agent() -> None:
    """Dependency-agent NOT selected when profile.build_systems is empty."""
    profile = ProjectProfile(fingerprint="test", build_systems=[])
    decisions: list[Decision] = []

    selected = select_agents(profile, decisions)
    selected_archetype_ids = {a.archetype_id for a in selected}

    assert "dependency-agent" not in selected_archetype_ids


def test_non_empty_build_systems_selects_dependency_agent() -> None:
    """Dependency-agent selected when profile.build_systems has entries."""
    profile = ProjectProfile(fingerprint="test", build_systems=["poetry"])
    decisions: list[Decision] = []

    selected = select_agents(profile, decisions)
    selected_archetype_ids = {a.archetype_id for a in selected}

    assert "dependency-agent" in selected_archetype_ids


def test_empty_ci_systems_does_not_select_ci_build_agent() -> None:
    """CI-build-agent NOT selected when profile.ci_systems is empty."""
    profile = ProjectProfile(fingerprint="test", ci_systems=[])
    decisions: list[Decision] = []

    selected = select_agents(profile, decisions)
    selected_archetype_ids = {a.archetype_id for a in selected}

    assert "ci-build-agent" not in selected_archetype_ids


def test_non_empty_ci_systems_selects_ci_build_agent() -> None:
    """CI-build-agent selected when profile.ci_systems has entries."""
    profile = ProjectProfile(fingerprint="test", ci_systems=["github-actions"])
    decisions: list[Decision] = []

    selected = select_agents(profile, decisions)
    selected_archetype_ids = {a.archetype_id for a in selected}

    assert "ci-build-agent" in selected_archetype_ids


def test_decision_with_bdd_in_title_selects_bdd_feature_agent() -> None:
    """BDD-feature-agent selected when decision title contains 'bdd' (case-insensitive)."""
    profile = ProjectProfile(fingerprint="test")
    decisions = [
        Decision(
            id="d1",
            title="Implement BDD test scenarios",
            value={},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="User requirement",
            status=DecisionStatus.ACTIVE,
        )
    ]

    selected = select_agents(profile, decisions)
    selected_archetype_ids = {a.archetype_id for a in selected}

    assert "bdd-feature-agent" in selected_archetype_ids


def test_decision_with_bdd_case_insensitive() -> None:
    """BDD-feature-agent selected regardless of 'bdd' casing."""
    profile = ProjectProfile(fingerprint="test")
    decisions = [
        Decision(
            id="d1",
            title="Implement Gherkin BDD scenarios",
            value={},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="Behavioral testing required",
            status=DecisionStatus.ACTIVE,
        )
    ]

    selected = select_agents(profile, decisions)
    selected_archetype_ids = {a.archetype_id for a in selected}

    assert "bdd-feature-agent" in selected_archetype_ids


def test_decision_with_gherkin_in_value_selects_bdd_feature_agent() -> None:
    """BDD-feature-agent selected when 'gherkin' appears in decision value."""
    profile = ProjectProfile(fingerprint="test")
    decisions = [
        Decision(
            id="d1",
            title="Feature specifications",
            value={"format": "gherkin"},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="Gherkin format required",
            status=DecisionStatus.ACTIVE,
        )
    ]

    selected = select_agents(profile, decisions)
    selected_archetype_ids = {a.archetype_id for a in selected}

    assert "bdd-feature-agent" in selected_archetype_ids


def test_decision_with_security_in_title_selects_security_reviewer() -> None:
    """Security-reviewer selected when decision title contains 'security' (case-insensitive)."""
    profile = ProjectProfile(fingerprint="test")
    decisions = [
        Decision(
            id="d1",
            title="Implement security audit",
            value={},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="Compliance requirement",
            status=DecisionStatus.ACTIVE,
        )
    ]

    selected = select_agents(profile, decisions)
    selected_archetype_ids = {a.archetype_id for a in selected}

    assert "security-reviewer" in selected_archetype_ids


def test_decision_with_performance_in_title_selects_performance_agent() -> None:
    """Performance-agent selected when 'performance' in decision title (case-insensitive)."""
    profile = ProjectProfile(fingerprint="test")
    decisions = [
        Decision(
            id="d1",
            title="Optimize performance for large datasets",
            value={},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="User complaints about slowness",
            status=DecisionStatus.ACTIVE,
        )
    ]

    selected = select_agents(profile, decisions)
    selected_archetype_ids = {a.archetype_id for a in selected}

    assert "performance-agent" in selected_archetype_ids


def test_decision_with_realtime_in_title_selects_performance_agent() -> None:
    """Performance-agent selected when 'realtime' in decision title."""
    profile = ProjectProfile(fingerprint="test")
    decisions = [
        Decision(
            id="d1",
            title="Implement real-time data processing",
            value={},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="Real-time requirements",
            status=DecisionStatus.ACTIVE,
        )
    ]

    selected = select_agents(profile, decisions)
    selected_archetype_ids = {a.archetype_id for a in selected}

    assert "performance-agent" in selected_archetype_ids


def test_decision_with_release_in_title_selects_release_agent() -> None:
    """Release-agent selected when decision title contains 'release' (case-insensitive)."""
    profile = ProjectProfile(fingerprint="test")
    decisions = [
        Decision(
            id="d1",
            title="Prepare v1.0 release",
            value={},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="Ready for production",
            status=DecisionStatus.ACTIVE,
        )
    ]

    selected = select_agents(profile, decisions)
    selected_archetype_ids = {a.archetype_id for a in selected}

    assert "release-agent" in selected_archetype_ids


def test_active_decision_with_agent_effects_injects_constraints_into_both_tiers() -> None:
    """ACTIVE decision targeting an archetype injects title:reason constraint into both tier variants."""
    profile = ProjectProfile(fingerprint="test")
    decisions = [
        Decision(
            id="d1",
            title="Use latest Python features",
            value={},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="Leverage modern syntax and performance",
            status=DecisionStatus.ACTIVE,
            effects={"agents": ["implementation-agent"]},
        )
    ]

    selected = select_agents(profile, decisions)
    impl_agents = [a for a in selected if a.archetype_id == "implementation-agent"]

    assert len(impl_agents) == 2
    for impl_agent in impl_agents:
        assert (
            "Use latest Python features: Leverage modern syntax and performance"
            in impl_agent.constraints
        )


def test_active_decision_sets_agent_source_to_adhoc_for_both_tiers() -> None:
    """ACTIVE decision with agent effects sets source to ADHOC on both tier variants."""
    profile = ProjectProfile(fingerprint="test")
    decisions = [
        Decision(
            id="d1",
            title="Apply custom rule",
            value={},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="Project-specific requirement",
            status=DecisionStatus.ACTIVE,
            effects={"agents": ["code-reviewer"]},
        )
    ]

    selected = select_agents(profile, decisions)
    reviewer_agents = [a for a in selected if a.archetype_id == "code-reviewer"]

    assert len(reviewer_agents) == 2
    for reviewer_agent in reviewer_agents:
        assert reviewer_agent.source == DefinitionSource.ADHOC


def test_non_active_decision_does_not_inject_constraints() -> None:
    """Non-ACTIVE decisions (e.g., SUPERSEDED) do NOT inject constraints."""
    profile = ProjectProfile(fingerprint="test")
    decisions = [
        Decision(
            id="d1",
            title="Old constraint",
            value={},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="Previously required",
            status=DecisionStatus.SUPERSEDED,  # Not ACTIVE
            effects={"agents": ["implementation-agent"]},
        )
    ]

    selected = select_agents(profile, decisions)
    impl_agents = [a for a in selected if a.archetype_id == "implementation-agent"]

    assert len(impl_agents) == 2
    for impl_agent in impl_agents:
        assert len(impl_agent.constraints) == 0
        assert impl_agent.source == DefinitionSource.DEFAULT


def test_decision_mandatory_tools_injected_into_both_tiers() -> None:
    """Decision value.mandatory_tools list injected into both tier variants."""
    profile = ProjectProfile(fingerprint="test")
    decisions = [
        Decision(
            id="d1",
            title="Use rtk for all commands",
            value={"mandatory_tools": ["rtk", "jq"]},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="Token optimization required",
            status=DecisionStatus.ACTIVE,
            effects={"agents": ["implementation-agent"]},
        )
    ]

    selected = select_agents(profile, decisions)
    impl_agents = [a for a in selected if a.archetype_id == "implementation-agent"]

    assert len(impl_agents) == 2
    for impl_agent in impl_agents:
        assert "rtk" in impl_agent.mandatory_tools
        assert "jq" in impl_agent.mandatory_tools


def test_mandatory_tools_not_duplicated() -> None:
    """Mandatory tools already present are not duplicated."""
    profile = ProjectProfile(fingerprint="test")
    decisions = [
        Decision(
            id="d1",
            title="Add mandatory tools",
            value={"mandatory_tools": ["rtk"]},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="Required",
            status=DecisionStatus.ACTIVE,
            effects={"agents": ["implementation-agent"]},
        ),
        Decision(
            id="d2",
            title="Add same tools again",
            value={"mandatory_tools": ["rtk"]},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="Repeated requirement",
            status=DecisionStatus.ACTIVE,
            effects={"agents": ["implementation-agent"]},
        ),
    ]

    selected = select_agents(profile, decisions)
    impl_agent = next((a for a in selected if a.id == "implementation-agent-haiku"), None)

    assert impl_agent is not None
    rtk_count = sum(1 for tool in impl_agent.mandatory_tools if tool == "rtk")
    assert rtk_count == 1


def test_returned_list_is_sorted_by_id() -> None:
    """Returned agent list is sorted lexicographically by id."""
    profile = ProjectProfile(
        fingerprint="test",
        test_frameworks=["pytest"],
        build_systems=["poetry"],
        ci_systems=["github-actions"],
    )
    decisions: list[Decision] = []

    selected = select_agents(profile, decisions)
    selected_ids = [a.id for a in selected]

    assert selected_ids == sorted(selected_ids)


def test_multiple_select_agents_calls_do_not_mutate_archetypes() -> None:
    """Calling select_agents multiple times does not mutate the ARCHETYPES catalog."""
    original_impl_agent = ARCHETYPES["implementation-agent"]["sonnet"]
    original_constraints_len = len(original_impl_agent.constraints)
    assert original_constraints_len == 0, "Initial constraints should be empty"

    # First call with decision that injects constraints
    profile1 = ProjectProfile(fingerprint="test1")
    decisions1 = [
        Decision(
            id="d1",
            title="Add constraint",
            value={},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="Requirement",
            status=DecisionStatus.ACTIVE,
            effects={"agents": ["implementation-agent"]},
        )
    ]
    selected1 = select_agents(profile1, decisions1)
    selected1_impl = next((a for a in selected1 if a.id == "implementation-agent-sonnet"), None)
    assert selected1_impl is not None
    assert len(selected1_impl.constraints) > 0

    # Second call with no decisions
    profile2 = ProjectProfile(fingerprint="test2")
    decisions2: list[Decision] = []
    selected2 = select_agents(profile2, decisions2)
    selected2_impl = next((a for a in selected2 if a.id == "implementation-agent-sonnet"), None)
    assert selected2_impl is not None
    assert len(selected2_impl.constraints) == 0

    # Verify ARCHETYPES is unchanged
    assert len(ARCHETYPES["implementation-agent"]["sonnet"].constraints) == original_constraints_len


def test_multiple_decisions_targeting_same_agent_accumulate_constraints() -> None:
    """Multiple ACTIVE decisions targeting same archetype add multiple constraints."""
    profile = ProjectProfile(fingerprint="test")
    decisions = [
        Decision(
            id="d1",
            title="Constraint one",
            value={},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="First requirement",
            status=DecisionStatus.ACTIVE,
            effects={"agents": ["implementation-agent"]},
        ),
        Decision(
            id="d2",
            title="Constraint two",
            value={},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="Second requirement",
            status=DecisionStatus.ACTIVE,
            effects={"agents": ["implementation-agent"]},
        ),
    ]

    selected = select_agents(profile, decisions)
    impl_agent = next((a for a in selected if a.id == "implementation-agent-haiku"), None)

    assert impl_agent is not None
    assert len(impl_agent.constraints) == 2
    assert "Constraint one: First requirement" in impl_agent.constraints
    assert "Constraint two: Second requirement" in impl_agent.constraints


def test_decision_targeting_multiple_agents_injects_all() -> None:
    """Decision with multiple archetypes in effects targets all of them."""
    profile = ProjectProfile(fingerprint="test")
    decisions = [
        Decision(
            id="d1",
            title="Multi-agent constraint",
            value={},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="Applies to both",
            status=DecisionStatus.ACTIVE,
            effects={"agents": ["implementation-agent", "code-reviewer"]},
        )
    ]

    selected = select_agents(profile, decisions)
    impl_agent = next((a for a in selected if a.id == "implementation-agent-haiku"), None)
    reviewer = next((a for a in selected if a.id == "code-reviewer-haiku"), None)

    assert impl_agent is not None
    assert "Multi-agent constraint: Applies to both" in impl_agent.constraints
    assert impl_agent.source == DefinitionSource.ADHOC

    assert reviewer is not None
    assert "Multi-agent constraint: Applies to both" in reviewer.constraints
    assert reviewer.source == DefinitionSource.ADHOC


def test_decision_effects_empty_agents_list_no_injection() -> None:
    """Decision with empty agents list in effects does not inject anything."""
    profile = ProjectProfile(fingerprint="test")
    decisions = [
        Decision(
            id="d1",
            title="Empty effects",
            value={},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="No targeted agents",
            status=DecisionStatus.ACTIVE,
            effects={"agents": []},  # Empty agents list
        )
    ]

    selected = select_agents(profile, decisions)
    impl_agent = next((a for a in selected if a.id == "implementation-agent-haiku"), None)

    assert impl_agent is not None
    assert len(impl_agent.constraints) == 0
    assert impl_agent.source == DefinitionSource.DEFAULT


def test_decision_no_effects_key_no_injection() -> None:
    """Decision with no 'agents' key in effects does not target any agents."""
    profile = ProjectProfile(fingerprint="test")
    decisions = [
        Decision(
            id="d1",
            title="No agents key",
            value={},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="Effects has no agents key",
            status=DecisionStatus.ACTIVE,
            effects={"skills": ["skill-1"]},  # Different key, not agents
        )
    ]

    selected = select_agents(profile, decisions)
    impl_agent = next((a for a in selected if a.id == "implementation-agent-haiku"), None)

    assert impl_agent is not None
    assert len(impl_agent.constraints) == 0
    assert impl_agent.source == DefinitionSource.DEFAULT


def test_decision_value_not_dict_no_mandatory_tools_injection() -> None:
    """Decision with non-dict value does not inject mandatory_tools."""
    profile = ProjectProfile(fingerprint="test")
    decisions = [
        Decision(
            id="d1",
            title="Non-dict value",
            value="some string value",
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="Value is not a dict",
            status=DecisionStatus.ACTIVE,
            effects={"agents": ["implementation-agent"]},
        )
    ]

    selected = select_agents(profile, decisions)
    impl_agent = next((a for a in selected if a.id == "implementation-agent-haiku"), None)

    assert impl_agent is not None
    assert len(impl_agent.mandatory_tools) == 0


def test_decision_mandatory_tools_not_list_no_injection() -> None:
    """Decision with non-list mandatory_tools in value does not inject."""
    profile = ProjectProfile(fingerprint="test")
    decisions = [
        Decision(
            id="d1",
            title="Non-list mandatory_tools",
            value={"mandatory_tools": "single_tool"},  # String, not list
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="mandatory_tools is not a list",
            status=DecisionStatus.ACTIVE,
            effects={"agents": ["implementation-agent"]},
        )
    ]

    selected = select_agents(profile, decisions)
    impl_agent = next((a for a in selected if a.id == "implementation-agent-haiku"), None)

    assert impl_agent is not None
    assert len(impl_agent.mandatory_tools) == 0


def test_all_decision_selection_rules_work_together() -> None:
    """Combined test: multiple profile attributes and decisions select correctly."""
    profile = ProjectProfile(
        fingerprint="complex",
        test_frameworks=["pytest", "unittest"],
        build_systems=["poetry"],
        ci_systems=["github-actions"],
        subsystems=["api", "auth", "database"],
        risks=["Legacy authentication system"],
    )
    decisions = [
        Decision(
            id="d1",
            title="Implement BDD scenarios for user flows",
            value={"format": "gherkin"},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="Stakeholder requirement",
            status=DecisionStatus.ACTIVE,
        ),
        Decision(
            id="d2",
            title="Security review for authentication changes",
            value={},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="Compliance",
            status=DecisionStatus.ACTIVE,
        ),
        Decision(
            id="d3",
            title="Performance optimization for database queries",
            value={},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="Slow queries reported",
            status=DecisionStatus.ACTIVE,
        ),
        Decision(
            id="d4",
            title="Prepare v2.0 release",
            value={},
            source=DecisionSource(type=DecisionSourceType.USER),
            reason="Major version bump",
            status=DecisionStatus.ACTIVE,
        ),
    ]

    selected = select_agents(profile, decisions)
    selected_archetype_ids = {a.archetype_id for a in selected}

    # Core archetypes
    assert "project-orchestrator" in selected_archetype_ids
    assert "repository-cartographer" in selected_archetype_ids
    assert "code-reviewer" in selected_archetype_ids
    assert "implementation-agent" in selected_archetype_ids
    assert "documentation-agent" in selected_archetype_ids

    # Profile-driven
    assert "architecture-guardian" in selected_archetype_ids  # 3+ subsystems and risks
    assert "test-agent" in selected_archetype_ids  # test_frameworks non-empty
    assert "dependency-agent" in selected_archetype_ids  # build_systems non-empty
    assert "ci-build-agent" in selected_archetype_ids  # ci_systems non-empty

    # Decision-driven
    assert "bdd-feature-agent" in selected_archetype_ids  # "bdd" in decision d1
    assert "security-reviewer" in selected_archetype_ids  # "security" in decision d2
    assert "performance-agent" in selected_archetype_ids  # "performance" in decision d3
    assert "release-agent" in selected_archetype_ids  # "release" in decision d4

    # All 13 archetypes should be selected, each yielding both tier variants
    assert len(selected_archetype_ids) == 13
    assert len(selected) == 26


# Tests: attach_orchestrator_roster / project-orchestrator collaboration_notes


def test_select_agents_gives_both_orchestrator_variants_a_roster_of_siblings() -> None:
    """Both orchestrator tier variants receive a roster of siblings in collaboration_notes."""
    profile = ProjectProfile(
        fingerprint="test",
        test_frameworks=["pytest"],
        build_systems=["setuptools"],
    )
    decisions: list[Decision] = []

    selected = select_agents(profile, decisions)
    orchestrators = [a for a in selected if a.archetype_id == "project-orchestrator"]

    assert len(orchestrators) == 2
    for orchestrator in orchestrators:
        assert orchestrator.collaboration_notes
        assert (
            "Available agents in this project's generated team" in orchestrator.collaboration_notes
        )
        # Verify at least one sibling is listed
        assert "repository-cartographer-haiku" in orchestrator.collaboration_notes


def test_select_agents_orchestrator_roster_excludes_orchestrator_variants() -> None:
    """Orchestrator roster does NOT list either orchestrator variant as a sibling."""
    profile = ProjectProfile(
        fingerprint="test",
        test_frameworks=["pytest"],
        build_systems=["setuptools"],
    )
    decisions: list[Decision] = []

    selected = select_agents(profile, decisions)
    orchestrators = [a for a in selected if a.archetype_id == "project-orchestrator"]

    assert len(orchestrators) == 2
    for orchestrator in orchestrators:
        assert orchestrator.collaboration_notes
        assert "- project-orchestrator-haiku:" not in orchestrator.collaboration_notes
        assert "- project-orchestrator-sonnet:" not in orchestrator.collaboration_notes


def test_select_agents_orchestrator_roster_lists_every_selected_sibling() -> None:
    """Every selected sibling agent appears in both orchestrator variants' collaboration_notes."""
    profile = ProjectProfile(
        fingerprint="test",
        test_frameworks=["pytest"],
        build_systems=["setuptools"],
        ci_systems=["github-actions"],
        subsystems=["core", "auth", "api"],
    )
    decisions: list[Decision] = []

    selected = select_agents(profile, decisions)
    orchestrators = [a for a in selected if a.archetype_id == "project-orchestrator"]
    siblings = [a for a in selected if a.archetype_id != "project-orchestrator"]

    assert len(orchestrators) == 2
    assert siblings  # Verify there are siblings to check

    for orchestrator in orchestrators:
        assert orchestrator.collaboration_notes
        for sibling in siblings:
            assert f"- {sibling.id}:" in orchestrator.collaboration_notes, (
                f"Sibling {sibling.id} not found in orchestrator's collaboration_notes"
            )


def test_attach_orchestrator_roster_no_orchestrator_returns_unchanged() -> None:
    """If no project-orchestrator variant in list, attach_orchestrator_roster returns unchanged."""
    agents = [
        copy.deepcopy(ARCHETYPES["repository-cartographer"]["haiku"]),
        copy.deepcopy(ARCHETYPES["code-reviewer"]["haiku"]),
    ]

    result = attach_orchestrator_roster(agents)

    assert result == agents
    assert len(result) == 2
    repo_cart = next((a for a in result if a.id == "repository-cartographer-haiku"), None)
    assert repo_cart is not None
    assert repo_cart.collaboration_notes == ""


def test_attach_orchestrator_roster_orchestrator_only_returns_unchanged() -> None:
    """If only project-orchestrator variants (no siblings), collaboration_notes unchanged."""
    agents = [
        copy.deepcopy(ARCHETYPES["project-orchestrator"]["haiku"]),
        copy.deepcopy(ARCHETYPES["project-orchestrator"]["sonnet"]),
    ]

    result = attach_orchestrator_roster(agents)

    assert result == agents
    assert len(result) == 2
    for orchestrator in result:
        assert orchestrator.collaboration_notes == ""


def test_attach_orchestrator_roster_adds_roster_to_existing_notes() -> None:
    """If orchestrator has existing collaboration_notes, roster is appended."""
    orchestrator = copy.deepcopy(ARCHETYPES["project-orchestrator"]["sonnet"])
    orchestrator.collaboration_notes = "Existing collaboration notes"

    agents = [
        orchestrator,
        copy.deepcopy(ARCHETYPES["repository-cartographer"]["haiku"]),
    ]

    result = attach_orchestrator_roster(agents)

    assert len(result) == 2
    result_orchestrator = result[0]
    # Existing notes should be preserved, then roster appended
    assert "Existing collaboration notes" in result_orchestrator.collaboration_notes
    assert (
        "Available agents in this project's generated team"
        in result_orchestrator.collaboration_notes
    )
    # Verify the separator newlines
    assert "\n\n" in result_orchestrator.collaboration_notes

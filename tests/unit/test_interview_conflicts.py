"""Unit tests for conflict detection and resolution in the Interview Engine."""

import pytest

from quattroagents.domain import (
    ConflictRecord,
    ConflictSeverity,
    ConflictStatus,
    ConflictType,
    Decision,
    DecisionScope,
    DecisionSource,
    DecisionSourceType,
    DecisionStatus,
    ProjectProfile,
    ToolDefinition,
)
from quattroagents.interview.conflicts import detect_conflicts, resolve_conflict

# ============================================================================
# Fixtures for common test objects
# ============================================================================


def _make_decision(
    id_: str,
    title: str,
    value: dict,
    status: DecisionStatus = DecisionStatus.ACTIVE,
    decision_scope: DecisionScope = DecisionScope.PROJECT_WIDE,
    updated_at: str = "2024-01-01T00:00:00Z",
) -> Decision:
    """Helper to create a Decision with sensible defaults."""
    return Decision(
        id=id_,
        title=title,
        value=value,
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Test decision",
        decision_scope=decision_scope,
        status=status,
        updated_at=updated_at,
    )


def _make_profile(
    test_frameworks: list[str] | None = None,
    tools: list[ToolDefinition] | None = None,
) -> ProjectProfile:
    """Helper to create a ProjectProfile with sensible defaults."""
    return ProjectProfile(
        fingerprint="test-fp",
        test_frameworks=test_frameworks or [],
        tools=tools or [],
    )


# ============================================================================
# Test detect_conflicts - Test Case 1: Empty input
# ============================================================================


def test_detect_conflicts_empty_lists_returns_empty() -> None:
    """No decisions, no profile issues -> empty conflict list."""
    decisions = []
    profile = _make_profile()

    conflicts = detect_conflicts(decisions, profile)

    assert conflicts == []


# ============================================================================
# Test detect_conflicts - Test Case 2: BDD requirement vs. framework availability
# ============================================================================


def test_detect_conflicts_bdd_requirement_without_bdd_framework_raises_conflict() -> None:
    """Active decision requiring BDD with no BDD framework -> USER_VS_REPOSITORY conflict."""
    decisions = [
        _make_decision(
            id_="dec-1",
            title="Use BDD",
            value={"policy": "require BDD for all features"},
        )
    ]
    profile = _make_profile(test_frameworks=["pytest", "unittest"])

    conflicts = detect_conflicts(decisions, profile)

    assert len(conflicts) == 1
    assert conflicts[0].type == ConflictType.USER_VS_REPOSITORY
    assert conflicts[0].decision_id == "dec-1"
    assert conflicts[0].status == ConflictStatus.UNRESOLVED
    assert len(conflicts[0].possible_resolutions) > 0
    assert conflicts[0].id == "conflict-0"


def test_detect_conflicts_bdd_requirement_with_cucumber_framework_no_conflict() -> None:
    """Active decision requiring BDD with cucumber framework -> no conflict."""
    decisions = [
        _make_decision(
            id_="dec-1",
            title="Use BDD",
            value={"policy": "require BDD for all features"},
        )
    ]
    profile = _make_profile(test_frameworks=["pytest", "cucumber"])

    conflicts = detect_conflicts(decisions, profile)

    assert conflicts == []


def test_detect_conflicts_bdd_requirement_with_behave_framework_no_conflict() -> None:
    """Active decision requiring BDD with behave framework -> no conflict."""
    decisions = [
        _make_decision(
            id_="dec-1",
            title="Use BDD",
            value={"policy": "require BDD for all features"},
        )
    ]
    profile = _make_profile(test_frameworks=["behave", "pytest"])

    conflicts = detect_conflicts(decisions, profile)

    assert conflicts == []


def test_detect_conflicts_bdd_requirement_with_gherkin_framework_no_conflict() -> None:
    """Active decision requiring BDD with gherkin framework -> no conflict."""
    decisions = [
        _make_decision(
            id_="dec-1",
            title="Use BDD",
            value={"policy": "require BDD"},
        )
    ]
    profile = _make_profile(test_frameworks=["gherkin"])

    conflicts = detect_conflicts(decisions, profile)

    assert conflicts == []


def test_detect_conflicts_bdd_check_is_case_insensitive() -> None:
    """BDD check should be case-insensitive (REQUIRE, Require, require all work)."""
    decisions = [
        _make_decision(
            id_="dec-1",
            title="Use BDD",
            value={"policy": "REQUIRE BDD"},
        )
    ]
    profile = _make_profile(test_frameworks=["pytest"])

    conflicts = detect_conflicts(decisions, profile)

    assert len(conflicts) == 1


def test_detect_conflicts_bdd_decision_inactive_no_conflict() -> None:
    """Inactive decision requiring BDD -> no conflict (even if no BDD framework)."""
    decisions = [
        _make_decision(
            id_="dec-1",
            title="Use BDD",
            value={"policy": "require BDD"},
            status=DecisionStatus.SUPERSEDED,
        )
    ]
    profile = _make_profile(test_frameworks=["pytest"])

    conflicts = detect_conflicts(decisions, profile)

    assert conflicts == []


def test_detect_conflicts_bdd_decision_task_local_no_conflict() -> None:
    """BDD decision with task_local scope -> no conflict (even if no BDD framework)."""
    decisions = [
        _make_decision(
            id_="dec-1",
            title="Use BDD",
            value={"policy": "require BDD"},
            decision_scope=DecisionScope.TASK_LOCAL,
        )
    ]
    profile = _make_profile(test_frameworks=["pytest"])

    conflicts = detect_conflicts(decisions, profile)

    assert conflicts == []


# ============================================================================
# Test detect_conflicts - Test Case 3: User vs User conflicts
# ============================================================================


def test_detect_conflicts_two_active_decisions_same_title_different_values_conflict() -> None:
    """Two active decisions with same title but different values -> USER_VS_USER conflict."""
    decisions = [
        _make_decision(
            id_="dec-1",
            title="Test Framework",
            value={"framework": "pytest"},
            updated_at="2024-01-01T00:00:00Z",
        ),
        _make_decision(
            id_="dec-2",
            title="Test Framework",
            value={"framework": "unittest"},
            updated_at="2024-01-02T00:00:00Z",
        ),
    ]
    profile = _make_profile()

    conflicts = detect_conflicts(decisions, profile)

    assert len(conflicts) == 1
    assert conflicts[0].type == ConflictType.USER_VS_USER
    assert conflicts[0].decision_id == "dec-2"  # Most recent
    assert conflicts[0].status == ConflictStatus.UNRESOLVED
    assert len(conflicts[0].possible_resolutions) > 0


def test_detect_conflicts_two_active_decisions_same_title_same_values_no_conflict() -> None:
    """Two active decisions with same title AND equal values -> no conflict."""
    decisions = [
        _make_decision(
            id_="dec-1",
            title="Test Framework",
            value={"framework": "pytest"},
        ),
        _make_decision(
            id_="dec-2",
            title="Test Framework",
            value={"framework": "pytest"},
        ),
    ]
    profile = _make_profile()

    conflicts = detect_conflicts(decisions, profile)

    assert conflicts == []


def test_detect_conflicts_multiple_groups_same_title_different_values() -> None:
    """Multiple decisions with same title, at least one group has conflicts."""
    decisions = [
        _make_decision(
            id_="dec-1",
            title="Framework A",
            value={"value": 1},
            updated_at="2024-01-01T00:00:00Z",
        ),
        _make_decision(
            id_="dec-2",
            title="Framework A",
            value={"value": 2},
            updated_at="2024-01-02T00:00:00Z",
        ),
        _make_decision(
            id_="dec-3",
            title="Framework B",
            value={"value": 3},
        ),
    ]
    profile = _make_profile()

    conflicts = detect_conflicts(decisions, profile)

    assert len(conflicts) == 1
    assert conflicts[0].type == ConflictType.USER_VS_USER


def test_detect_conflicts_inactive_decision_ignored_in_user_vs_user() -> None:
    """Inactive decisions are not considered in USER_VS_USER detection."""
    decisions = [
        _make_decision(
            id_="dec-1",
            title="Test Framework",
            value={"framework": "pytest"},
            status=DecisionStatus.SUPERSEDED,
        ),
        _make_decision(
            id_="dec-2",
            title="Test Framework",
            value={"framework": "unittest"},
        ),
    ]
    profile = _make_profile()

    conflicts = detect_conflicts(decisions, profile)

    assert conflicts == []


# ============================================================================
# Test detect_conflicts - Test Case 4: Tool policy vs availability
# ============================================================================


def test_detect_conflicts_mandatory_tool_not_in_profile_raises_conflict() -> None:
    """Decision requires tool that doesn't exist in profile -> TOOL_POLICY_VS_AVAILABILITY."""
    decisions = [
        _make_decision(
            id_="dec-1",
            title="Tool Policy",
            value={"mandatory_tools": ["mytool"]},
        )
    ]
    profile = _make_profile(tools=[])

    conflicts = detect_conflicts(decisions, profile)

    assert len(conflicts) == 1
    assert conflicts[0].type == ConflictType.TOOL_POLICY_VS_AVAILABILITY
    assert conflicts[0].decision_id == "dec-1"
    assert conflicts[0].status == ConflictStatus.UNRESOLVED
    assert len(conflicts[0].possible_resolutions) > 0


def test_detect_conflicts_mandatory_tool_unavailable_raises_conflict() -> None:
    """Decision requires tool with availability='unavailable' -> TOOL_POLICY_VS_AVAILABILITY."""
    decisions = [
        _make_decision(
            id_="dec-1",
            title="Tool Policy",
            value={"mandatory_tools": ["mytool"]},
        )
    ]
    profile = _make_profile(
        tools=[ToolDefinition(id="mytool", availability="unavailable", source="detected")]
    )

    conflicts = detect_conflicts(decisions, profile)

    assert len(conflicts) == 1
    assert conflicts[0].type == ConflictType.TOOL_POLICY_VS_AVAILABILITY


def test_detect_conflicts_mandatory_tool_available_no_conflict() -> None:
    """Decision requires tool with availability='available' -> no conflict."""
    decisions = [
        _make_decision(
            id_="dec-1",
            title="Tool Policy",
            value={"mandatory_tools": ["mytool"]},
        )
    ]
    profile = _make_profile(
        tools=[ToolDefinition(id="mytool", availability="available", source="detected")]
    )

    conflicts = detect_conflicts(decisions, profile)

    assert conflicts == []


def test_detect_conflicts_multiple_mandatory_tools_one_unavailable() -> None:
    """Multiple mandatory tools where one is unavailable -> one TOOL_POLICY_VS_AVAILABILITY."""
    decisions = [
        _make_decision(
            id_="dec-1",
            title="Tool Policy",
            value={"mandatory_tools": ["tool-a", "tool-b"]},
        )
    ]
    profile = _make_profile(
        tools=[
            ToolDefinition(id="tool-a", availability="available", source="detected"),
            ToolDefinition(id="tool-b", availability="unavailable", source="detected"),
        ]
    )

    conflicts = detect_conflicts(decisions, profile)

    assert len(conflicts) == 1
    assert conflicts[0].type == ConflictType.TOOL_POLICY_VS_AVAILABILITY


def test_detect_conflicts_no_mandatory_tools_key_no_conflict() -> None:
    """Decision without 'mandatory_tools' key -> no tool conflict."""
    decisions = [
        _make_decision(
            id_="dec-1",
            title="Tool Policy",
            value={"other_policy": "value"},
        )
    ]
    profile = _make_profile()

    conflicts = detect_conflicts(decisions, profile)

    assert conflicts == []


def test_detect_conflicts_empty_mandatory_tools_list_no_conflict() -> None:
    """Decision with empty 'mandatory_tools' list -> no conflict."""
    decisions = [
        _make_decision(
            id_="dec-1",
            title="Tool Policy",
            value={"mandatory_tools": []},
        )
    ]
    profile = _make_profile()

    conflicts = detect_conflicts(decisions, profile)

    assert conflicts == []


def test_detect_conflicts_mandatory_tools_not_list_no_conflict() -> None:
    """Decision where mandatory_tools is not a list -> no conflict (edge case)."""
    decisions = [
        _make_decision(
            id_="dec-1",
            title="Tool Policy",
            value={"mandatory_tools": "not-a-list"},
        )
    ]
    profile = _make_profile()

    conflicts = detect_conflicts(decisions, profile)

    assert conflicts == []


# ============================================================================
# Test detect_conflicts - Test Case 5: Conflict properties
# ============================================================================


def test_detect_conflicts_all_conflicts_have_unresolved_status() -> None:
    """Every conflict has status=UNRESOLVED."""
    decisions = [
        _make_decision(
            id_="dec-1",
            title="BDD Policy",
            value={"policy": "require BDD"},
        ),
        _make_decision(
            id_="dec-2",
            title="Tool Policy",
            value={"mandatory_tools": ["unavailable-tool"]},
        ),
    ]
    profile = _make_profile(
        test_frameworks=["pytest"],
        tools=[
            ToolDefinition(id="unavailable-tool", availability="unavailable", source="detected")
        ],
    )

    conflicts = detect_conflicts(decisions, profile)

    for conflict in conflicts:
        assert conflict.status == ConflictStatus.UNRESOLVED


def test_detect_conflicts_all_conflicts_have_non_empty_resolutions() -> None:
    """Every conflict has non-empty possible_resolutions list."""
    decisions = [
        _make_decision(
            id_="dec-1",
            title="BDD Policy",
            value={"policy": "require BDD"},
        ),
        _make_decision(
            id_="dec-2",
            title="Tool Policy",
            value={"mandatory_tools": ["unavailable-tool"]},
        ),
    ]
    profile = _make_profile(
        test_frameworks=["pytest"],
        tools=[
            ToolDefinition(id="unavailable-tool", availability="unavailable", source="detected")
        ],
    )

    conflicts = detect_conflicts(decisions, profile)

    for conflict in conflicts:
        assert len(conflict.possible_resolutions) > 0


def test_detect_conflicts_all_conflicts_have_unique_ids() -> None:
    """Every conflict has a unique id."""
    decisions = [
        _make_decision(
            id_="dec-1",
            title="BDD Policy",
            value={"policy": "require BDD"},
        ),
        _make_decision(
            id_="dec-2",
            title="Tool Policy 1",
            value={"mandatory_tools": ["tool-a"]},
        ),
        _make_decision(
            id_="dec-3",
            title="Tool Policy 2",
            value={"mandatory_tools": ["tool-b"]},
        ),
    ]
    profile = _make_profile(
        test_frameworks=["pytest"],
        tools=[
            ToolDefinition(id="tool-a", availability="unavailable", source="detected"),
            ToolDefinition(id="tool-b", availability="unavailable", source="detected"),
        ],
    )

    conflicts = detect_conflicts(decisions, profile)

    ids = [c.id for c in conflicts]
    assert len(ids) == len(set(ids))
    assert ids == ["conflict-0", "conflict-1", "conflict-2"]


def test_detect_conflicts_resolution_property_is_none() -> None:
    """Every conflict's resolution property is initially None."""
    decisions = [
        _make_decision(
            id_="dec-1",
            title="BDD Policy",
            value={"policy": "require BDD"},
        )
    ]
    profile = _make_profile(test_frameworks=["pytest"])

    conflicts = detect_conflicts(decisions, profile)

    for conflict in conflicts:
        assert conflict.resolution is None


# ============================================================================
# Test resolve_conflict - Test Case 6: Successful resolution
# ============================================================================


def test_resolve_conflict_with_valid_resolution_returns_resolved() -> None:
    """Resolving with valid resolution -> new ConflictRecord with RESOLVED status."""
    conflict = ConflictRecord(
        id="conflict-0",
        type=ConflictType.USER_VS_REPOSITORY,
        decision_id="dec-1",
        evidence=["test"],
        severity=ConflictSeverity.MEDIUM,
        status=ConflictStatus.UNRESOLVED,
        possible_resolutions=["resolution-1", "resolution-2"],
        resolution=None,
    )

    resolved = resolve_conflict(conflict, "resolution-1")

    assert resolved.status == ConflictStatus.RESOLVED
    assert resolved.resolution == "resolution-1"
    assert resolved.id == "conflict-0"
    assert resolved.type == ConflictType.USER_VS_REPOSITORY


def test_resolve_conflict_returns_new_object_immutability() -> None:
    """Resolving conflict returns new object; original is unchanged (immutability)."""
    conflict = ConflictRecord(
        id="conflict-0",
        type=ConflictType.USER_VS_REPOSITORY,
        decision_id="dec-1",
        evidence=["test"],
        severity=ConflictSeverity.MEDIUM,
        status=ConflictStatus.UNRESOLVED,
        possible_resolutions=["resolution-1"],
        resolution=None,
    )

    resolved = resolve_conflict(conflict, "resolution-1")

    # Original conflict should still be UNRESOLVED and resolution should be None
    assert conflict.status == ConflictStatus.UNRESOLVED
    assert conflict.resolution is None
    # New object should be RESOLVED
    assert resolved.status == ConflictStatus.RESOLVED
    assert resolved.resolution == "resolution-1"


def test_resolve_conflict_preserves_other_fields() -> None:
    """Resolving conflict preserves all other fields from the original."""
    conflict = ConflictRecord(
        id="conflict-42",
        type=ConflictType.TOOL_POLICY_VS_AVAILABILITY,
        decision_id="dec-xyz",
        evidence=["evidence-1", "evidence-2"],
        severity=ConflictSeverity.HIGH,
        status=ConflictStatus.UNRESOLVED,
        possible_resolutions=["fix-1", "fix-2"],
        resolution=None,
    )

    resolved = resolve_conflict(conflict, "fix-1")

    assert resolved.id == "conflict-42"
    assert resolved.type == ConflictType.TOOL_POLICY_VS_AVAILABILITY
    assert resolved.decision_id == "dec-xyz"
    assert resolved.evidence == ["evidence-1", "evidence-2"]
    assert resolved.severity == ConflictSeverity.HIGH
    assert resolved.possible_resolutions == ["fix-1", "fix-2"]


# ============================================================================
# Test resolve_conflict - Test Case 7: Error handling
# ============================================================================


def test_resolve_conflict_invalid_resolution_raises_valueerror() -> None:
    """Resolving with invalid resolution -> raises ValueError."""
    conflict = ConflictRecord(
        id="conflict-0",
        type=ConflictType.USER_VS_REPOSITORY,
        decision_id="dec-1",
        evidence=["test"],
        severity=ConflictSeverity.MEDIUM,
        status=ConflictStatus.UNRESOLVED,
        possible_resolutions=["resolution-1", "resolution-2"],
        resolution=None,
    )

    with pytest.raises(ValueError) as exc_info:
        resolve_conflict(conflict, "invalid-resolution")

    assert "invalid-resolution" in str(exc_info.value)
    assert "conflict-0" in str(exc_info.value)


def test_resolve_conflict_empty_resolution_string_raises_valueerror() -> None:
    """Resolving with empty string -> raises ValueError (if not in possible_resolutions)."""
    conflict = ConflictRecord(
        id="conflict-0",
        type=ConflictType.USER_VS_REPOSITORY,
        decision_id="dec-1",
        evidence=["test"],
        severity=ConflictSeverity.MEDIUM,
        status=ConflictStatus.UNRESOLVED,
        possible_resolutions=["resolution-1"],
        resolution=None,
    )

    with pytest.raises(ValueError):
        resolve_conflict(conflict, "")


# ============================================================================
# Integration tests: Multiple conflicts detected and resolved
# ============================================================================


def test_detect_and_resolve_multiple_conflicts() -> None:
    """Detect multiple conflicts and resolve some of them."""
    decisions = [
        _make_decision(
            id_="dec-1",
            title="BDD Policy",
            value={"policy": "require BDD"},
        ),
        _make_decision(
            id_="dec-2",
            title="Tool Policy",
            value={"mandatory_tools": ["unavailable-tool"]},
        ),
    ]
    profile = _make_profile(
        test_frameworks=["pytest"],
        tools=[
            ToolDefinition(id="unavailable-tool", availability="unavailable", source="detected")
        ],
    )

    conflicts = detect_conflicts(decisions, profile)
    assert len(conflicts) == 2

    # Resolve first conflict
    resolved_1 = resolve_conflict(conflicts[0], conflicts[0].possible_resolutions[0])
    assert resolved_1.status == ConflictStatus.RESOLVED

    # Resolve second conflict
    resolved_2 = resolve_conflict(conflicts[1], conflicts[1].possible_resolutions[0])
    assert resolved_2.status == ConflictStatus.RESOLVED

    # Original conflicts unchanged
    assert conflicts[0].status == ConflictStatus.UNRESOLVED
    assert conflicts[1].status == ConflictStatus.UNRESOLVED

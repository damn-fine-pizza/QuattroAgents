"""Tests for knowledge gap detection in the Interview Engine.

Tests cover detect_knowledge_gaps() and find_stale_decisions() with specific
scenarios for missing test policies, autonomy decisions, legacy areas, language
prioritization, tool policies, and stale subsystem references.
"""

from datetime import datetime

from quattroagents.domain import (
    Decision,
    DecisionSource,
    DecisionSourceType,
    DecisionStatus,
    GapStatus,
    GapType,
    ProjectProfile,
    ToolDefinition,
)
from quattroagents.interview.gaps import detect_knowledge_gaps, find_stale_decisions


def test_detect_knowledge_gaps_empty_profile_produces_core_gaps() -> None:
    """Empty/minimal ProjectProfile produces missing-test-policy and agent-autonomy-level gaps."""
    profile = ProjectProfile(fingerprint="test")
    active_decisions = []

    gaps = detect_knowledge_gaps(profile, active_decisions)

    gap_ids = {gap.id for gap in gaps}
    assert "missing-test-policy" in gap_ids
    assert "agent-autonomy-level" in gap_ids
    # Should not have these for empty profile
    assert "duplicate-implementation" not in gap_ids
    assert "legacy-area-ownership" not in gap_ids


def test_detect_knowledge_gaps_duplicate_risk_produces_ambiguous_architecture_gap() -> None:
    """A risk starting with "duplicate implementation name" produces AMBIGUOUS_ARCHITECTURE gap."""
    risk_text = "duplicate implementation name detected in payment_processor"
    profile = ProjectProfile(fingerprint="test", risks=[risk_text])
    active_decisions = []

    gaps = detect_knowledge_gaps(profile, active_decisions)

    ambiguous_gaps = [g for g in gaps if g.gap_type == GapType.AMBIGUOUS_ARCHITECTURE]
    assert len(ambiguous_gaps) > 0
    gap = ambiguous_gaps[0]
    assert risk_text in gap.evidence


def test_detect_knowledge_gaps_legacy_areas_produces_single_gap() -> None:
    """Non-empty legacy_areas produces exactly one legacy-area-ownership gap."""
    profile = ProjectProfile(
        fingerprint="test",
        legacy_areas=["src/old_api.py", "src/deprecated_utils.py", "lib/legacy.py"],
    )
    active_decisions = []

    gaps = detect_knowledge_gaps(profile, active_decisions)

    legacy_gaps = [g for g in gaps if g.id == "legacy-area-ownership"]
    assert len(legacy_gaps) == 1
    gap = legacy_gaps[0]
    assert gap.gap_type == GapType.MISSING_OWNERSHIP


def test_detect_knowledge_gaps_test_frameworks_suppresses_test_policy_gap() -> None:
    """Non-empty test_frameworks suppresses the missing-test-policy gap."""
    profile = ProjectProfile(fingerprint="test", test_frameworks=["pytest"])
    active_decisions = []

    gaps = detect_knowledge_gaps(profile, active_decisions)

    gap_ids = {gap.id for gap in gaps}
    assert "missing-test-policy" not in gap_ids


def test_detect_knowledge_gaps_single_language_no_priority_gap() -> None:
    """A single language does not produce multi-language-priority gap."""
    profile = ProjectProfile(fingerprint="test", languages=["python"])
    active_decisions = []

    gaps = detect_knowledge_gaps(profile, active_decisions)

    gap_ids = {gap.id for gap in gaps}
    assert "multi-language-priority" not in gap_ids


def test_detect_knowledge_gaps_no_languages_no_priority_gap() -> None:
    """Zero languages do not produce multi-language-priority gap."""
    profile = ProjectProfile(fingerprint="test", languages=[])
    active_decisions = []

    gaps = detect_knowledge_gaps(profile, active_decisions)

    gap_ids = {gap.id for gap in gaps}
    assert "multi-language-priority" not in gap_ids


def test_detect_knowledge_gaps_multiple_languages_produces_priority_gap() -> None:
    """2+ languages produces multi-language-priority gap listing them in evidence."""
    profile = ProjectProfile(fingerprint="test", languages=["python", "typescript"])
    active_decisions = []

    gaps = detect_knowledge_gaps(profile, active_decisions)

    priority_gaps = [g for g in gaps if g.id == "multi-language-priority"]
    assert len(priority_gaps) == 1
    gap = priority_gaps[0]
    assert gap.gap_type == GapType.MISSING_PRIORITY
    assert "python" in gap.evidence
    assert "typescript" in gap.evidence


def test_detect_knowledge_gaps_rtk_unavailable_produces_tool_policy_gap() -> None:
    """A ToolDefinition for 'rtk' with availability='unavailable' produces tool-policy-rtk gap."""
    rtk_tool = ToolDefinition(
        id="rtk",
        availability="unavailable",
        source="cli",
    )
    profile = ProjectProfile(fingerprint="test", tools=[rtk_tool])
    active_decisions = []

    gaps = detect_knowledge_gaps(profile, active_decisions)

    tool_gaps = [g for g in gaps if g.id == "tool-policy-rtk"]
    assert len(tool_gaps) == 1
    gap = tool_gaps[0]
    assert gap.gap_type == GapType.MISSING_TOOL_POLICY


def test_detect_knowledge_gaps_rtk_available_no_tool_policy_gap() -> None:
    """A ToolDefinition for 'rtk' with availability='available' produces no tool-policy-rtk gap."""
    rtk_tool = ToolDefinition(
        id="rtk",
        availability="available",
        source="cli",
    )
    profile = ProjectProfile(fingerprint="test", tools=[rtk_tool])
    active_decisions = []

    gaps = detect_knowledge_gaps(profile, active_decisions)

    gap_ids = {gap.id for gap in gaps}
    assert "tool-policy-rtk" not in gap_ids


def test_detect_knowledge_gaps_autonomy_decision_suppresses_autonomy_gap() -> None:
    """An active decision with 'autonomy' in title suppresses agent-autonomy-level gap."""
    decision = Decision(
        id="autonomy-001",
        title="Agent autonomy level for code modifications",
        value={"autonomy": "write"},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Agents should be able to modify code directly",
        status=DecisionStatus.ACTIVE,
    )
    profile = ProjectProfile(fingerprint="test")
    active_decisions = [decision]

    gaps = detect_knowledge_gaps(profile, active_decisions)

    gap_ids = {gap.id for gap in gaps}
    assert "agent-autonomy-level" not in gap_ids


def test_detect_knowledge_gaps_write_permission_decision_suppresses_autonomy_gap() -> None:
    """An active decision with 'write permission' in title suppresses agent-autonomy-level gap."""
    decision = Decision(
        id="perm-001",
        title="Write permission policy for agents",
        value={"permission": "allow"},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Agents may write to certain paths",
        status=DecisionStatus.ACTIVE,
    )
    profile = ProjectProfile(fingerprint="test")
    active_decisions = [decision]

    gaps = detect_knowledge_gaps(profile, active_decisions)

    gap_ids = {gap.id for gap in gaps}
    assert "agent-autonomy-level" not in gap_ids


def test_detect_knowledge_gaps_case_insensitive_autonomy_match() -> None:
    """Autonomy decision matching is case-insensitive."""
    decision = Decision(
        id="autonomy-001",
        title="AGENT AUTONOMY LEVEL Requirements",
        value={"autonomy": "write"},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Test case insensitivity",
        status=DecisionStatus.ACTIVE,
    )
    profile = ProjectProfile(fingerprint="test")
    active_decisions = [decision]

    gaps = detect_knowledge_gaps(profile, active_decisions)

    gap_ids = {gap.id for gap in gaps}
    assert "agent-autonomy-level" not in gap_ids


def test_detect_knowledge_gaps_all_gaps_have_open_status() -> None:
    """Every returned gap has status=GapStatus.OPEN."""
    profile = ProjectProfile(
        fingerprint="test",
        languages=["python", "js"],
        risks=["duplicate implementation name in auth"],
        legacy_areas=["old.py"],
    )
    active_decisions = []

    gaps = detect_knowledge_gaps(profile, active_decisions)

    for gap in gaps:
        assert gap.status == GapStatus.OPEN


def test_detect_knowledge_gaps_all_gaps_have_non_empty_timestamps() -> None:
    """Every returned gap has non-empty created_at and updated_at."""
    profile = ProjectProfile(
        fingerprint="test",
        languages=["python", "js"],
    )
    active_decisions = []

    gaps = detect_knowledge_gaps(profile, active_decisions)

    for gap in gaps:
        assert gap.created_at, "created_at should not be empty"
        assert gap.updated_at, "updated_at should not be empty"
        # Verify they're valid ISO format timestamps
        datetime.fromisoformat(gap.created_at.replace("Z", "+00:00"))
        datetime.fromisoformat(gap.updated_at.replace("Z", "+00:00"))


def test_detect_knowledge_gaps_all_gaps_have_non_empty_id() -> None:
    """Every returned gap has a non-empty id."""
    profile = ProjectProfile(
        fingerprint="test",
        languages=["python", "js"],
        risks=["duplicate implementation name"],
    )
    active_decisions = []

    gaps = detect_knowledge_gaps(profile, active_decisions)

    for gap in gaps:
        assert gap.id, "id should not be empty"
        assert isinstance(gap.id, str)
        assert len(gap.id) > 0


def test_find_stale_decisions_active_with_missing_subsystem() -> None:
    """An ACTIVE decision whose scope_paths reference a missing subsystem produces STALE_DECISION gap."""
    decision = Decision(
        id="dec-001",
        title="Legacy auth system handling",
        value={"action": "preserve"},
        source=DecisionSource(type=DecisionSourceType.REPOSITORY),
        reason="Legacy system still in use",
        scope_paths=["auth_system"],  # This subsystem doesn't exist
        status=DecisionStatus.ACTIVE,
    )
    profile = ProjectProfile(
        fingerprint="test",
        subsystems=["api", "core", "storage"],  # auth_system is NOT here
    )
    active_decisions = [decision]

    gaps = find_stale_decisions(active_decisions, profile)

    assert len(gaps) > 0
    gap = gaps[0]
    assert gap.id == f"stale-{decision.id}"
    assert gap.gap_type == GapType.STALE_DECISION


def test_find_stale_decisions_active_with_existing_subsystem() -> None:
    """A decision whose scope_paths subsystem IS in profile.subsystems produces no stale gap."""
    decision = Decision(
        id="dec-001",
        title="API versioning policy",
        value={"version": "v2"},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Support multiple API versions",
        scope_paths=["api"],  # This subsystem exists
        status=DecisionStatus.ACTIVE,
    )
    profile = ProjectProfile(
        fingerprint="test",
        subsystems=["api", "core", "storage"],  # api IS here
    )
    active_decisions = [decision]

    gaps = find_stale_decisions(active_decisions, profile)

    assert len(gaps) == 0


def test_find_stale_decisions_multiple_subsystems_one_missing() -> None:
    """A decision with multiple scope_paths where one is missing produces a stale gap."""
    decision = Decision(
        id="dec-002",
        title="Cross-system logging",
        value={"logging": "centralized"},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Unified logging across systems",
        scope_paths=["api", "defunct_module"],  # defunct_module is missing
        status=DecisionStatus.ACTIVE,
    )
    profile = ProjectProfile(
        fingerprint="test",
        subsystems=["api", "core", "storage"],
    )
    active_decisions = [decision]

    gaps = find_stale_decisions(active_decisions, profile)

    assert len(gaps) > 0
    gap = gaps[0]
    assert gap.gap_type == GapType.STALE_DECISION


def test_find_stale_decisions_ignores_non_active_decisions() -> None:
    """Non-ACTIVE decisions are ignored even if their subsystems are missing."""
    decision = Decision(
        id="dec-003",
        title="Old system handling",
        value={"action": "ignore"},
        source=DecisionSource(type=DecisionSourceType.REPOSITORY),
        reason="Superseded",
        scope_paths=["missing_subsystem"],
        status=DecisionStatus.SUPERSEDED,  # Not ACTIVE
    )
    profile = ProjectProfile(
        fingerprint="test",
        subsystems=["api", "core"],
    )
    active_decisions = [decision]

    gaps = find_stale_decisions(active_decisions, profile)

    assert len(gaps) == 0


def test_find_stale_decisions_one_gap_per_decision() -> None:
    """Only one gap is generated per decision, even with multiple missing subsystems."""
    decision = Decision(
        id="dec-004",
        title="Multi-subsystem policy",
        value={"policy": "unified"},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Apply to multiple subsystems",
        scope_paths=["missing1", "missing2", "missing3"],
        status=DecisionStatus.ACTIVE,
    )
    profile = ProjectProfile(
        fingerprint="test",
        subsystems=["api", "core"],
    )
    active_decisions = [decision]

    gaps = find_stale_decisions(active_decisions, profile)

    # Should have exactly one gap, not three
    assert len(gaps) == 1
    gap = gaps[0]
    assert gap.id == f"stale-{decision.id}"


def test_find_stale_decisions_all_gaps_have_open_status() -> None:
    """Every stale decision gap has status=GapStatus.OPEN."""
    decision1 = Decision(
        id="dec-005",
        title="Old auth",
        value={},
        source=DecisionSource(type=DecisionSourceType.REPOSITORY),
        reason="",
        scope_paths=["old_auth"],
        status=DecisionStatus.ACTIVE,
    )
    decision2 = Decision(
        id="dec-006",
        title="Missing payment",
        value={},
        source=DecisionSource(type=DecisionSourceType.REPOSITORY),
        reason="",
        scope_paths=["payment"],
        status=DecisionStatus.ACTIVE,
    )
    profile = ProjectProfile(
        fingerprint="test",
        subsystems=["api"],  # None of the scope_paths exist
    )
    active_decisions = [decision1, decision2]

    gaps = find_stale_decisions(active_decisions, profile)

    for gap in gaps:
        assert gap.status == GapStatus.OPEN


def test_find_stale_decisions_all_gaps_have_non_empty_timestamps() -> None:
    """Every stale decision gap has non-empty created_at and updated_at."""
    decision = Decision(
        id="dec-007",
        title="Stale subsystem",
        value={},
        source=DecisionSource(type=DecisionSourceType.REPOSITORY),
        reason="",
        scope_paths=["nonexistent"],
        status=DecisionStatus.ACTIVE,
    )
    profile = ProjectProfile(
        fingerprint="test",
        subsystems=["api"],
    )
    active_decisions = [decision]

    gaps = find_stale_decisions(active_decisions, profile)

    for gap in gaps:
        assert gap.created_at, "created_at should not be empty"
        assert gap.updated_at, "updated_at should not be empty"
        # Verify they're valid ISO format timestamps
        datetime.fromisoformat(gap.created_at.replace("Z", "+00:00"))
        datetime.fromisoformat(gap.updated_at.replace("Z", "+00:00"))


def test_find_stale_decisions_multiple_decisions_mixed_active_status() -> None:
    """Multiple decisions are checked; only ACTIVE ones generate stale gaps."""
    active_stale = Decision(
        id="active-stale",
        title="Active but stale",
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="",
        scope_paths=["gone"],
        status=DecisionStatus.ACTIVE,
    )
    superseded_stale = Decision(
        id="superseded-stale",
        title="Superseded but stale",
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="",
        scope_paths=["also_gone"],
        status=DecisionStatus.SUPERSEDED,
    )
    active_valid = Decision(
        id="active-valid",
        title="Active and valid",
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="",
        scope_paths=["api"],
        status=DecisionStatus.ACTIVE,
    )
    profile = ProjectProfile(
        fingerprint="test",
        subsystems=["api"],
    )
    active_decisions = [active_stale, superseded_stale, active_valid]

    gaps = find_stale_decisions(active_decisions, profile)

    # Only one gap: from active_stale
    assert len(gaps) == 1
    assert gaps[0].id == "stale-active-stale"


def test_detect_knowledge_gaps_deterministic_timestamps() -> None:
    """Timestamps within a single call are the same (computed once)."""
    profile = ProjectProfile(
        fingerprint="test",
        languages=["python", "js"],
    )
    active_decisions = []

    gaps = detect_knowledge_gaps(profile, active_decisions)

    # All gaps should have the same created_at and updated_at
    first_created = gaps[0].created_at if gaps else None
    first_updated = gaps[0].updated_at if gaps else None

    for gap in gaps:
        assert gap.created_at == first_created
        assert gap.updated_at == first_updated

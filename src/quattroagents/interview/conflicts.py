"""Conflict detection and resolution for the Interview Engine.

Identifies contradictions between user decisions and repository evidence,
between concurrent decisions, and between tool policies and availability.
"""

from __future__ import annotations

import dataclasses

from quattroagents.domain import (
    ConflictRecord,
    ConflictSeverity,
    ConflictStatus,
    ConflictType,
    Decision,
    DecisionScope,
    DecisionStatus,
    ProjectProfile,
)


def detect_conflicts(decisions: list[Decision], profile: ProjectProfile) -> list[ConflictRecord]:
    """Detect conflicts between decisions and repository evidence.

    Checks for:
    1. User answer vs. repository evidence (BDD policy vs. test framework availability)
    2. Conflicting active decisions with the same title but different values
    3. Tool policies requiring unavailable tools

    Args:
        decisions: List of decisions to check.
        profile: Project profile containing repository analysis.

    Returns:
        List of ConflictRecords, each with a unique id like "conflict-0", "conflict-1", etc.
    """
    conflicts: list[ConflictRecord] = []
    _next_id = 0

    # Check 1: User answer vs. repository evidence (BDD scenario)
    for decision in decisions:
        if (
            decision.status == DecisionStatus.ACTIVE
            and decision.decision_scope == DecisionScope.PROJECT_WIDE
            and "require" in str(decision.value).lower()
            and "bdd" in str(decision.value).lower()
        ):
            # Check if any test framework matches BDD/Gherkin/Cucumber/Behave
            bdd_frameworks = {"gherkin", "cucumber", "behave"}
            has_bdd_framework = any(
                any(bdd_keyword in framework.lower() for bdd_keyword in bdd_frameworks)
                for framework in profile.test_frameworks
            )

            if not has_bdd_framework:
                conflicts.append(
                    ConflictRecord(
                        id=f"conflict-{_next_id}",
                        type=ConflictType.USER_VS_REPOSITORY,
                        decision_id=decision.id,
                        evidence=[
                            f"Decision requires BDD scenarios: {decision.title}",
                            "No BDD/Gherkin test runner detected in the repository",
                        ],
                        severity=ConflictSeverity.MEDIUM,
                        status=ConflictStatus.UNRESOLVED,
                        possible_resolutions=[
                            "generate the skill and BDD tooling configuration",
                            "make the policy advisory only",
                            "postpone enforcement of this policy",
                        ],
                        resolution=None,
                    )
                )
                _next_id += 1

    # Check 2: Two active decisions with the same title but different value
    decisions_by_title: dict[str, list[Decision]] = {}
    for decision in decisions:
        if decision.status == DecisionStatus.ACTIVE:
            if decision.title not in decisions_by_title:
                decisions_by_title[decision.title] = []
            decisions_by_title[decision.title].append(decision)

    for _title, group in decisions_by_title.items():
        if len(group) >= 2:
            # Check if any two decisions in the group have different values
            first_value = group[0].value
            if any(d.value != first_value for d in group[1:]):
                # Find the most recently updated decision
                most_recent = max(group, key=lambda d: d.updated_at)
                conflicts.append(
                    ConflictRecord(
                        id=f"conflict-{_next_id}",
                        type=ConflictType.USER_VS_USER,
                        decision_id=most_recent.id,
                        evidence=[f"{d.id}: {d.value}" for d in group],
                        severity=ConflictSeverity.HIGH,
                        status=ConflictStatus.UNRESOLVED,
                        possible_resolutions=[
                            "keep the most recent decision and supersede the others",
                            "ask the user to explicitly reconcile them",
                        ],
                        resolution=None,
                    )
                )
                _next_id += 1

    # Check 3: Tool policy vs. availability
    tool_availability_map: dict[str, str] = {t.id: t.availability for t in profile.tools}

    for decision in decisions:
        if "mandatory_tools" in decision.value:
            mandatory_tools = decision.value.get("mandatory_tools")
            if isinstance(mandatory_tools, list) and len(mandatory_tools) > 0:
                for tool_id in mandatory_tools:
                    tool_availability = tool_availability_map.get(tool_id)
                    if tool_availability is None or tool_availability == "unavailable":
                        conflicts.append(
                            ConflictRecord(
                                id=f"conflict-{_next_id}",
                                type=ConflictType.TOOL_POLICY_VS_AVAILABILITY,
                                decision_id=decision.id,
                                evidence=[
                                    f"Decision '{decision.title}' requires tool '{tool_id}'",
                                    f"'{tool_id}' is not available in this environment",
                                ],
                                severity=ConflictSeverity.MEDIUM,
                                status=ConflictStatus.UNRESOLVED,
                                possible_resolutions=[
                                    "remove the tool from the mandatory list",
                                    "mark the affected agent as blocked until the tool is installed",
                                    "treat the requirement as advisory",
                                ],
                                resolution=None,
                            )
                        )
                        _next_id += 1

    return conflicts


def resolve_conflict(conflict: ConflictRecord, resolution: str) -> ConflictRecord:
    """Resolve a conflict by choosing one of its possible resolutions.

    Args:
        conflict: The conflict to resolve.
        resolution: One of the resolutions from conflict.possible_resolutions.

    Returns:
        A new ConflictRecord with status=RESOLVED and the chosen resolution.

    Raises:
        ValueError: If resolution is not in conflict.possible_resolutions.
    """
    if resolution not in conflict.possible_resolutions:
        raise ValueError(
            f"'{resolution}' is not one of the possible resolutions for conflict '{conflict.id}'"
        )

    return dataclasses.replace(
        conflict,
        status=ConflictStatus.RESOLVED,
        resolution=resolution,
    )

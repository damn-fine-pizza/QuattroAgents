"""Agent selection logic for the Project Agent Factory.

Selects which archetypes (see `archetypes.py`) apply to a given project
profile and decision set, and instantiates both the Haiku and Sonnet tier
variant of each selected archetype.
"""

from __future__ import annotations

import copy

from ..domain import (
    AgentDefinition,
    Decision,
    DecisionStatus,
    DefinitionSource,
    ProjectProfile,
)
from .archetypes import ARCHETYPES


def select_agents(profile: ProjectProfile, decisions: list[Decision]) -> list[AgentDefinition]:
    """Select archetypes for a project and instantiate both tier variants of each.

    Args:
        profile: Project profile describing the codebase structure and tools.
        decisions: List of active decisions affecting agent selection.

    Returns:
        Sorted list of AgentDefinition instances (Haiku + Sonnet variant of
        every selected archetype) configured for the project.
    """
    selected_archetype_ids: set[str] = set()

    # Rule 1: Always include core archetypes
    selected_archetype_ids.update(
        ["project-orchestrator", "repository-cartographer", "code-reviewer"]
    )

    # Rule 2: Include architecture-guardian if conditions met
    if len(profile.subsystems) >= 3 or profile.risks or profile.legacy_areas:
        selected_archetype_ids.add("architecture-guardian")

    # Rule 3: Always include implementation-agent
    selected_archetype_ids.add("implementation-agent")

    # Rule 4: Include test-agent if test frameworks exist
    if profile.test_frameworks:
        selected_archetype_ids.add("test-agent")

    # Rule 5: Always include documentation-agent (always safe to include)
    selected_archetype_ids.add("documentation-agent")

    # Rule 6: Include dependency-agent if build systems exist
    if profile.build_systems:
        selected_archetype_ids.add("dependency-agent")

    # Rule 7: Include ci-build-agent if CI systems exist
    if profile.ci_systems:
        selected_archetype_ids.add("ci-build-agent")

    # Rule 8: Include bdd-feature-agent if "bdd" or "gherkin" in any decision title/value
    for decision in decisions:
        decision_text = f"{decision.title} {str(decision.value)}".lower()
        if "bdd" in decision_text or "gherkin" in decision_text:
            selected_archetype_ids.add("bdd-feature-agent")
            break

    # Rule 9: Include performance-agent if "performance", "realtime", or "real-time" in decision title
    for decision in decisions:
        decision_title = decision.title.lower()
        if (
            "performance" in decision_title
            or "realtime" in decision_title
            or "real-time" in decision_title
        ):
            selected_archetype_ids.add("performance-agent")
            break

    # Rule 10: Include security-reviewer if "security" in decision title
    for decision in decisions:
        if "security" in decision.title.lower():
            selected_archetype_ids.add("security-reviewer")
            break

    # Rule 11: Include release-agent if "release" in decision title
    for decision in decisions:
        if "release" in decision.title.lower():
            selected_archetype_ids.add("release-agent")
            break

    # Deep-copy both tier variants of every selected archetype and apply
    # decision-driven attribute injection, matched by archetype_id so a
    # decision targets both the Haiku and Sonnet variant of a role.
    agents: list[AgentDefinition] = []
    for archetype_id in selected_archetype_ids:
        for variant in ARCHETYPES[archetype_id].values():
            agent = copy.deepcopy(variant)

            for decision in decisions:
                if (
                    decision.status == DecisionStatus.ACTIVE
                    and archetype_id in decision.effects.get("agents", [])
                ):
                    constraint = f"{decision.title}: {decision.reason}"
                    if constraint not in agent.constraints:
                        agent.constraints.append(constraint)

                    if isinstance(decision.value, dict):
                        mandatory_tools = decision.value.get("mandatory_tools", [])
                        if isinstance(mandatory_tools, list):
                            for tool in mandatory_tools:
                                if tool not in agent.mandatory_tools:
                                    agent.mandatory_tools.append(tool)

                    agent.source = DefinitionSource.ADHOC

            agents.append(agent)

    return attach_orchestrator_roster(sorted(agents, key=lambda a: a.id))


def attach_orchestrator_roster(agents: list[AgentDefinition]) -> list[AgentDefinition]:
    """Give every project-orchestrator variant explicit knowledge of every sibling agent.

    Without this, the orchestrator's rendered output only carries generic
    catalog prose and has no idea which agents actually exist in this
    project's generated team, so it can't dispatch work to them by name.

    Args:
        agents: The selected agents for this project (already includes both
            project-orchestrator variants per Rule 1, when present).

    Returns:
        The same list, with every project-orchestrator variant's
        collaboration_notes extended to enumerate every other agent by id
        and description.
    """
    orchestrators = [a for a in agents if a.archetype_id == "project-orchestrator"]
    siblings = [a for a in agents if a.archetype_id != "project-orchestrator"]
    if not orchestrators or not siblings:
        return agents

    roster = "Available agents in this project's generated team:\n" + "\n".join(
        f"- {a.id}: {a.description}" for a in sorted(siblings, key=lambda a: a.id)
    )
    for orchestrator in orchestrators:
        orchestrator.collaboration_notes = (
            f"{orchestrator.collaboration_notes}\n\n{roster}"
            if orchestrator.collaboration_notes
            else roster
        )
    return agents

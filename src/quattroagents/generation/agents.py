"""Agent catalog and selection logic for the Project Agent Factory.

Defines the complete roster of candidate agent roles and a function to
select the appropriate agents for a given project profile and decision set.
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from ..domain import (
    AgentDefinition,
    AgentLifetime,
    AgentMode,
    AgentPermissions,
    Decision,
    DecisionStatus,
    DefinitionSource,
    Model,
    ProjectProfile,
)

# Module-level catalog of all candidate agent roles.
CANDIDATE_ROLES: dict[str, AgentDefinition] = {
    "project-orchestrator": AgentDefinition(
        id="project-orchestrator",
        description="Coordinates discovery, design, implementation, and review phases across the generated agent team.",
        mode=AgentMode.READ_ONLY,
        preferred_model=Model.SONNET,
        permissions=AgentPermissions(can_read_files=True),
        lifetime=AgentLifetime.PERMANENT,
        source=DefinitionSource.DEFAULT,
        responsibilities=[
            "Orchestrate discovery, design, and implementation phases",
            "Coordinate communication between team members",
            "Track progress and manage phase transitions",
        ],
        scope="Entire project lifecycle management",
        when_to_use="At the start of any agent swarm to coordinate work",
        when_not_to_use="Not needed for single-agent or trivial tasks",
        completion_criteria=[
            "All phases completed and reviewed",
            "Handoff to next phase confirmed",
            "Team alignment on deliverables achieved",
        ],
    ),
    "repository-cartographer": AgentDefinition(
        id="repository-cartographer",
        description="Maps repository structure, dependencies, and subsystem boundaries.",
        mode=AgentMode.READ_ONLY,
        preferred_model=Model.HAIKU,
        permissions=AgentPermissions(can_read_files=True),
        lifetime=AgentLifetime.PERMANENT,
        source=DefinitionSource.DEFAULT,
        responsibilities=[
            "Analyze repository structure and layout",
            "Document dependencies and their relationships",
            "Identify subsystem boundaries and interfaces",
        ],
        scope="Repository analysis and mapping",
        when_to_use="During initial project analysis and onboarding",
        when_not_to_use="Not applicable to non-repository work",
        completion_criteria=[
            "Complete repo structure documented",
            "Dependencies mapped and categorized",
            "Subsystem boundaries clearly identified",
        ],
    ),
    "architecture-guardian": AgentDefinition(
        id="architecture-guardian",
        description="Evaluates architectural decisions and cross-component changes.",
        mode=AgentMode.READ_ONLY,
        preferred_model=Model.SONNET,
        permissions=AgentPermissions(can_read_files=True),
        lifetime=AgentLifetime.PERMANENT,
        source=DefinitionSource.DEFAULT,
        responsibilities=[
            "Review architectural implications of changes",
            "Assess cross-component dependencies and impacts",
            "Ensure architectural consistency across system",
        ],
        scope="Architectural decisions and system design",
        when_to_use="When changes affect system architecture or multiple components",
        when_not_to_use="For isolated, single-component changes with no architectural impact",
        completion_criteria=[
            "Design review completed and documented",
            "Cross-component impact assessed",
            "Architectural consistency verified",
        ],
    ),
    "implementation-agent": AgentDefinition(
        id="implementation-agent",
        description="Implements scoped changes within the boundaries set by the orchestrator.",
        mode=AgentMode.WRITE,
        preferred_model=Model.SONNET,
        permissions=AgentPermissions(can_read_files=True, can_write_files=True),
        lifetime=AgentLifetime.PERMANENT,
        source=DefinitionSource.DEFAULT,
        responsibilities=[
            "Implement requested changes and features",
            "Follow established coding standards and patterns",
            "Respect scoping boundaries set by orchestrator",
        ],
        scope="Code implementation within defined scope",
        when_to_use="When code changes or new features need to be implemented",
        when_not_to_use="Not used for review, testing, or release tasks",
        completion_criteria=[
            "Code changes implemented",
            "Changes comply with scope boundaries",
            "Implementation follows established patterns",
        ],
    ),
    "test-agent": AgentDefinition(
        id="test-agent",
        description="Writes and runs automated tests for the requested behavior.",
        mode=AgentMode.WRITE,
        preferred_model=Model.SONNET,
        permissions=AgentPermissions(
            can_read_files=True, can_write_files=True, can_execute_commands=True
        ),
        lifetime=AgentLifetime.PERMANENT,
        source=DefinitionSource.DEFAULT,
        responsibilities=[
            "Write automated test cases covering requested behavior",
            "Execute test suites and validate results",
            "Achieve adequate test coverage",
        ],
        scope="Automated testing and test coverage",
        when_to_use="When automated tests are required for new or modified behavior",
        when_not_to_use="Not used for manual testing or exploratory verification",
        completion_criteria=[
            "Test cases written and documented",
            "All tests passing",
            "Coverage threshold met for new code",
        ],
    ),
    "bdd-feature-agent": AgentDefinition(
        id="bdd-feature-agent",
        description="Writes behavior-driven Gherkin scenarios for user-facing features.",
        mode=AgentMode.WRITE,
        preferred_model=Model.SONNET,
        permissions=AgentPermissions(can_read_files=True, can_write_files=True),
        lifetime=AgentLifetime.PERMANENT,
        source=DefinitionSource.DEFAULT,
        responsibilities=[
            "Write behavior-driven scenarios in Gherkin format",
            "Validate scenarios with stakeholders",
            "Prepare scenarios for automated step definitions",
        ],
        scope="Behavior-driven development and feature specifications",
        when_to_use="When user-facing features need BDD-style specifications",
        when_not_to_use="Not used for internal utilities or non-user-facing code",
        completion_criteria=[
            "Scenarios written in Gherkin format",
            "Scenarios validated with stakeholders",
            "Ready for step implementation",
        ],
    ),
    "code-reviewer": AgentDefinition(
        id="code-reviewer",
        description="Reviews diffs for correctness, compatibility, and test coverage without modifying files.",
        mode=AgentMode.READ_ONLY,
        preferred_model=Model.SONNET,
        permissions=AgentPermissions(can_read_files=True),
        lifetime=AgentLifetime.PERMANENT,
        source=DefinitionSource.DEFAULT,
        responsibilities=[
            "Review code changes for correctness and quality",
            "Assess compatibility with existing codebase",
            "Evaluate test coverage of changes",
        ],
        scope="Code review and quality assurance",
        when_to_use="After code changes are ready for review",
        when_not_to_use="Not used for implementing changes or writing code",
        completion_criteria=[
            "Diff reviewed for correctness",
            "Compatibility with codebase verified",
            "Test coverage adequacy assessed",
        ],
    ),
    "documentation-agent": AgentDefinition(
        id="documentation-agent",
        description="Keeps README and docs synchronized with implemented behavior.",
        mode=AgentMode.WRITE,
        preferred_model=Model.HAIKU,
        permissions=AgentPermissions(can_read_files=True, can_write_files=True),
        lifetime=AgentLifetime.PERMANENT,
        source=DefinitionSource.DEFAULT,
        responsibilities=[
            "Update documentation to reflect implemented changes",
            "Keep examples and usage docs synchronized",
            "Maintain README and user-facing docs",
        ],
        scope="Documentation and user guides",
        when_to_use="When new features or changes need documentation updates",
        when_not_to_use="Not used for code implementation or testing",
        completion_criteria=[
            "Documentation updated to reflect changes",
            "Examples and usage docs synchronized",
            "README and primary docs reviewed",
        ],
    ),
    "dependency-agent": AgentDefinition(
        id="dependency-agent",
        description="Tracks and updates project dependencies and their compatibility.",
        mode=AgentMode.WRITE,
        preferred_model=Model.HAIKU,
        permissions=AgentPermissions(
            can_read_files=True, can_write_files=True, can_execute_commands=True
        ),
        lifetime=AgentLifetime.PERMANENT,
        source=DefinitionSource.DEFAULT,
        responsibilities=[
            "Audit project dependencies for updates and security",
            "Apply dependency updates and resolve conflicts",
            "Verify compatibility across dependencies",
        ],
        scope="Dependency management and maintenance",
        when_to_use="For regular dependency audits and updates",
        when_not_to_use="Not used for feature implementation",
        completion_criteria=[
            "Dependencies audited for updates",
            "Updates applied and tested",
            "Compatibility across dependency graph verified",
        ],
    ),
    "ci-build-agent": AgentDefinition(
        id="ci-build-agent",
        description="Maintains CI pipeline configuration and build health.",
        mode=AgentMode.WRITE,
        preferred_model=Model.HAIKU,
        permissions=AgentPermissions(can_read_files=True, can_write_files=True),
        lifetime=AgentLifetime.PERMANENT,
        source=DefinitionSource.DEFAULT,
        responsibilities=[
            "Maintain CI/CD pipeline configuration",
            "Monitor and improve build health",
            "Ensure test suite runs successfully in CI",
        ],
        scope="CI/CD pipeline and build infrastructure",
        when_to_use="When CI configuration needs updates or maintenance",
        when_not_to_use="Not used for application code changes",
        completion_criteria=[
            "CI configuration verified and updated",
            "Build pipeline health confirmed",
            "Test suite passing in CI environment",
        ],
    ),
    "performance-agent": AgentDefinition(
        id="performance-agent",
        description="Checks for performance regressions in changed code paths.",
        mode=AgentMode.READ_ONLY,
        preferred_model=Model.SONNET,
        permissions=AgentPermissions(can_read_files=True, can_execute_commands=True),
        lifetime=AgentLifetime.PERMANENT,
        source=DefinitionSource.DEFAULT,
        responsibilities=[
            "Establish baseline performance metrics",
            "Detect performance regressions in changes",
            "Identify performance hotspots and optimization opportunities",
        ],
        scope="Performance analysis and regression detection",
        when_to_use="When changes might affect system performance",
        when_not_to_use="Not used for purely cosmetic or documentation-only changes",
        completion_criteria=[
            "Baseline performance established",
            "No performance regressions detected",
            "Hotspots identified and documented",
        ],
    ),
    "security-reviewer": AgentDefinition(
        id="security-reviewer",
        description="Reviews changes for security risks and unsafe patterns.",
        mode=AgentMode.READ_ONLY,
        preferred_model=Model.SONNET,
        permissions=AgentPermissions(can_read_files=True),
        lifetime=AgentLifetime.PERMANENT,
        source=DefinitionSource.DEFAULT,
        responsibilities=[
            "Review changes for security vulnerabilities",
            "Identify unsafe patterns and anti-patterns",
            "Provide security recommendations",
        ],
        scope="Security review and vulnerability assessment",
        when_to_use="When changes involve security-sensitive code or data handling",
        when_not_to_use="Not used for non-security concerns",
        completion_criteria=[
            "Security review completed",
            "No high-risk patterns or vulnerabilities found",
            "Security recommendations documented",
        ],
    ),
    "release-agent": AgentDefinition(
        id="release-agent",
        description="Prepares version bumps, changelogs, and release artifacts.",
        mode=AgentMode.WRITE,
        preferred_model=Model.HAIKU,
        permissions=AgentPermissions(
            can_read_files=True, can_write_files=True, can_create_commits=True
        ),
        lifetime=AgentLifetime.PERMANENT,
        source=DefinitionSource.DEFAULT,
        responsibilities=[
            "Bump version numbers according to semver",
            "Update changelogs with release notes",
            "Prepare release artifacts and tags",
        ],
        scope="Release management and versioning",
        when_to_use="When preparing a new release version",
        when_not_to_use="Not used for development or pre-release work",
        completion_criteria=[
            "Version number updated",
            "Changelog updated with release notes",
            "Release artifacts and tags prepared",
        ],
    ),
}


def select_agents(profile: ProjectProfile, decisions: list[Decision]) -> list[AgentDefinition]:
    """Select and configure agents for a project based on profile and decisions.

    Args:
        profile: Project profile describing the codebase structure and tools.
        decisions: List of active decisions affecting agent selection.

    Returns:
        Sorted list of AgentDefinition instances configured for the project.
    """
    selected_ids: set[str] = set()

    # Rule 1: Always include core agents
    selected_ids.update(["project-orchestrator", "repository-cartographer", "code-reviewer"])

    # Rule 2: Include architecture-guardian if conditions met
    if len(profile.subsystems) >= 3 or profile.risks or profile.legacy_areas:
        selected_ids.add("architecture-guardian")

    # Rule 3: Always include implementation-agent
    selected_ids.add("implementation-agent")

    # Rule 4: Include test-agent if test frameworks exist
    if profile.test_frameworks:
        selected_ids.add("test-agent")

    # Rule 5: Always include documentation-agent (always safe to include)
    selected_ids.add("documentation-agent")

    # Rule 6: Include dependency-agent if build systems exist
    if profile.build_systems:
        selected_ids.add("dependency-agent")

    # Rule 7: Include ci-build-agent if CI systems exist
    if profile.ci_systems:
        selected_ids.add("ci-build-agent")

    # Rule 8: Include bdd-feature-agent if "bdd" or "gherkin" in any decision title/value
    for decision in decisions:
        decision_text = f"{decision.title} {str(decision.value)}".lower()
        if "bdd" in decision_text or "gherkin" in decision_text:
            selected_ids.add("bdd-feature-agent")
            break

    # Rule 9: Include performance-agent if "performance", "realtime", or "real-time" in decision title
    for decision in decisions:
        decision_title = decision.title.lower()
        if (
            "performance" in decision_title
            or "realtime" in decision_title
            or "real-time" in decision_title
        ):
            selected_ids.add("performance-agent")
            break

    # Rule 10: Include security-reviewer if "security" in decision title
    for decision in decisions:
        if "security" in decision.title.lower():
            selected_ids.add("security-reviewer")
            break

    # Rule 11: Include release-agent if "release" in decision title
    for decision in decisions:
        if "release" in decision.title.lower():
            selected_ids.add("release-agent")
            break

    # Deep-copy selected agents and apply decision-driven attribute injection
    agents: list[AgentDefinition] = []
    for agent_id in selected_ids:
        agent = copy.deepcopy(CANDIDATE_ROLES[agent_id])

        # Apply decision-driven constraints and mandatory tools
        for decision in decisions:
            if decision.status == DecisionStatus.ACTIVE and agent_id in decision.effects.get(
                "agents", []
            ):
                # Add constraint
                constraint = f"{decision.title}: {decision.reason}"
                if constraint not in agent.constraints:
                    agent.constraints.append(constraint)

                # Add mandatory tools if present in decision value
                if isinstance(decision.value, dict):
                    mandatory_tools = decision.value.get("mandatory_tools", [])
                    if isinstance(mandatory_tools, list):
                        for tool in mandatory_tools:
                            if tool not in agent.mandatory_tools:
                                agent.mandatory_tools.append(tool)

                # Mark as ADHOC if constraints or mandatory tools were added
                agent.source = DefinitionSource.ADHOC

        agents.append(agent)

    # Return sorted by id
    return sorted(agents, key=lambda a: a.id)

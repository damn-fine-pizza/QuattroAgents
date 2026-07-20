"""Skills catalog and selection logic for agent workflows.

Defines the DEFAULT_SKILLS catalog and the select_skills function that
filters default skills by agent capabilities and creates ad-hoc skills
from workflow-related decisions.
"""

from __future__ import annotations

import copy
import re

from quattroagents.domain import (
    AgentDefinition,
    Decision,
    DecisionStatus,
    DefinitionSource,
    SkillDefinition,
)

# --------------------------------------------------------------------------
# DEFAULT_SKILLS catalog
# --------------------------------------------------------------------------

DEFAULT_SKILLS: dict[str, SkillDefinition] = {
    "implement-feature": SkillDefinition(
        id="implement-feature",
        trigger="Implement a new feature or scoped change.",
        workflow=[
            "Analyze requirements and acceptance criteria.",
            "Write implementation code with appropriate abstractions.",
            "Add unit tests covering normal and edge cases.",
            "Verify integration with existing systems.",
        ],
        inputs=[
            "Feature specification or user story",
            "Acceptance criteria",
            "Design notes or API contracts",
        ],
        outputs=[
            "Implemented feature code",
            "Unit tests",
            "Integration test results",
        ],
        validation_criteria=[
            "All acceptance criteria met",
            "Unit test coverage above 80%",
            "Code review approval",
        ],
        usable_by_agents=["implementation-agent"],
        source=DefinitionSource.DEFAULT,
        body=None,
    ),
    "fix-bug": SkillDefinition(
        id="fix-bug",
        trigger="Diagnose and fix a reported bug.",
        workflow=[
            "Reproduce the bug with a minimal test case.",
            "Identify root cause by inspecting relevant code.",
            "Implement a targeted fix with regression tests.",
            "Verify the fix resolves the issue without side effects.",
        ],
        inputs=[
            "Bug report with reproduction steps",
            "Expected behavior",
            "Affected system or component",
        ],
        outputs=[
            "Bug fix code",
            "Regression test",
            "Root cause analysis",
        ],
        validation_criteria=[
            "Bug successfully reproduced and fixed",
            "Regression test passes",
            "No new issues introduced",
        ],
        usable_by_agents=["implementation-agent"],
        source=DefinitionSource.DEFAULT,
        body=None,
    ),
    "review-change": SkillDefinition(
        id="review-change",
        trigger="Independently review a diff before it is accepted.",
        workflow=[
            "Examine the diff for correctness and style compliance.",
            "Verify tests adequately cover the changes.",
            "Check for performance implications or security concerns.",
            "Provide structured feedback or approval.",
        ],
        inputs=[
            "Pull request or diff",
            "Change context and rationale",
            "Test results",
        ],
        outputs=[
            "Code review feedback",
            "Approval or requested changes",
            "Summary of issues found",
        ],
        validation_criteria=[
            "Review covers functional correctness",
            "Test coverage assessment provided",
            "Clear recommendations or approval given",
        ],
        usable_by_agents=["code-reviewer", "architecture-guardian"],
        source=DefinitionSource.DEFAULT,
        body=None,
    ),
    "update-documentation": SkillDefinition(
        id="update-documentation",
        trigger="Keep README/docs synchronized with a behavior change.",
        workflow=[
            "Identify affected documentation sections.",
            "Update docs to reflect new behavior or API.",
            "Verify examples are correct and runnable.",
            "Check for consistency with other docs.",
        ],
        inputs=[
            "Behavior change or new feature",
            "Updated API signatures or configs",
            "Related codebase changes",
        ],
        outputs=[
            "Updated documentation",
            "Verified examples",
            "Consistency check summary",
        ],
        validation_criteria=[
            "Documentation matches current behavior",
            "Examples tested and working",
            "No orphaned or outdated references",
        ],
        usable_by_agents=["documentation-agent"],
        source=DefinitionSource.DEFAULT,
        body=None,
    ),
    "run-regression-analysis": SkillDefinition(
        id="run-regression-analysis",
        trigger="Investigate a regression or unexpected behavior change.",
        workflow=[
            "Define scope and identify potential causes.",
            "Run tests to isolate the regression.",
            "Compare behavior before and after change.",
            "Document findings and recommend resolution.",
        ],
        inputs=[
            "Reported regression or behavior change",
            "Recent code changes or deployment info",
            "Test results showing the issue",
        ],
        outputs=[
            "Regression analysis report",
            "Root cause identification",
            "Recommended fix or workaround",
        ],
        validation_criteria=[
            "Root cause clearly identified",
            "Analysis reproducible",
            "Recommendations prioritized",
        ],
        usable_by_agents=["implementation-agent", "test-agent"],
        source=DefinitionSource.DEFAULT,
        body=None,
    ),
    "prepare-release": SkillDefinition(
        id="prepare-release",
        trigger="Prepare a version bump, changelog entry, and release artifacts.",
        workflow=[
            "Determine new version following semantic versioning.",
            "Compile changelog from commits and pull requests.",
            "Update version strings in codebase.",
            "Generate release notes and tag the release.",
        ],
        inputs=[
            "Previous version number",
            "List of changes or commits",
            "Release notes template",
        ],
        outputs=[
            "Updated version numbers",
            "Changelog entry",
            "Release notes and artifacts",
        ],
        validation_criteria=[
            "Semantic versioning applied correctly",
            "Changelog comprehensive and accurate",
            "Version strings consistent across codebase",
        ],
        usable_by_agents=["release-agent"],
        source=DefinitionSource.DEFAULT,
        body=None,
    ),
    "update-dependencies": SkillDefinition(
        id="update-dependencies",
        trigger="Check for and apply compatible dependency updates.",
        workflow=[
            "Scan dependencies for available updates.",
            "Identify breaking changes in candidates.",
            "Update compatible versions and lock file.",
            "Run tests to verify compatibility.",
        ],
        inputs=[
            "Dependency manifest or lock file",
            "Update strategy (major/minor/patch)",
            "Security advisory list (if any)",
        ],
        outputs=[
            "Updated dependency versions",
            "Updated lock file",
            "Test results and compatibility report",
        ],
        validation_criteria=[
            "Updates applied safely without breaking changes",
            "All tests pass with new versions",
            "Security advisories resolved",
        ],
        usable_by_agents=["dependency-agent"],
        source=DefinitionSource.DEFAULT,
        body=None,
    ),
}


# --------------------------------------------------------------------------
# select_skills function
# --------------------------------------------------------------------------


def _slugify(title: str) -> str:
    """Convert title to kebab-case slug.

    Converts to lowercase, replaces non-alphanumeric chars with hyphens,
    collapses repeated hyphens, and strips leading/trailing hyphens.
    """
    # Convert to lowercase and replace non-[a-z0-9] with hyphen
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower())
    # Collapse repeated hyphens
    slug = re.sub(r"-+", "-", slug)
    # Strip leading and trailing hyphens
    slug = slug.strip("-")
    return slug


def select_skills(
    agents: list[AgentDefinition], decisions: list[Decision]
) -> list[SkillDefinition]:
    """Select applicable skills for given agents and active decisions.

    1. Filter DEFAULT_SKILLS to include only those usable by provided agents.
       Deep-copy each to avoid mutating the module catalog.
    2. For each ACTIVE decision with "workflow" in classification or title,
       create an ad-hoc SkillDefinition with slugified id.
    3. Deduplicate by id (keeping first occurrence) and return sorted by id.

    Args:
        agents: List of agent definitions to filter skills for.
        decisions: List of decisions to extract workflow-related skills from.

    Returns:
        Sorted list of applicable SkillDefinitions.
    """
    agent_ids = {agent.id for agent in agents}
    result: dict[str, SkillDefinition] = {}

    # Part 1: Filter and deep-copy DEFAULT_SKILLS
    for skill_id, skill in DEFAULT_SKILLS.items():
        if agent_ids & set(skill.usable_by_agents):
            result[skill_id] = copy.deepcopy(skill)

    # Part 2: Create ad-hoc skills from ACTIVE decisions with workflow classification
    for decision in decisions:
        if decision.status != DecisionStatus.ACTIVE:
            continue

        # Check for "workflow" classification or in title
        is_workflow = (
            "workflow" in decision.value.get("classification", [])
            or "workflow" in decision.title.lower()
        )

        if not is_workflow:
            continue

        # Slugify the title
        slug = _slugify(decision.title)
        custom_id = f"custom-{slug}"

        # Skip if this id already exists (dedup)
        if custom_id in result:
            continue

        # Build workflow: use reason if available, otherwise title
        workflow = [decision.reason] if decision.reason else [decision.title]

        # Extract effects.agents for usable_by_agents
        usable_by = list(decision.effects.get("agents", []))

        # Extract mandatory_tools and validation_criteria from value
        required_tools = (
            list(decision.value.get("mandatory_tools", []))
            if "mandatory_tools" in decision.value
            else []
        )
        validation_criteria = (
            list(decision.value.get("validation_criteria", ["manual review"]))
            if "validation_criteria" in decision.value
            else ["manual review"]
        )

        # Create the ad-hoc skill
        adhoc_skill = SkillDefinition(
            id=custom_id,
            trigger=decision.title,
            workflow=workflow,
            inputs=[],
            outputs=[],
            required_tools=required_tools,
            validation_criteria=validation_criteria,
            usable_by_agents=usable_by,
            source=DefinitionSource.ADHOC,
            body=None,
        )

        result[custom_id] = adhoc_skill

    # Part 3: Return sorted by id
    return sorted(result.values(), key=lambda s: s.id)

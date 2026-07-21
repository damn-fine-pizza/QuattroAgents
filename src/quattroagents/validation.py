"""Configuration validation for agent, skill, and swarm definitions.

Collects all validation violations and returns them as a structured result,
with optional rendering as JSON or human-readable text.
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field

from quattroagents.domain import AgentDefinition, AgentMode, SkillDefinition, SwarmDefinition
from quattroagents.formatting import AgentDisplayFormatValidator, render_agent_display
from quattroagents.generation.swarm import find_dependency_cycle


@dataclass
class ConfigViolation:
    """A single configuration validation violation."""

    code: str
    message: str
    path: str | None = None


@dataclass
class ConfigValidationResult:
    """Result of a full configuration validation."""

    valid: bool
    violations: list[ConfigViolation] = field(default_factory=list)


def validate_generated_configuration(
    agents: list[AgentDefinition],
    skills: list[SkillDefinition],
    swarm: SwarmDefinition | None = None,
    available_tool_ids: set[str] | None = None,
) -> ConfigValidationResult:
    """Validate a generated configuration for consistency and completeness.

    Performs all validation checks and collects violations without raising
    exceptions. Returns a ConfigValidationResult with valid=False if any
    violations are found.

    Args:
        agents: List of agent definitions to validate.
        skills: List of skill definitions to validate.
        swarm: Optional swarm definition to validate.
        available_tool_ids: Optional set of available tool IDs for tool validation.

    Returns:
        ConfigValidationResult with valid flag and list of violations found.
    """
    violations: list[ConfigViolation] = []

    # Check 1: Duplicate agent ids
    seen_agent_ids: dict[str, int] = {}
    for agent in agents:
        seen_agent_ids[agent.id] = seen_agent_ids.get(agent.id, 0) + 1

    for agent_id, count in seen_agent_ids.items():
        if count > 1:
            violations.append(
                ConfigViolation(
                    code="duplicate_agent_id",
                    message=f"agent id '{agent_id}' is declared more than once",
                    path=agent_id,
                )
            )

    # Check 2: Duplicate skill ids
    seen_skill_ids: dict[str, int] = {}
    for skill in skills:
        seen_skill_ids[skill.id] = seen_skill_ids.get(skill.id, 0) + 1

    for skill_id, count in seen_skill_ids.items():
        if count > 1:
            violations.append(
                ConfigViolation(
                    code="duplicate_skill_id",
                    message=f"skill id '{skill_id}' is declared more than once",
                    path=skill_id,
                )
            )

    # Check 3: Agents without completion criteria
    for agent in agents:
        if not agent.completion_criteria:
            violations.append(
                ConfigViolation(
                    code="agent_missing_completion_criteria",
                    message=f"agent '{agent.id}' has no completion criteria",
                    path=agent.id,
                )
            )

    # Check 4: Skills without trigger or workflow
    for skill in skills:
        has_trigger = skill.trigger.strip() if skill.trigger else False
        has_workflow = skill.workflow is not None and len(skill.workflow) > 0
        has_body = skill.body is not None

        if not has_trigger and not (has_body or has_workflow):
            violations.append(
                ConfigViolation(
                    code="skill_missing_trigger_or_workflow",
                    message=f"skill '{skill.id}' has no trigger and no workflow",
                    path=skill.id,
                )
            )

    # Check 5: Write-enabled agents without clear limits
    for agent in agents:
        if agent.mode == AgentMode.WRITE:
            if not agent.relevant_paths and not agent.constraints:
                violations.append(
                    ConfigViolation(
                        code="write_agent_without_limits",
                        message=f"agent '{agent.id}' can write files but declares no relevant_paths or constraints",
                        path=agent.id,
                    )
                )

    # Check 6: References to non-existent agents
    known_agent_ids = {a.id for a in agents}

    # Check skill references
    for skill in skills:
        for agent_id in skill.usable_by_agents:
            if agent_id not in known_agent_ids:
                violations.append(
                    ConfigViolation(
                        code="skill_references_unknown_agent",
                        message=f"skill '{skill.id}' references unknown agent '{agent_id}'",
                        path=skill.id,
                    )
                )

    # Check swarm references
    if swarm is not None:
        # Check agent steps
        for step in swarm.agents:
            if step.agent_id not in known_agent_ids:
                violations.append(
                    ConfigViolation(
                        code="swarm_references_unknown_agent",
                        message=f"swarm plan references unknown agent '{step.agent_id}'",
                        path=step.agent_id,
                    )
                )

        # Check required review agents
        for agent_id in swarm.required_review_agents:
            if agent_id not in known_agent_ids:
                violations.append(
                    ConfigViolation(
                        code="swarm_references_unknown_agent",
                        message=f"swarm plan references unknown agent '{agent_id}'",
                        path=agent_id,
                    )
                )

    # Check 7: Circular dependency in swarm
    if swarm is not None:
        dependencies: dict[str, list[str]] = {}
        for step in swarm.agents:
            dependencies[step.agent_id] = step.depends_on
        # Dependency targets may reference agents outside the swarm's own
        # step list (e.g. required reviewers) — include them as nodes too.
        for deps in dependencies.values():
            for dep in deps:
                dependencies.setdefault(dep, [])

        if find_dependency_cycle(set(dependencies), dependencies) is not None:
            violations.append(
                ConfigViolation(
                    code="swarm_dependency_cycle",
                    message="swarm plan contains a circular dependency",
                    path=None,
                )
            )

    # Check 8: Agents referencing unavailable tools
    if available_tool_ids is not None:
        for agent in agents:
            for tool_id in agent.mandatory_tools:
                if tool_id not in available_tool_ids:
                    violations.append(
                        ConfigViolation(
                            code="agent_requires_unavailable_tool",
                            message=f"agent '{agent.id}' requires unavailable tool '{tool_id}'",
                            path=agent.id,
                        )
                    )

    # Check 9: Agent display line must match the canonical
    # `<role> (<tier>)` grammar
    display_validator = AgentDisplayFormatValidator()
    for agent in agents:
        display_result = display_validator.validate(render_agent_display(agent))
        for format_violation in display_result.violations:
            violations.append(
                ConfigViolation(
                    code=f"agent_display_format_{format_violation.code}",
                    message=f"agent '{agent.id}' display line: {format_violation.message}",
                    path=agent.id,
                )
            )

    # Check 10: Circular hand-off in the expected_inputs/expected_outputs
    # producer/consumer graph. Each entry is "artifact-name: description";
    # an agent depends on whatever other agent declares that artifact name
    # as an output. This is the static-generation analogue of a deadlock
    # check — it catches agent teams whose declared hand-offs can never be
    # ordered (A waits on an artifact only B produces, and B waits on one
    # only A produces).
    def _artifact_name(entry: str) -> str:
        return entry.split(":", 1)[0].strip()

    producers: dict[str, list[str]] = {}
    for agent in agents:
        for entry in agent.expected_outputs:
            producers.setdefault(_artifact_name(entry), []).append(agent.id)

    handoff_depends_on: dict[str, list[str]] = {agent.id: [] for agent in agents}
    for agent in agents:
        for entry in agent.expected_inputs:
            for producer_id in producers.get(_artifact_name(entry), []):
                if producer_id != agent.id and producer_id not in handoff_depends_on[agent.id]:
                    handoff_depends_on[agent.id].append(producer_id)

    cycle = find_dependency_cycle(set(handoff_depends_on), handoff_depends_on)
    if cycle is not None:
        violations.append(
            ConfigViolation(
                code="agent_handoff_cycle",
                message=f"agents have a circular hand-off dependency: {', '.join(cycle)}",
                path=None,
            )
        )

    return ConfigValidationResult(
        valid=(len(violations) == 0),
        violations=violations,
    )


def render_validation_report(result: ConfigValidationResult, format: str = "text") -> str:
    """Render a validation result as a formatted report.

    Args:
        result: The ConfigValidationResult to render.
        format: Output format - "text" (default) or "json".

    Returns:
        Formatted validation report as a string.

    Raises:
        ValueError: If format is not recognized.
    """
    if format == "json":
        return json.dumps(
            {
                "status": "ok" if result.valid else "error",
                "violations": [dataclasses.asdict(v) for v in result.violations],
            },
            indent=2,
        )
    elif format == "text":
        if result.valid:
            return "Configuration is valid."

        lines = [f"Configuration validation failed ({len(result.violations)} issue(s)):"]
        lines.append("")
        for violation in result.violations:
            lines.append(f"- {violation.code}: {violation.message}")

        return "\n".join(lines)
    else:
        raise ValueError(f"unknown format: {format}")

"""Swarm plan generation with wave-based scheduling.

This module implements deterministic swarm plan construction using Kahn's
algorithm to compute conflict-free execution waves for agent groups.
"""

from __future__ import annotations

from ..domain import (
    AgentDefinition,
    AgentMode,
    Decision,
    SwarmAgentStep,
    SwarmDefinition,
)
from ..formatting import render_agent_display


def _files_overlap(first: list[str], second: list[str]) -> bool:
    """Check if two path lists have overlapping ownership.

    Paths overlap if they are equal, one is a wildcard "*", or one is a
    prefix directory of the other (with "/" boundary respect).
    """
    for left in first:
        for right in second:
            left_path = left.rstrip("/")
            right_path = right.rstrip("/")
            if (
                left_path == "*"
                or right_path == "*"
                or left_path == right_path
                or left_path.startswith(right_path + "/")
                or right_path.startswith(left_path + "/")
            ):
                return True
    return False


def find_dependency_cycle(node_ids: set[str], depends_on: dict[str, list[str]]) -> list[str] | None:
    """Find a cycle in a dependency graph using Kahn's algorithm.

    Generic dependency-only cycle check (no file-ownership conflict
    handling — see `_compute_waves` for that). Used both internally and by
    `validate_generated_configuration` to check the producer/consumer graph
    derived from agents' `expected_inputs`/`expected_outputs` for circular
    hand-off loops.

    Returns the sorted list of node ids stuck in a cycle, or None if the
    graph is acyclic.
    """
    completed: set[str] = set()
    remaining = set(node_ids)

    while remaining:
        ready = {
            node_id for node_id in remaining if set(depends_on.get(node_id, [])).issubset(completed)
        }
        if not ready:
            return sorted(remaining)
        completed.update(ready)
        remaining -= ready

    return None


def _compute_waves(
    agent_ids: set[str],
    depends_on: dict[str, list[str]],
    file_ownership: dict[str, list[str]],
) -> list[list[str]]:
    """Compute wave groups using Kahn's algorithm with file conflict resolution.

    Iteratively finds agents whose dependencies are satisfied, then selects
    non-conflicting agents (by file ownership) for each wave. Agents within
    a wave can run in parallel.

    Raises ValueError if a cycle is detected.
    """
    completed: set[str] = set()
    waves: list[list[str]] = []

    while len(completed) < len(agent_ids):
        # Find ready agents: all dependencies completed, not yet done
        ready = [
            agent_id
            for agent_id in agent_ids
            if agent_id not in completed and set(depends_on.get(agent_id, [])).issubset(completed)
        ]

        if not ready:
            raise ValueError("swarm dependencies contain a cycle")

        # Sort for stable ordering
        ready.sort()

        # Select non-conflicting agents for this wave
        selected: list[str] = []
        claimed_paths: list[str] = []

        for agent_id in ready:
            paths = file_ownership.get(agent_id, [])
            if not _files_overlap(claimed_paths, paths):
                selected.append(agent_id)
                claimed_paths.extend(paths)

        if not selected:
            # This shouldn't happen if we have ready agents
            raise ValueError("swarm dependencies contain a cycle")

        completed.update(selected)
        waves.append(selected)

    return waves


def build_swarm_plan(
    task_id: str,
    goal: str,
    agents: list[AgentDefinition],
    phases: dict[str, str],
    depends_on: dict[str, list[str]],
    file_ownership: dict[str, list[str]],
    decisions: list[Decision],
) -> SwarmDefinition:
    """Build a swarm plan with wave-based scheduling.

    Validates agent references, computes non-conflicting waves, and
    extracts mandatory reviewers and completion criteria from agent
    definitions and decisions.

    Args:
        task_id: Unique task identifier
        goal: Task goal/objective
        agents: Agent definitions to be scheduled
        phases: Mapping of agent_id to phase name
        depends_on: Mapping of agent_id to list of agent_ids it depends on
        file_ownership: Mapping of agent_id to list of path prefixes it owns
        decisions: List of decisions affecting swarm configuration

    Returns:
        SwarmDefinition with computed waves and metadata

    Raises:
        ValueError if validation fails (unknown agent, self-dependency, cycle)
    """
    # Validate all dict keys correspond to agents
    agent_ids = {agent.id for agent in agents}

    for agent_id in phases:
        if agent_id not in agent_ids:
            raise ValueError(f"unknown agent in swarm plan: {agent_id}")

    for agent_id in depends_on:
        if agent_id not in agent_ids:
            raise ValueError(f"unknown agent in swarm plan: {agent_id}")

    for agent_id in file_ownership:
        if agent_id not in agent_ids:
            raise ValueError(f"unknown agent in swarm plan: {agent_id}")

    # Validate dependency constraints
    for agent_id, deps in depends_on.items():
        if agent_id in deps:
            raise ValueError("swarm agent cannot depend on itself")
        for dep in deps:
            if dep not in agent_ids:
                raise ValueError(f"unknown swarm dependency: {dep}")

    # Compute waves
    waves = _compute_waves(agent_ids, depends_on, file_ownership)

    # Build SwarmAgentStep objects
    agent_steps: list[SwarmAgentStep] = []
    for wave_idx, wave_agents in enumerate(waves):
        for agent_id in wave_agents:
            parallel_group: str | None = None
            can_run_parallel: list[str] = []

            if len(wave_agents) > 1:
                parallel_group = f"wave-{wave_idx}"
                can_run_parallel = sorted([a for a in wave_agents if a != agent_id])

            step = SwarmAgentStep(
                agent_id=agent_id,
                phase=phases.get(agent_id, ""),
                parallel_group=parallel_group,
                depends_on=sorted(depends_on.get(agent_id, [])),
                can_run_parallel_with=can_run_parallel,
            )
            agent_steps.append(step)

    # Extract required_review_agents
    review_agents: set[str] = set()

    # From agent modes (READ_ONLY agents are mandatory reviewers)
    for agent in agents:
        if agent.mode == AgentMode.READ_ONLY:
            review_agents.add(agent.id)

    # From decisions with mandatory_review flag
    for decision in decisions:
        if decision.effects.get("agents") and decision.value.get("mandatory_review"):
            review_agents.update(decision.effects["agents"])

    review_agents_list = sorted(review_agents)

    # Extract completion_criteria
    criteria = [
        "build passes",
        "tests pass",
        "requested behavior is covered",
    ]

    for decision in decisions:
        dc = decision.value.get("completion_criteria")
        if isinstance(dc, list) and all(isinstance(c, str) for c in dc):
            criteria.extend(dc)

    # Dedup while preserving order
    seen: set[str] = set()
    unique_criteria: list[str] = []
    for c in criteria:
        if c not in seen:
            seen.add(c)
            unique_criteria.append(c)

    return SwarmDefinition(
        task_id=task_id,
        goal=goal,
        agents=agent_steps,
        required_review_agents=review_agents_list,
        completion_criteria=unique_criteria,
    )


def render_swarm_plan_text(
    plan: SwarmDefinition,
    agents_by_id: dict[str, AgentDefinition],
) -> str:
    """Render a swarm plan as human-readable text.

    Groups agents by phase, renders each using canonical format,
    and lists mandatory reviewers and completion criteria if present.

    Args:
        plan: The swarm plan to render
        agents_by_id: Mapping of agent_id to AgentDefinition

    Returns:
        Human-readable text representation of the plan
    """
    # Group agents by phase, preserving first-seen order
    phases_ordered: list[str] = []
    phase_to_steps: dict[str, list[SwarmAgentStep]] = {}

    for step in plan.agents:
        if step.phase not in phase_to_steps:
            phases_ordered.append(step.phase)
            phase_to_steps[step.phase] = []
        phase_to_steps[step.phase].append(step)

    lines: list[str] = []

    for phase in phases_ordered:
        if lines:
            lines.append("")

        lines.append(f"{phase}:")

        for step in phase_to_steps[phase]:
            agent = agents_by_id[step.agent_id]
            display = render_agent_display(agent)
            lines.append(display)

    if plan.required_review_agents:
        lines.append("")
        review_list = ", ".join(plan.required_review_agents)
        lines.append(f"Review required: {review_list}")

    if plan.completion_criteria:
        lines.append(f"Completion criteria: {'; '.join(plan.completion_criteria)}")

    return "\n".join(lines)

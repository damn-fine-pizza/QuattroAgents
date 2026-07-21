"""Adapter for rendering agents and skills as Claude .claude/ configuration files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..domain import AgentDefinition, SkillDefinition
from ..formatting import agent_file_stem
from ..persistence import GeneratedFileGuard, WriteResult


def render_claude(
    root: Path,
    agents: list[AgentDefinition],
    skills: list[SkillDefinition],
    guard: GeneratedFileGuard,
) -> list[WriteResult]:
    """Render agents and skills as Claude .claude/ configuration files.

    For each agent, writes `.claude/agents/qag-{agent.id}.md` with YAML frontmatter
    and structured markdown content.

    For each skill, writes `.claude/skills/{skill.id}/SKILL.md` with either
    the skill's pre-rendered body (if provided) or generated markdown.

    Also writes `.claude/settings.json` and `.mcp.json` configuration files,
    merging with existing content if present.

    Args:
        root: Project root path.
        agents: List of agents to render.
        skills: List of skills to render.
        guard: GeneratedFileGuard instance for writing files with conflict detection.

    Returns:
        List of WriteResult objects from all guard.write() calls.
    """
    results: list[WriteResult] = []

    # Write agents
    for agent in agents:
        content = _render_agent_markdown(agent)
        relative_path = f".claude/agents/{agent_file_stem(agent.id)}.md"
        result = guard.write(relative_path, content)
        results.append(result)

    # Write skills
    for skill in skills:
        content = _render_skill_markdown(skill)
        relative_path = f".claude/skills/{skill.id}/SKILL.md"
        result = guard.write(relative_path, content)
        results.append(result)

    # Write settings.json
    settings_content = _render_settings_json(root)
    result = guard.write(".claude/settings.json", settings_content)
    results.append(result)

    # Write .mcp.json
    mcp_content = _render_mcp_json(root)
    result = guard.write(".mcp.json", mcp_content)
    results.append(result)

    return results


def _render_agent_markdown(agent: AgentDefinition) -> str:
    """Render an agent definition as markdown with YAML frontmatter."""
    lines: list[str] = []

    # Frontmatter
    lines.append("---")
    lines.append(f"name: {agent_file_stem(agent.id)}")
    lines.append(f"description: {agent.description}")
    lines.append(f"model: {agent.preferred_model.value}")
    lines.append(f"mode: {agent.mode.value}")
    lines.append("---")
    lines.append("")

    # Responsibilities
    lines.append("## Responsibilities")
    for item in agent.responsibilities:
        lines.append(f"- {item}")
    lines.append("")

    # Scope
    lines.append("## Scope")
    lines.append(agent.scope)
    lines.append("")

    # When to use
    lines.append("## When to use")
    lines.append(agent.when_to_use)
    lines.append("")

    # When not to use
    lines.append("## When not to use")
    lines.append(agent.when_not_to_use)
    lines.append("")

    # Tools
    lines.append("## Tools")
    available = ", ".join(agent.available_tools) if agent.available_tools else "none declared"
    lines.append(f"- Available: {available}")
    mandatory = ", ".join(agent.mandatory_tools) if agent.mandatory_tools else "none"
    lines.append(f"- Mandatory: {mandatory}")
    forbidden = ", ".join(agent.forbidden_tools) if agent.forbidden_tools else "none"
    lines.append(f"- Forbidden: {forbidden}")
    lines.append("")

    # Handoff — read/write these artifacts directly instead of relaying
    # their content through the orchestrator's context.
    lines.append("## Handoff")
    if agent.expected_inputs:
        lines.append("- Reads:")
        for item in agent.expected_inputs:
            lines.append(f"  - {item}")
    else:
        lines.append("- Reads: none declared.")
    if agent.expected_outputs:
        lines.append("- Produces:")
        for item in agent.expected_outputs:
            lines.append(f"  - {item}")
    else:
        lines.append("- Produces: none declared.")
    lines.append("")

    # Completion criteria
    lines.append("## Completion criteria")
    for item in agent.completion_criteria:
        lines.append(f"- {item}")
    lines.append("")

    # Escalation criteria
    lines.append("## Escalation criteria")
    if agent.escalation_criteria:
        for item in agent.escalation_criteria:
            lines.append(f"- {item}")
    else:
        lines.append("- None declared.")
    lines.append("")

    # Collaboration
    lines.append("## Collaboration")
    collaboration_text = (
        agent.collaboration_notes
        if agent.collaboration_notes
        else "No special collaboration notes."
    )
    lines.append(collaboration_text)
    lines.append("")

    return "\n".join(lines)


def _render_skill_markdown(skill: SkillDefinition) -> str:
    """Render a skill definition as markdown with YAML frontmatter.

    If skill.body is provided, returns it directly. Otherwise, generates
    markdown from the skill's structured fields.
    """
    if skill.body is not None:
        return skill.body

    lines: list[str] = []

    # Frontmatter
    lines.append("---")
    lines.append(f"name: {skill.id}")
    lines.append(f"trigger: {skill.trigger}")
    lines.append("---")
    lines.append("")

    # Workflow
    lines.append("## Workflow")
    for idx, item in enumerate(skill.workflow, 1):
        lines.append(f"{idx}. {item}")
    lines.append("")

    # Inputs
    lines.append("## Inputs")
    if skill.inputs:
        for item in skill.inputs:
            lines.append(f"- {item}")
    else:
        lines.append("- None declared.")
    lines.append("")

    # Outputs
    lines.append("## Outputs")
    if skill.outputs:
        for item in skill.outputs:
            lines.append(f"- {item}")
    else:
        lines.append("- None declared.")
    lines.append("")

    # Required tools
    lines.append("## Required tools")
    if skill.required_tools:
        for item in skill.required_tools:
            lines.append(f"- {item}")
    else:
        lines.append("- None declared.")
    lines.append("")

    # Validation criteria
    lines.append("## Validation criteria")
    if skill.validation_criteria:
        for item in skill.validation_criteria:
            lines.append(f"- {item}")
    else:
        lines.append("- None declared.")
    lines.append("")

    # Usable by
    lines.append("## Usable by")
    if skill.usable_by_agents:
        usable_text = ", ".join(skill.usable_by_agents)
    else:
        usable_text = "Any agent."
    lines.append(usable_text)
    lines.append("")

    return "\n".join(lines)


def _render_settings_json(root: Path) -> str:
    """Render .claude/settings.json, merging with existing file if present.

    Performs a shallow merge at the top level: the new permissions and hooks
    keys replace any existing ones, but other pre-existing top-level keys
    are preserved.
    """
    settings_path = root / ".claude" / "settings.json"

    # Read existing settings if they exist
    existing: dict[str, Any] = {}
    if settings_path.exists():
        try:
            existing = json.loads(settings_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            pass

    # New settings to merge in
    new_settings: dict[str, Any] = {
        "permissions": {"deny": ["Bash(git push --force:*)"]},
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Edit|Write",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "qagents validate",
                        }
                    ],
                }
            ]
        },
    }

    # Shallow merge: new keys replace/add to existing
    merged = dict(existing)
    merged.update(new_settings)

    return json.dumps(merged, indent=2) + "\n"


def _render_mcp_json(root: Path) -> str:
    """Render .mcp.json, merging with existing file if present.

    Performs a shallow merge at the top level: the new mcpServers key
    replaces any existing one, but other pre-existing top-level keys
    are preserved.
    """
    mcp_path = root / ".mcp.json"

    # Read existing MCP config if it exists
    existing: dict[str, Any] = {}
    if mcp_path.exists():
        try:
            existing = json.loads(mcp_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            pass

    # New MCP servers configuration
    new_servers: dict[str, Any] = {
        "mcpServers": {
            "quattroagents": {
                "command": "qagents",
                "args": ["mcp", "serve"],
            }
        }
    }

    # Shallow merge: new key replaces/adds to existing
    merged = dict(existing)
    merged.update(new_servers)

    return json.dumps(merged, indent=2) + "\n"

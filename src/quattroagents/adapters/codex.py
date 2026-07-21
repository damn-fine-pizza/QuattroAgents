"""Codex adapter for rendering agent and skill definitions.

Generates Codex-compatible configuration files from QuattroAgents definitions.
"""

from __future__ import annotations

import re
from pathlib import Path

from quattroagents.domain import AgentDefinition, Model, SkillDefinition
from quattroagents.persistence import GeneratedFileGuard, WriteResult


def _toml_string(value: str) -> str:
    """Escape TOML string value: backslashes, quotes, and newlines."""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _replace_toml_table(existing: str, header: str, replacement: str) -> str:
    """Replace a TOML table section, preserving other content.

    Removes the header and everything until the next table or EOF,
    then appends the replacement block.
    """
    pattern = rf"(?ms)^{re.escape(header)}\n.*?(?=^\[|\Z)"
    remaining = re.sub(pattern, "", existing).strip()
    return f"{remaining}\n\n{replacement}" if remaining else replacement


def _build_skill_markdown(skill: SkillDefinition) -> str:
    """Build markdown content for a skill from structured data.

    Creates a Markdown file with YAML frontmatter and sections for:
    - Workflow (numbered list)
    - Inputs (bullet list)
    - Outputs (bullet list)
    - Required tools (bullet list)
    - Validation criteria (bullet list)
    - Usable by (comma-joined list or "Any agent.")
    """
    lines: list[str] = []

    # Frontmatter
    lines.append("---")
    lines.append(f"name: {skill.id}")
    lines.append(f"trigger: {skill.trigger}")
    lines.append("---\n")

    # Workflow section (numbered list)
    lines.append("## Workflow")
    if skill.workflow:
        for i, step in enumerate(skill.workflow, 1):
            lines.append(f"{i}. {step}")
    else:
        lines.append("None declared.")
    lines.append("")

    # Inputs section (bullets)
    lines.append("## Inputs")
    if skill.inputs:
        for input_item in skill.inputs:
            lines.append(f"- {input_item}")
    else:
        lines.append("None declared.")
    lines.append("")

    # Outputs section (bullets)
    lines.append("## Outputs")
    if skill.outputs:
        for output_item in skill.outputs:
            lines.append(f"- {output_item}")
    else:
        lines.append("None declared.")
    lines.append("")

    # Required tools section (bullets)
    lines.append("## Required tools")
    if skill.required_tools:
        for tool in skill.required_tools:
            lines.append(f"- {tool}")
    else:
        lines.append("None declared.")
    lines.append("")

    # Validation criteria section (bullets)
    lines.append("## Validation criteria")
    if skill.validation_criteria:
        for criterion in skill.validation_criteria:
            lines.append(f"- {criterion}")
    else:
        lines.append("None declared.")
    lines.append("")

    # Usable by section (comma-joined)
    lines.append("## Usable by")
    if skill.usable_by_agents:
        lines.append(", ".join(skill.usable_by_agents))
    else:
        lines.append("Any agent.")

    return "\n".join(lines)


def render_codex(
    root: Path,
    agents: list[AgentDefinition],
    skills: list[SkillDefinition],
    guard: GeneratedFileGuard,
) -> list[WriteResult]:
    """Render Codex adapter files for agents and skills.

    Generates:
    - `.codex/agents/{agent.id}.toml` for each agent
    - `.agents/skills/{skill.id}/SKILL.md` for each skill
    - `.codex/config.toml` with MCP server configuration
    - `AGENTS.md` project documentation

    Args:
        root: Project root path.
        agents: List of agent definitions.
        skills: List of skill definitions.
        guard: Generated file guard for write operations.

    Returns:
        List of WriteResult objects from all guard.write() calls,
        in the order they were made.
    """
    results: list[WriteResult] = []

    # Model effort mapping
    effort_map: dict[Model, str] = {
        Model.HAIKU: "low",
        Model.SONNET: "medium",
        Model.OPUS: "high",
        Model.INHERIT: "medium",
    }

    # Write agent TOML files
    for agent in agents:
        effort = effort_map[agent.preferred_model]

        # Build developer_instructions from parts
        instructions_parts: list[str] = []

        if agent.scope:
            instructions_parts.append(agent.scope)

        if agent.when_to_use:
            instructions_parts.append(f"When to use: {agent.when_to_use}")

        if agent.when_not_to_use:
            instructions_parts.append(f"When not to use: {agent.when_not_to_use}")

        if agent.completion_criteria:
            instructions_parts.append(
                f"Completion criteria: {'; '.join(agent.completion_criteria)}"
            )

        if agent.constraints:
            instructions_parts.append(f"Constraints: {'; '.join(agent.constraints)}")

        instructions = "\n\n".join(instructions_parts)

        # Build TOML content
        toml_content = (
            f'name = "{_toml_string(agent.id)}"\n'
            f'description = "{_toml_string(agent.description)}"\n'
            f'model_reasoning_effort = "{effort}"\n'
            f'developer_instructions = "{_toml_string(instructions)}"\n'
        )

        result = guard.write(f".codex/agents/{agent.id}.toml", toml_content)
        results.append(result)

    # Write skill markdown files
    for skill in skills:
        if skill.body is not None:
            content = skill.body
        else:
            # Build markdown body from structured data
            content = _build_skill_markdown(skill)

        result = guard.write(f".agents/skills/{skill.id}/SKILL.md", content)
        results.append(result)

    # Write config.toml
    config_path = root / ".codex" / "config.toml"
    if config_path.exists():
        existing_config = config_path.read_text(encoding="utf-8")
    else:
        existing_config = "agents.max_depth = 1\nagents.max_threads = 3"

    quattroagents_server_block = (
        "[mcp_servers.quattroagents]\n"
        'command = ".venv/bin/qagents"\n'
        'args = ["mcp", "serve"]\n'
        'cwd = "."\n'
        "startup_timeout_sec = 10\n"
    )

    config_content = _replace_toml_table(
        existing_config,
        "[mcp_servers.quattroagents]",
        quattroagents_server_block,
    )

    result = guard.write(".codex/config.toml", config_content)
    results.append(result)

    # Write AGENTS.md
    agents_md = (
        "# QuattroAgents Project Agent Factory\n\n"
        "Generated agents live in `.codex/agents/`. Generated skills live in "
        "`.agents/skills/`. State lives in `.agent-factory/`. Do not hand-edit "
        "generated files without expecting the next `setup` run to detect the "
        "change and ask before overwriting.\n"
    )

    result = guard.write("AGENTS.md", agents_md)
    results.append(result)

    return results

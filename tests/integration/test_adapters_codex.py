"""Integration tests for render_codex adapter.

Tests the rendering of agent and skill definitions to Codex-compatible files.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from quattroagents.adapters.codex import render_codex
from quattroagents.domain import AgentDefinition, Model, SkillDefinition
from quattroagents.persistence import AgentFactoryStore


def test_render_codex_writes_single_agent_and_skill(tmp_path: Path) -> None:
    """Test that render_codex writes .codex/agents/<id>.toml and .agents/skills/<id>/SKILL.md."""
    agent = AgentDefinition(
        id="test-agent",
        description="A test agent",
        preferred_model=Model.HAIKU,
        scope="Test scope",
    )
    skill = SkillDefinition(
        id="test-skill",
        trigger="manual",
        workflow=["Step 1", "Step 2"],
    )

    store = AgentFactoryStore(tmp_path)
    guard = store.file_guard()
    results = render_codex(tmp_path, [agent], [skill], guard)

    # Should have 4 write results: agent TOML, skill MD, config TOML, AGENTS.md
    assert len(results) == 4

    # Check agent TOML was written
    agent_toml_path = tmp_path / ".codex" / "agents" / "qag-test-agent.toml"
    assert agent_toml_path.exists()
    agent_toml_content = agent_toml_path.read_text(encoding="utf-8")
    agent_toml = tomllib.loads(agent_toml_content)
    assert agent_toml["name"] == "qag-test-agent"
    assert agent_toml["description"] == "A test agent"
    assert agent_toml["model_reasoning_effort"] == "low"  # HAIKU maps to "low"

    # Check skill SKILL.md was written
    skill_md_path = tmp_path / ".agents" / "skills" / "test-skill" / "SKILL.md"
    assert skill_md_path.exists()
    skill_content = skill_md_path.read_text(encoding="utf-8")
    assert "test-skill" in skill_content
    assert "Step 1" in skill_content
    assert "Step 2" in skill_content


def test_render_codex_model_reasoning_effort_mappings(tmp_path: Path) -> None:
    """Test that different models map to correct model_reasoning_effort values."""
    agents = [
        AgentDefinition(
            id="haiku-agent",
            description="Haiku agent",
            preferred_model=Model.HAIKU,
        ),
        AgentDefinition(
            id="sonnet-agent",
            description="Sonnet agent",
            preferred_model=Model.SONNET,
        ),
        AgentDefinition(
            id="opus-agent",
            description="Opus agent",
            preferred_model=Model.OPUS,
        ),
        AgentDefinition(
            id="inherit-agent",
            description="Inherit agent",
            preferred_model=Model.INHERIT,
        ),
    ]

    store = AgentFactoryStore(tmp_path)
    guard = store.file_guard()
    render_codex(tmp_path, agents, [], guard)

    # Check HAIKU -> "low"
    haiku_toml = tomllib.loads(
        (tmp_path / ".codex" / "agents" / "qag-haiku-agent.toml").read_text(encoding="utf-8")
    )
    assert haiku_toml["model_reasoning_effort"] == "low"

    # Check SONNET -> "medium"
    sonnet_toml = tomllib.loads(
        (tmp_path / ".codex" / "agents" / "qag-sonnet-agent.toml").read_text(encoding="utf-8")
    )
    assert sonnet_toml["model_reasoning_effort"] == "medium"

    # Check OPUS -> "high"
    opus_toml = tomllib.loads(
        (tmp_path / ".codex" / "agents" / "qag-opus-agent.toml").read_text(encoding="utf-8")
    )
    assert opus_toml["model_reasoning_effort"] == "high"

    # Check INHERIT -> "medium"
    inherit_toml = tomllib.loads(
        (tmp_path / ".codex" / "agents" / "qag-inherit-agent.toml").read_text(encoding="utf-8")
    )
    assert inherit_toml["model_reasoning_effort"] == "medium"


def test_render_codex_escapes_special_characters_in_toml(tmp_path: Path) -> None:
    """Test that double-quotes and backslashes in agent fields are properly escaped."""
    agent = AgentDefinition(
        id="special-agent",
        description='Agent with "quotes" and \\backslashes\\',
        scope='Scope with "double quotes"',
        when_to_use="When: use \\path\\to\\file",
    )

    store = AgentFactoryStore(tmp_path)
    guard = store.file_guard()
    render_codex(tmp_path, [agent], [], guard)

    agent_toml_path = tmp_path / ".codex" / "agents" / "qag-special-agent.toml"
    agent_toml_content = agent_toml_path.read_text(encoding="utf-8")

    # Should be able to parse the TOML without errors
    agent_toml = tomllib.loads(agent_toml_content)

    # Values should be unescaped after parsing
    assert "quotes" in agent_toml["description"]
    assert "backslashes" in agent_toml["description"]
    # scope, when_to_use, etc. are assembled into developer_instructions
    instructions = agent_toml["developer_instructions"]
    assert "double quotes" in instructions
    assert "path\\to\\file" in instructions


def test_render_codex_special_chars_in_skill_body(tmp_path: Path) -> None:
    """Test that special characters in skill body are preserved."""
    skill = SkillDefinition(
        id="special-skill",
        trigger="manual",
        body='# Skill with "quotes"\n\nAnd \\backslashes\\ in body.',
    )

    store = AgentFactoryStore(tmp_path)
    guard = store.file_guard()
    render_codex(tmp_path, [], [skill], guard)

    skill_md_path = tmp_path / ".agents" / "skills" / "special-skill" / "SKILL.md"
    content = skill_md_path.read_text(encoding="utf-8")

    # Content should be exactly as provided
    assert content == '# Skill with "quotes"\n\nAnd \\backslashes\\ in body.'


def test_render_codex_creates_config_toml_with_defaults(tmp_path: Path) -> None:
    """Test that .codex/config.toml is created with default values when it doesn't exist."""
    store = AgentFactoryStore(tmp_path)
    guard = store.file_guard()
    render_codex(tmp_path, [], [], guard)

    config_path = tmp_path / ".codex" / "config.toml"
    assert config_path.exists()

    config_content = config_path.read_text(encoding="utf-8")
    config = tomllib.loads(config_content)

    # Check default keys
    assert config["agents"]["max_depth"] == 1
    assert config["agents"]["max_threads"] == 3

    # Check MCP server configuration
    assert "mcp_servers" in config
    assert "quattroagents" in config["mcp_servers"]
    quattroagents_config = config["mcp_servers"]["quattroagents"]
    assert quattroagents_config["command"] == ".venv/bin/qagents"
    assert quattroagents_config["args"] == ["mcp", "serve"]
    assert quattroagents_config["cwd"] == "."
    assert quattroagents_config["startup_timeout_sec"] == 10


def test_render_codex_preserves_unrelated_config_keys(tmp_path: Path) -> None:
    """Test that existing unrelated keys in config.toml are preserved."""
    config_path = tmp_path / ".codex" / "config.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        'some_other_setting = true\nfoo = "bar"\nagents.max_depth = 5\n',
        encoding="utf-8",
    )

    store = AgentFactoryStore(tmp_path)
    guard = store.file_guard()
    render_codex(tmp_path, [], [], guard)

    updated_content = config_path.read_text(encoding="utf-8")
    config = tomllib.loads(updated_content)

    # Unrelated keys should be preserved
    assert config["some_other_setting"] is True
    assert config["foo"] == "bar"

    # MCP server config should be added/updated
    assert "mcp_servers" in config
    assert "quattroagents" in config["mcp_servers"]


def test_render_codex_writes_agents_md(tmp_path: Path) -> None:
    """Test that AGENTS.md is written and contains references to .codex/agents/ and .agents/skills/."""
    store = AgentFactoryStore(tmp_path)
    guard = store.file_guard()
    render_codex(tmp_path, [], [], guard)

    agents_md_path = tmp_path / "AGENTS.md"
    assert agents_md_path.exists()

    content = agents_md_path.read_text(encoding="utf-8")
    assert ".codex/agents/" in content
    assert ".agents/skills/" in content


def test_render_codex_regenerate_produces_identical_output(tmp_path: Path) -> None:
    """Test that regenerating with identical data produces identical output files."""
    agent = AgentDefinition(
        id="idempotent-agent",
        description="Test agent",
        preferred_model=Model.SONNET,
    )
    skill = SkillDefinition(
        id="idempotent-skill",
        trigger="manual",
        workflow=["Step 1", "Step 2"],
    )

    store = AgentFactoryStore(tmp_path)
    guard = store.file_guard()

    # First call
    render_codex(tmp_path, [agent], [skill], guard)
    agent_toml_path = tmp_path / ".codex" / "agents" / "qag-idempotent-agent.toml"
    skill_md_path = tmp_path / ".agents" / "skills" / "idempotent-skill" / "SKILL.md"
    config_path = tmp_path / ".codex" / "config.toml"

    first_agent_content = agent_toml_path.read_text(encoding="utf-8")
    first_skill_content = skill_md_path.read_text(encoding="utf-8")
    first_config_content = config_path.read_text(encoding="utf-8")

    # Second call with identical data
    guard2 = store.file_guard()
    render_codex(tmp_path, [agent], [skill], guard2)

    second_agent_content = agent_toml_path.read_text(encoding="utf-8")
    second_skill_content = skill_md_path.read_text(encoding="utf-8")
    second_config_content = config_path.read_text(encoding="utf-8")

    # Output should be identical
    assert first_agent_content == second_agent_content
    assert first_skill_content == second_skill_content
    assert first_config_content == second_config_content


def test_render_codex_skill_with_custom_body(tmp_path: Path) -> None:
    """Test that a skill with body set uses the body string instead of generated markdown."""
    custom_body = """# Custom Skill

This is a custom body that should be used as-is.

- Item 1
- Item 2
"""
    skill = SkillDefinition(
        id="custom-body-skill",
        trigger="manual",
        workflow=["Should be ignored"],  # This should be ignored when body is set
        inputs=["Should be ignored"],  # These too
        body=custom_body,
    )

    store = AgentFactoryStore(tmp_path)
    guard = store.file_guard()
    render_codex(tmp_path, [], [skill], guard)

    skill_md_path = tmp_path / ".agents" / "skills" / "custom-body-skill" / "SKILL.md"
    content = skill_md_path.read_text(encoding="utf-8")

    # Content should be exactly the custom body, not auto-generated
    assert content == custom_body
    assert "Workflow" not in content  # Should not have auto-generated sections


def test_render_codex_agent_fields_in_developer_instructions(tmp_path: Path) -> None:
    """Test that agent fields are properly assembled into developer_instructions TOML field."""
    agent = AgentDefinition(
        id="full-agent",
        description="Full featured agent",
        scope="Primary responsibility",
        when_to_use="When X happens",
        when_not_to_use="When Y happens",
        completion_criteria=["Criterion 1", "Criterion 2"],
        constraints=["Constraint 1", "Constraint 2"],
    )

    store = AgentFactoryStore(tmp_path)
    guard = store.file_guard()
    render_codex(tmp_path, [agent], [], guard)

    agent_toml_path = tmp_path / ".codex" / "agents" / "qag-full-agent.toml"
    agent_toml = tomllib.loads(agent_toml_path.read_text(encoding="utf-8"))

    instructions = agent_toml["developer_instructions"]
    # All these parts should be in the instructions
    assert "Primary responsibility" in instructions
    assert "When X happens" in instructions
    assert "When Y happens" in instructions
    assert "Criterion 1" in instructions
    assert "Constraint 1" in instructions


def test_render_codex_multiple_agents_and_skills(tmp_path: Path) -> None:
    """Test render_codex with multiple agents and skills."""
    agents = [
        AgentDefinition(
            id="agent-1",
            description="First agent",
            preferred_model=Model.HAIKU,
        ),
        AgentDefinition(
            id="agent-2",
            description="Second agent",
            preferred_model=Model.SONNET,
        ),
    ]
    skills = [
        SkillDefinition(id="skill-1", trigger="manual"),
        SkillDefinition(id="skill-2", trigger="automatic"),
    ]

    store = AgentFactoryStore(tmp_path)
    guard = store.file_guard()
    results = render_codex(tmp_path, agents, skills, guard)

    # Should have: 2 agents + 2 skills + 1 config + 1 AGENTS.md = 6 results
    assert len(results) == 6

    # All should be written
    assert all(r.status == "written" for r in results)

    # Verify both agent files exist
    assert (tmp_path / ".codex" / "agents" / "qag-agent-1.toml").exists()
    assert (tmp_path / ".codex" / "agents" / "qag-agent-2.toml").exists()

    # Verify both skill files exist
    assert (tmp_path / ".agents" / "skills" / "skill-1" / "SKILL.md").exists()
    assert (tmp_path / ".agents" / "skills" / "skill-2" / "SKILL.md").exists()

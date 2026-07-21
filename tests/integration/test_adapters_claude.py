import json
from pathlib import Path

from quattroagents.adapters.claude import render_claude
from quattroagents.domain import AgentDefinition, AgentMode, Model, SkillDefinition
from quattroagents.persistence import AgentFactoryStore


def test_render_claude_writes_agent_and_skill_markdown_files(tmp_path: Path) -> None:
    agent = AgentDefinition(
        id="test-agent",
        description="A test agent",
        responsibilities=["Responsibility 1", "Responsibility 2"],
        scope="Global scope",
        when_to_use="When needed",
        when_not_to_use="When not needed",
        completion_criteria=["Criteria 1"],
        preferred_model=Model.HAIKU,
        mode=AgentMode.READ_ONLY,
    )
    skill = SkillDefinition(
        id="test-skill",
        trigger="on_demand",
        workflow=["Step 1", "Step 2"],
        inputs=["Input 1"],
        outputs=["Output 1"],
    )

    store = AgentFactoryStore(tmp_path)
    guard = store.file_guard()

    render_claude(tmp_path, [agent], [skill], guard)

    # Verify files exist
    agent_file = tmp_path / ".claude" / "agents" / "qag-test-agent.md"
    skill_file = tmp_path / ".claude" / "skills" / "test-skill" / "SKILL.md"

    assert agent_file.exists()
    assert skill_file.exists()

    # Verify agent frontmatter
    agent_content = agent_file.read_text()
    assert "name: qag-test-agent" in agent_content
    assert "description: A test agent" in agent_content
    assert "model: haiku" in agent_content
    assert "mode: read_only" in agent_content
    assert "- Responsibility 1" in agent_content
    assert "- Responsibility 2" in agent_content

    # Verify skill frontmatter
    skill_content = skill_file.read_text()
    assert "name: test-skill" in skill_content
    assert "trigger: on_demand" in skill_content
    assert "1. Step 1" in skill_content
    assert "2. Step 2" in skill_content


def test_render_claude_writes_handoff_section_with_inputs_and_outputs(tmp_path: Path) -> None:
    agent = AgentDefinition(
        id="test-agent",
        description="A test agent",
        completion_criteria=["Criteria 1"],
        expected_inputs=["repo-map.json: directory tree summary"],
        expected_outputs=["test-report.json: pass/fail counts"],
    )

    store = AgentFactoryStore(tmp_path)
    guard = store.file_guard()

    render_claude(tmp_path, [agent], [], guard)

    agent_content = (tmp_path / ".claude" / "agents" / "qag-test-agent.md").read_text()

    assert "## Handoff" in agent_content
    assert "- Reads:" in agent_content
    assert "  - repo-map.json: directory tree summary" in agent_content
    assert "- Produces:" in agent_content
    assert "  - test-report.json: pass/fail counts" in agent_content


def test_render_claude_writes_handoff_section_with_none_declared(tmp_path: Path) -> None:
    agent = AgentDefinition(id="test-agent", description="Test", completion_criteria=["C"])

    store = AgentFactoryStore(tmp_path)
    guard = store.file_guard()

    render_claude(tmp_path, [agent], [], guard)

    agent_content = (tmp_path / ".claude" / "agents" / "qag-test-agent.md").read_text()

    assert "## Handoff" in agent_content
    assert "- Reads: none declared." in agent_content
    assert "- Produces: none declared." in agent_content


def test_render_claude_writes_settings_json_with_valid_structure(tmp_path: Path) -> None:
    agent = AgentDefinition(id="test-agent", description="Test")

    store = AgentFactoryStore(tmp_path)
    guard = store.file_guard()

    render_claude(tmp_path, [agent], [], guard)

    settings_file = tmp_path / ".claude" / "settings.json"
    assert settings_file.exists()

    settings = json.loads(settings_file.read_text())

    # Verify required keys
    assert "permissions" in settings
    assert "hooks" in settings

    # Verify permissions structure
    assert "deny" in settings["permissions"]
    assert isinstance(settings["permissions"]["deny"], list)

    # Verify hooks structure
    assert isinstance(settings["hooks"], dict)
    assert "PreToolUse" in settings["hooks"]
    assert isinstance(settings["hooks"]["PreToolUse"], list)


def test_render_claude_writes_mcp_json_with_valid_structure(tmp_path: Path) -> None:
    agent = AgentDefinition(id="test-agent", description="Test")

    store = AgentFactoryStore(tmp_path)
    guard = store.file_guard()

    render_claude(tmp_path, [agent], [], guard)

    mcp_file = tmp_path / ".mcp.json"
    assert mcp_file.exists()

    mcp = json.loads(mcp_file.read_text())

    # Verify required keys
    assert "mcpServers" in mcp
    assert "quattroagents" in mcp["mcpServers"]

    quattroagents_config = mcp["mcpServers"]["quattroagents"]
    assert "command" in quattroagents_config
    assert quattroagents_config["command"] == "qagents"
    assert "args" in quattroagents_config


def test_render_claude_preserves_existing_settings_json_keys(tmp_path: Path) -> None:
    agent = AgentDefinition(id="test-agent", description="Test")

    # Pre-create settings.json with an unrelated key
    settings_file = tmp_path / ".claude" / "settings.json"
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    existing_settings = {"customKey": "customValue"}
    settings_file.write_text(json.dumps(existing_settings))

    store = AgentFactoryStore(tmp_path)
    guard = store.file_guard()

    render_claude(tmp_path, [agent], [], guard)

    # Verify the custom key is preserved
    settings = json.loads(settings_file.read_text())
    assert settings["customKey"] == "customValue"

    # Verify new keys are present
    assert "permissions" in settings
    assert "hooks" in settings


def test_render_claude_idempotent_on_identical_invocations(tmp_path: Path) -> None:
    agent = AgentDefinition(
        id="test-agent",
        description="A test agent",
        responsibilities=["Responsibility 1"],
        scope="Global scope",
        when_to_use="When needed",
        when_not_to_use="When not needed",
        completion_criteria=["Criteria 1"],
        preferred_model=Model.HAIKU,
        mode=AgentMode.READ_ONLY,
    )
    skill = SkillDefinition(
        id="test-skill",
        trigger="on_demand",
        workflow=["Step 1"],
        inputs=["Input 1"],
        outputs=["Output 1"],
    )

    store = AgentFactoryStore(tmp_path)
    guard = store.file_guard()

    # First render
    results1 = render_claude(tmp_path, [agent], [skill], guard)

    # Verify first render has "written" status
    assert all(r.status == "written" for r in results1)

    # Verify files are created with correct content
    agent_file = tmp_path / ".claude" / "agents" / "qag-test-agent.md"
    skill_file = tmp_path / ".claude" / "skills" / "test-skill" / "SKILL.md"
    agent_content_1 = agent_file.read_text()
    skill_content_1 = skill_file.read_text()

    # Second render with identical agents/skills and a fresh guard
    guard2 = store.file_guard()
    results2 = render_claude(tmp_path, [agent], [skill], guard2)

    # Verify files still exist and content is identical
    agent_content_2 = agent_file.read_text()
    skill_content_2 = skill_file.read_text()
    assert agent_content_1 == agent_content_2
    assert skill_content_1 == skill_content_2

    # Both calls should complete successfully (status is "written" for both)
    # because guard.write() returns "written" whenever a file is successfully written
    assert all(r.status == "written" for r in results2)


def test_render_claude_detects_conflict_on_manual_edit(tmp_path: Path) -> None:
    agent1 = AgentDefinition(
        id="test-agent",
        description="Original description",
        responsibilities=["Original responsibility"],
        scope="Original scope",
        when_to_use="Original when_to_use",
        when_not_to_use="Original when_not_to_use",
        completion_criteria=["Original criteria"],
        preferred_model=Model.HAIKU,
        mode=AgentMode.READ_ONLY,
    )

    store = AgentFactoryStore(tmp_path)
    guard = store.file_guard()

    # First render
    render_claude(tmp_path, [agent1], [], guard)

    agent_file = tmp_path / ".claude" / "agents" / "qag-test-agent.md"
    original_content = agent_file.read_text()

    # Manually edit the file
    edited_content = original_content.replace("Original description", "Manually edited description")
    agent_file.write_text(edited_content)

    # Now render again with a different agent (same id, different content)
    agent2 = AgentDefinition(
        id="test-agent",
        description="New description",
        responsibilities=["New responsibility"],
        scope="New scope",
        when_to_use="New when_to_use",
        when_not_to_use="New when_not_to_use",
        completion_criteria=["New criteria"],
        preferred_model=Model.SONNET,
        mode=AgentMode.WRITE,
    )

    guard2 = store.file_guard()
    results = render_claude(tmp_path, [agent2], [], guard2)

    # Find the result for the agent file
    agent_result = next(r for r in results if r.relative_path == ".claude/agents/qag-test-agent.md")

    # Verify conflict is detected
    assert agent_result.status == "conflict"
    assert agent_result.previous_content is not None
    assert agent_result.attempted_content is not None
    assert "Manually edited" in agent_result.previous_content
    assert "New description" in agent_result.attempted_content


def test_render_claude_writes_global_files_even_with_empty_agents_and_skills(
    tmp_path: Path,
) -> None:
    store = AgentFactoryStore(tmp_path)
    guard = store.file_guard()

    results = render_claude(tmp_path, [], [], guard)

    # Verify settings.json and mcp.json are written
    settings_file = tmp_path / ".claude" / "settings.json"
    mcp_file = tmp_path / ".mcp.json"

    assert settings_file.exists()
    assert mcp_file.exists()

    # Verify results include settings and mcp writes
    result_paths = [r.relative_path for r in results]
    assert ".claude/settings.json" in result_paths
    assert ".mcp.json" in result_paths

    # Verify both are valid JSON
    assert json.loads(settings_file.read_text())
    assert json.loads(mcp_file.read_text())


def test_render_claude_uses_skill_body_when_provided(tmp_path: Path) -> None:
    custom_body = "---\nname: custom-skill\ntrigger: on_demand\n---\n\n## Custom Section\nThis is custom content.\n"
    skill = SkillDefinition(
        id="test-skill",
        trigger="on_demand",
        workflow=["This should be ignored"],
        inputs=["This should be ignored"],
        outputs=["This should be ignored"],
        body=custom_body,
    )

    store = AgentFactoryStore(tmp_path)
    guard = store.file_guard()

    render_claude(tmp_path, [], [skill], guard)

    skill_file = tmp_path / ".claude" / "skills" / "test-skill" / "SKILL.md"
    assert skill_file.exists()

    content = skill_file.read_text()

    # Verify the custom body is written exactly as provided
    assert content == custom_body

    # Verify workflow/inputs/outputs are NOT in the output
    assert "This should be ignored" not in content
    assert "## Workflow" not in content
    assert "## Inputs" not in content
    assert "## Outputs" not in content

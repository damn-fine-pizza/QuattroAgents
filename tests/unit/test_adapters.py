import json
import tomllib
from pathlib import Path

from quattroagents.adapters.registry import render_claude, render_codex


def test_render_codex_preserves_other_mcp_servers_and_generates_valid_roles(tmp_path: Path) -> None:
    config = tmp_path / ".codex/config.toml"
    config.parent.mkdir()
    config.write_text(
        "agents.max_depth = 2\n\n"
        "[mcp_servers.openaiDeveloperDocs]\n"
        'url = "https://developers.openai.com/mcp"\n\n'
        "[mcp_servers.quattroagents]\n"
        'command = "qagents"\n'
        'args = ["mcp", "serve"]\n'
    )

    render_codex(tmp_path)

    generated = config.read_text()
    parsed = tomllib.loads(generated)
    assert parsed["agents"]["max_depth"] == 2
    assert parsed["mcp_servers"]["openaiDeveloperDocs"]["url"] == (
        "https://developers.openai.com/mcp"
    )
    assert parsed["mcp_servers"]["quattroagents"]["command"] == ".venv/bin/qagents"
    assert generated.count("[mcp_servers.quattroagents]") == 1
    for name in ("bounded-worker", "semantic-reviewer", "architecture-adjudicator"):
        role = tomllib.loads((tmp_path / f".codex/agents/{name}.toml").read_text())
        assert role["name"] == name
        assert role["description"]
        assert role["developer_instructions"]
        assert role["model_reasoning_effort"]


def test_render_claude_generates_agents_skills_and_mcp_configuration(tmp_path: Path) -> None:
    render_claude(tmp_path)

    settings = json.loads((tmp_path / ".claude/settings.json").read_text())
    assert settings["permissions"]["deny"] == ["Bash(git push --force:*)"]
    assert settings["hooks"]["PreToolUse"]
    mcp = json.loads((tmp_path / ".mcp.json").read_text())
    assert mcp["mcpServers"]["quattroagents"]["command"] == "qagents"
    for name in ("bounded-worker", "semantic-reviewer", "architecture-adjudicator"):
        assert f"name: {name}" in (tmp_path / f".claude/agents/{name}.md").read_text()
    assert (tmp_path / ".claude/skills/qagents-review/SKILL.md").exists()

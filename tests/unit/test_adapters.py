import json
import tomllib
from pathlib import Path

from quattroagents.adapters.registry import render_claude, render_codex
from quattroagents.core.agent_synthesis import DEFAULT_MANIFEST


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
    agents = {
        "bounded-worker": "low",
        "semantic-reviewer": "medium",
        "architecture-adjudicator": "high",
    }
    for name, reasoning_effort in agents.items():
        role = tomllib.loads((tmp_path / f".codex/agents/{name}.toml").read_text())
        assert role["name"] == name
        assert role["description"]
        assert role["developer_instructions"]
        assert role["model_reasoning_effort"] == reasoning_effort
        assert role["model_reasoning_effort"] not in {"small", "large"}

    agents_instructions = (tmp_path / "AGENTS.md").read_text()
    assert "useful, independent work" in agents_instructions
    assert "non-overlapping file or contract scopes" in agents_instructions
    assert "`spawn_agent`, `wait_agent`, `send_message`, and `followup_task`" in agents_instructions
    assert "no provider-neutral or QuattroAgents launcher" in agents_instructions
    assert "it does not spawn or wait for Codex agents" in agents_instructions
    assert "does not create, select, or promise QuattroAgents workers" in agents_instructions
    assert "Wait for every subagent in a wave" in agents_instructions
    assert "claim its contract and acquire a lease" in agents_instructions
    assert "independent reviewer who did not implement" in agents_instructions

    bounded_worker = tomllib.loads((tmp_path / ".codex/agents/bounded-worker.toml").read_text())
    assert "Codex coordinator's assigned packet" in bounded_worker["developer_instructions"]
    assert "result envelope" in bounded_worker["developer_instructions"]

    orchestration_skill = (tmp_path / ".agents/skills/qagents-orchestrate/SKILL.md").read_text()
    assert "Ask only material questions whose answers are missing" in orchestration_skill
    assert "continue the QuattroAgents lifecycle autonomously" in orchestration_skill
    assert "Stop only for a genuine blocker or a human decision" in orchestration_skill
    assert "task contract and confirmed interview" in orchestration_skill
    assert "claim tasks and acquire leases before dispatch" in orchestration_skill
    assert "independent reviewer before completion" in orchestration_skill
    assert "does not dispatch or wait for agents" in orchestration_skill
    assert "daemon, generic dispatcher, automatic setup, rendering, or" in orchestration_skill
    assert "remote service, or LLM runner" in orchestration_skill
    assert "only a concurrency ceiling" in orchestration_skill


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
    orchestration_skill = (tmp_path / ".claude/skills/qagents-orchestrate/SKILL.md").read_text()
    assert "Ask only material questions whose answers are missing" in orchestration_skill
    assert "continue the QuattroAgents lifecycle autonomously" in orchestration_skill
    assert "Use provider-native subagents only" in orchestration_skill
    assert "QuattroAgents MCP is the control plane only" in orchestration_skill


def _custom_manifest() -> dict:
    return {
        "schema_version": 1,
        "roles": [
            {
                "name": "bounded-worker",
                "tier": "small",
                "source": "adhoc",
                "description": "Custom description for this project.",
                "instructions": "Custom instructions mentioning rtk and codebase-memory-mcp.",
                "claude_model": "sonnet",
                "claude_max_turns": 12,
            }
        ],
        "skills": [
            {
                "name": "qagents-custom",
                "source": "adhoc",
                "body": "---\nname: qagents-custom\ndescription: custom\n---\n\nCustom body.\n",
            }
        ],
        "rationale": {},
    }


def test_render_codex_is_manifest_driven(tmp_path: Path) -> None:
    manifest = _custom_manifest()

    render_codex(tmp_path, manifest)

    role = tomllib.loads((tmp_path / ".codex/agents/bounded-worker.toml").read_text())
    assert role["description"] == "Custom description for this project."
    assert "rtk and codebase-memory-mcp" in role["developer_instructions"]
    assert (tmp_path / ".agents/skills/qagents-custom/SKILL.md").read_text() == (
        "---\nname: qagents-custom\ndescription: custom\n---\n\nCustom body.\n"
    )
    assert not (tmp_path / ".codex/agents/semantic-reviewer.toml").exists()


def test_render_claude_is_manifest_driven(tmp_path: Path) -> None:
    manifest = _custom_manifest()

    render_claude(tmp_path, manifest)

    role_file = (tmp_path / ".claude/agents/bounded-worker.md").read_text()
    assert "description: Custom description for this project." in role_file
    assert "Custom instructions mentioning rtk and codebase-memory-mcp." in role_file
    assert (tmp_path / ".claude/skills/qagents-custom/SKILL.md").read_text() == (
        "---\nname: qagents-custom\ndescription: custom\n---\n\nCustom body.\n"
    )


def test_render_codex_and_claude_without_manifest_falls_back_to_default_manifest(
    tmp_path: Path,
) -> None:
    render_codex(tmp_path)
    render_claude(tmp_path)

    for role in DEFAULT_MANIFEST["roles"]:
        assert (tmp_path / f".codex/agents/{role['name']}.toml").exists()
        assert (tmp_path / f".claude/agents/{role['name']}.md").exists()
    for skill in DEFAULT_MANIFEST["skills"]:
        assert (tmp_path / f".agents/skills/{skill['name']}/SKILL.md").exists()
        assert (tmp_path / f".claude/skills/{skill['name']}/SKILL.md").exists()

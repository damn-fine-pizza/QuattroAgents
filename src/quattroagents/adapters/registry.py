from __future__ import annotations

import json
from pathlib import Path

from quattroagents.core.configuration import backup, merge_json
from quattroagents.core.gates import PROTECTED


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    backup(root, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _skill(name: str) -> str:
    return f"---\nname: {name}\ndescription: QuattroAgents {name} workflow\n---\n\nRead .quattroagents/ first. Keep L0/L1 concise; store L2 evidence by reference.\n"


def render_codex(root: Path) -> list[str]:
    _write(
        root,
        "AGENTS.md",
        "# QuattroAgents\n\nState lives in `.quattroagents/`. Route by tier, use task contracts, keep L0/L1 concise, and escalate protected-kernel changes. Validate with `python -m quattroagents validate --json`.\n",
    )
    _write(
        root,
        ".codex/config.toml",
        'agents.max_depth = 1\nagents.max_threads = 3\n\n[mcp_servers.quattroagents]\ncommand = "qagents"\nargs = ["mcp", "serve", "--project", "."]\ncwd = "."\nstartup_timeout_sec = 10\n',
    )
    for name in (
        "qagents-bootstrap",
        "qagents-plan",
        "qagents-execute",
        "qagents-review",
        "qagents-reconfigure",
        "qagents-benchmark",
    ):
        _write(root, f".agents/skills/{name}/SKILL.md", _skill(name))
    for name, tier in (
        ("bounded-worker", "small"),
        ("semantic-reviewer", "medium"),
        ("architecture-adjudicator", "large"),
    ):
        _write(
            root,
            f".codex/agents/{name}.toml",
            f'name = "{name}"\nmodel_reasoning_effort = "{tier}"\n',
        )
    return ["AGENTS.md", ".codex/config.toml", ".agents/skills", ".codex/agents"]


def render_claude(root: Path) -> list[str]:
    _write(
        root,
        "CLAUDE.md",
        "# QuattroAgents\n\nCanonical state is `.quattroagents/`; generated provider files are derived. Use task contracts and references, not copied transcripts. Protected paths require human approval.\n",
    )
    settings = {
        "permissions": {"deny": ["Bash(git push --force:*)"]},
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Edit|Write",
                    "hooks": [{"type": "command", "command": "qagents validate --json"}],
                }
            ]
        },
    }
    settings_path = root / ".claude/settings.json"
    existing = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    _write(
        root, ".claude/settings.json", json.dumps(merge_json(existing, settings), indent=2) + "\n"
    )
    _write(
        root,
        ".mcp.json",
        json.dumps(
            {
                "mcpServers": {
                    "quattroagents": {
                        "command": "qagents",
                        "args": ["mcp", "serve", "--project", "."],
                    }
                }
            },
            indent=2,
        )
        + "\n",
    )
    for name, model, turns, effort in (
        ("bounded-worker", "sonnet", 12, "low"),
        ("semantic-reviewer", "sonnet", 20, "medium"),
        ("architecture-adjudicator", "opus", 24, "high"),
    ):
        _write(
            root,
            f".claude/agents/{name}.md",
            f"---\nname: {name}\ndescription: Use for {name.replace('-', ' ')} tasks.\nmodel: {model}\ntools: Read, Edit, Write, Bash\nmaxTurns: {turns}\neffort: {effort}\n---\n\nTier is authoritative in `.quattroagents/fleet.json`. Escalate protected paths: {', '.join(PROTECTED[:2])}.\n",
        )
    for name in (
        "qagents-bootstrap",
        "qagents-plan",
        "qagents-execute",
        "qagents-review",
        "qagents-reconfigure",
        "qagents-benchmark",
    ):
        _write(root, f".claude/skills/{name}/SKILL.md", _skill(name))
    return ["CLAUDE.md", ".claude", ".mcp.json"]


def render(root: Path, providers: list[str]) -> list[str]:
    files: list[str] = []
    if "codex" in providers:
        files.extend(render_codex(root))
    if "claude" in providers:
        files.extend(render_claude(root))
    return files

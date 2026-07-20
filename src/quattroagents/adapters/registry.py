from __future__ import annotations

import json
import re
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


def _replace_toml_table(existing: str, header: str, replacement: str) -> str:
    pattern = rf"(?ms)^{re.escape(header)}\n.*?(?=^\[|\Z)"
    remaining = re.sub(pattern, "", existing).strip()
    return f"{remaining}\n\n{replacement}" if remaining else replacement


def render_codex(root: Path) -> list[str]:
    _write(
        root,
        "AGENTS.md",
        "# QuattroAgents\n\nState lives in `.quattroagents/`. Route by tier, use task contracts, keep L0/L1 concise, and escalate protected-kernel changes. Validate with `python -m quattroagents validate --format json`.\n",
    )
    config_path = root / ".codex/config.toml"
    existing_config = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    default_config = "agents.max_depth = 1\nagents.max_threads = 3"
    quattroagents_server = (
        "[mcp_servers.quattroagents]\n"
        'command = ".venv/bin/qagents"\n'
        'args = ["mcp", "serve", "--project", "."]\n'
        'cwd = "."\n'
        "startup_timeout_sec = 10\n"
    )
    _write(
        root,
        ".codex/config.toml",
        _replace_toml_table(
            existing_config or default_config,
            "[mcp_servers.quattroagents]",
            quattroagents_server,
        ),
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
    for name, tier, description, instructions in (
        (
            "bounded-worker",
            "small",
            "Implements explicitly scoped, low-risk changes.",
            "Implement only the assigned task, preserve unrelated changes, and report verification.",
        ),
        (
            "semantic-reviewer",
            "medium",
            "Reviews behavioral correctness, compatibility, and test coverage.",
            "Do not modify files; report actionable findings with evidence.",
        ),
        (
            "architecture-adjudicator",
            "large",
            "Reviews architectural trade-offs and protected-boundary impact.",
            "Do not modify files; identify decisions and approvals required for protected changes.",
        ),
    ):
        _write(
            root,
            f".codex/agents/{name}.toml",
            f'name = "{name}"\n'
            f'description = "{description}"\n'
            f'model_reasoning_effort = "{tier}"\n'
            f'developer_instructions = "{instructions}"\n',
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
                    "hooks": [{"type": "command", "command": "qagents validate --format json"}],
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

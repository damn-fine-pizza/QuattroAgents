from __future__ import annotations

import json
import re
from pathlib import Path

from quattroagents.core.configuration import backup, merge_json
from quattroagents.core.gates import PROTECTED

_CODEX_REASONING_EFFORT = {
    "small": "low",
    "medium": "medium",
    "large": "high",
    "long_horizon": "xhigh",
}

_CODEX_COORDINATOR_HANDOFF = (
    "Codex's coordinator manually dispatches and manages subagents with the native "
    "`spawn_agent`, `wait_agent`, `send_message`, and `followup_task` tools; there is "
    "no provider-neutral or QuattroAgents launcher. Give each worker only its packet: "
    "objective, requirements, allowed files, context and evidence references, claim and "
    "lease identity, acceptance commands, and result-envelope format. QuattroAgents MCP "
    "is the local control plane for tasks, claims, leases, runs, snapshots, artifacts, "
    "and evidence; it does not spawn or wait for Codex agents. "
)


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
        "# QuattroAgents\n\n"
        "State lives in `.quattroagents/`. Route by tier, use task contracts, keep "
        "L0/L1 concise, and escalate protected-kernel changes. Validate with "
        "`python -m quattroagents validate --format json`.\n\n"
        "Work in waves. Before beginning a task, claim its contract and acquire a "
        "lease; renew the lease while working and release it when reporting. Dispatch "
        "native subagents in the same wave only for useful, independent work with "
        "non-overlapping file or contract scopes. "
        + _CODEX_COORDINATOR_HANDOFF
        + "`agents.max_threads` is only a concurrency ceiling for selected eligible "
        "work: it does not create, select, or promise QuattroAgents workers. Wait for "
        "every subagent in a wave before starting dependent work, then consolidate their "
        "evidence. Assign an independent reviewer who did not implement the change before "
        "completion.\n",
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
            "Work only from the Codex coordinator's assigned packet. Claim and lease the "
            "assigned contract, implement only that bounded task, preserve unrelated "
            "changes, and report the packet's result envelope with changed files and "
            "verification.",
        ),
        (
            "semantic-reviewer",
            "medium",
            "Reviews behavioral correctness, compatibility, and test coverage.",
            "Independently review a final diff and its acceptance evidence for work you "
            "did not implement. Check behavioral correctness, compatibility, claims and "
            "lease discipline, and test coverage. Do not modify files; report actionable "
            "findings with evidence.",
        ),
        (
            "architecture-adjudicator",
            "large",
            "Reviews architectural trade-offs and protected-boundary impact.",
            "Assess architectural trade-offs and protected-boundary impact before "
            "implementation. Do not modify files; identify recommended decisions and "
            "approvals required for protected changes.",
        ),
    ):
        _write(
            root,
            f".codex/agents/{name}.toml",
            f'name = "{name}"\n'
            f'description = "{description}"\n'
            f'model_reasoning_effort = "{_CODEX_REASONING_EFFORT[tier]}"\n'
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

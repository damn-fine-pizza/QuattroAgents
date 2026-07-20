from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from quattroagents.core.agent_synthesis import DEFAULT_MANIFEST
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


def _render_skill_body(entry: dict[str, Any]) -> str:
    if entry.get("body") is not None:
        return str(entry["body"])
    return _default_skill_body(entry["name"])


def _toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _default_skill_body(name: str) -> str:
    header = (
        f"---\nname: {name}\ndescription: QuattroAgents {name} workflow\n---\n\n"
        "Read .quattroagents/ first. Keep L0/L1 concise; store L2 evidence by reference.\n"
    )
    if name != "qagents-orchestrate":
        return header
    return (
        header + "\nAsk only material questions whose answers are missing from the task, project "
        "state, or confirmed interview. Once those answers are available, continue the "
        "QuattroAgents lifecycle autonomously; do not pause for routine status checks or "
        "permission to perform normal in-scope work. Stop only for a genuine blocker or "
        "a human decision that materially changes scope, risk, or protected-path approval.\n\n"
        "Create or validate the task contract and confirmed interview, plan non-overlapping "
        "work and dependency waves, then claim tasks and acquire leases before dispatch. "
        "Use provider-native subagents only for useful independent packets. Collect result "
        "envelopes and evidence, run acceptance gates, record run snapshots, and assign an "
        "independent reviewer before completion.\n\n"
        "QuattroAgents MCP is the control plane only for tasks, claims, leases, runs, "
        "snapshots, artifacts, and evidence; it does not dispatch or wait for agents. Do "
        "not add or rely on a daemon, generic dispatcher, automatic setup, rendering, or "
        "configuration, remote service, or LLM runner. `agents.max_threads` is only a "
        "concurrency ceiling for already selected eligible work; it does not create, select, "
        "or promise workers.\n"
    )


def _replace_toml_table(existing: str, header: str, replacement: str) -> str:
    pattern = rf"(?ms)^{re.escape(header)}\n.*?(?=^\[|\Z)"
    remaining = re.sub(pattern, "", existing).strip()
    return f"{remaining}\n\n{replacement}" if remaining else replacement


def render_codex(root: Path, manifest: dict[str, Any] | None = None) -> list[str]:
    manifest = manifest if manifest is not None else DEFAULT_MANIFEST
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
    for skill in manifest["skills"]:
        _write(root, f".agents/skills/{skill['name']}/SKILL.md", _render_skill_body(skill))
    for role in manifest["roles"]:
        _write(
            root,
            f".codex/agents/{role['name']}.toml",
            f'name = "{_toml_string(role["name"])}"\n'
            f'description = "{_toml_string(role["description"])}"\n'
            f'model_reasoning_effort = "{_CODEX_REASONING_EFFORT[role["tier"]]}"\n'
            f'developer_instructions = "{_toml_string(role["instructions"])}"\n',
        )
    return ["AGENTS.md", ".codex/config.toml", ".agents/skills", ".codex/agents"]


def render_claude(root: Path, manifest: dict[str, Any] | None = None) -> list[str]:
    manifest = manifest if manifest is not None else DEFAULT_MANIFEST
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
    for role in manifest["roles"]:
        effort = _CODEX_REASONING_EFFORT[role["tier"]]
        _write(
            root,
            f".claude/agents/{role['name']}.md",
            f"---\nname: {role['name']}\ndescription: {role['description']}\n"
            f"model: {role['claude_model']}\ntools: Read, Edit, Write, Bash\n"
            f"maxTurns: {role['claude_max_turns']}\neffort: {effort}\n---\n\n"
            f"{role['instructions']}\n\n"
            f"Tier is authoritative in `.quattroagents/fleet.json`. "
            f"Escalate protected paths: {', '.join(PROTECTED[:2])}.\n",
        )
    for skill in manifest["skills"]:
        _write(root, f".claude/skills/{skill['name']}/SKILL.md", _render_skill_body(skill))
    return ["CLAUDE.md", ".claude", ".mcp.json"]


def render(root: Path, providers: list[str], manifest: dict[str, Any] | None = None) -> list[str]:
    manifest = manifest if manifest is not None else DEFAULT_MANIFEST
    files: list[str] = []
    if "codex" in providers:
        files.extend(render_codex(root, manifest))
    if "claude" in providers:
        files.extend(render_claude(root, manifest))
    return files

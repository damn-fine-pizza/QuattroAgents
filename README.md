# QuattroAgents

QuattroAgents is an MCP server and CLI that analyzes a target repository and generates or updates tailored Claude and Codex agents and skills on disk. It re-runs safely: it tracks the hash of what it last generated per file, so it can distinguish "unchanged," "would update," and "conflict — you hand-edited this" apart, and never silently clobbers manual edits.

## Install and quick start

```bash
pip install quattroagents
qagents setup --project /path/to/target --providers claude,codex
qagents doctor
qagents validate
```

The tool generates agents and skills in provider-specific directories (`.claude/`, `.codex/`) alongside a canonical state directory (`.agent-factory/`) that tracks project profile snapshots, decisions, interview sessions, and generated manifests.

## Command reference

| Command | Purpose |
|---------|---------|
| `analyze` | Scan the target repository and detect language, framework, tools. |
| `setup` | Analyze project, optionally interview user, and generate/update agents and skills for selected providers. |
| `validate` | Check generated agents and skills for consistency and tooling availability. |
| `diff` | Show what files would be written/updated/created by the next setup without modifying disk. |
| `doctor` | Report version, Python, environment, state directory, and available tools (Claude, Codex, rtk, codebase-memory-mcp). |
| `agents list` | List all generated agents. |
| `agents generate` | Synthesize agents from project profile and active decisions. |
| `skills generate` | Synthesize skills (Claude and Codex) for the generated agents. |
| `decisions list` | Show all recorded decisions, optionally filtered by status or scope. |
| `decisions record` | Manually record a decision (user, repository, inferred, or imported). |
| `decisions reopen` | Mark a decision as uncertain and re-examine it. |
| `task prepare` | Prepare an ad-hoc task-temporary agent. |
| `swarm plan` | Generate a deterministic, reference-only swarm execution plan. |
| `interview start` | Begin a structured interview session (initial setup, repository change, task prep, etc.). |
| `interview state` | Fetch current interview session state and progress. |
| `interview next` | Retrieve the next set of questions for the active interview. |
| `interview answer` | Submit answers to interview questions. |
| `interview summary` | Get a human-readable review of interview responses. |
| `interview confirm` | Confirm the interview and convert answers into decisions. |
| `interview gaps` | List open knowledge gaps from the interview. |
| `interview conflicts` | Identify conflicting decisions from repository and interview. |
| `interview resolve` | Resolve a specific decision conflict. |
| `mcp serve` | Start the stdio JSON-RPC server (21 tools). |
| `mcp list` | Show available MCP tools. |

All commands accept `--project /path` to target a specific repository; default is the current directory. Every command outputs JSON; add `--help` to see all flags.

## MCP Server

```bash
qagents mcp serve
```

Starts a stdio JSON-RPC server that exposes 21 tools for analyzing projects, managing decisions, conducting interviews, and generating agents and skills. Suitable for use with Claude Code's MCP integration or other MCP clients. See `docs/mcp.md` for tool descriptions.

## State directory (`.agent-factory/`)

- `project-profile.json` — latest repository scan (languages, frameworks, tools, sizes).
- `history/` — timestamped profile snapshots for change detection.
- `decisions/` — one JSON file per decision (immutable, with supersedes/superseded_by chains).
- `sessions/` — interview sessions and their questions, answers, gaps, conflicts.
- `generated/` — manifest of synthesized agents and skills.
- `overrides/` — last-generated-content hash per output file (detects manual edits).

## Developing this repository

Install and bootstrap:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
scripts/setup.sh
```

Run tests and checks (see [CONTRIBUTING.md](CONTRIBUTING.md) for details):

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check . && .venv/bin/python -m ruff format --check .
.venv/bin/python -m mypy src
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for full requirements and [docs/](docs/) for architecture, benchmarking, and provider details.

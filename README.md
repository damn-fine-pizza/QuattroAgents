# QuattroAgents

QuattroAgents configures a small, provider-neutral coding-agent fleet from one canonical local state directory. Its four phases are **Discover**, **Plan**, **Execute**, and **Verify**. Large models decide; bounded small-model work is verified by deterministic gates.

## Install and quick start

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m quattroagents setup --project . --providers codex,claude --profile economy --install-mcp recommended --yes
```

The `qagents` console command provides `init`, `analyze`, `interview`, `propose`, `apply`, `setup`, `doctor`, `validate`, `diff`, `rollback`, `reconfigure`, `benchmark`, agent/task views, MCP serving and metrics reporting. Add `--help` to every command.

## Optional local tools

Setup safely detects, but never installs or configures, optional `rtk` and `codebase-memory-mcp` executables. Re-run `scripts/detect-rtk.sh` or `scripts/detect-codebase-memory-mcp.sh` at any time; absence is reported and is not an error. `qagents doctor --json` exposes their availability as `rtk` and `codebase_memory_mcp`.

RTK is useful for compact local diagnostics, but it resolves tools from `PATH`. Keep the authoritative project checks on `.venv/bin/python -m pytest`, `.venv/bin/python -m ruff`, and `.venv/bin/python -m mypy` unless the virtualenv tool directory is deliberately on `PATH`.

## Metrics report

Use `.venv/bin/python -m quattroagents metrics report --format markdown` for a deterministic, human-readable benchmark summary. During 0.2, no execution samples are persisted, so the report explicitly shows zero values and does not infer savings or outcomes. The default JSON format remains available for machine consumers.

## Canonical state and providers

`.quattroagents/` is authoritative; Codex (`AGENTS.md`, `.codex/`, `.agents/`) and Claude Code (`CLAUDE.md`, `.claude/`, `.mcp.json`) are generated adapters. The core uses abstract `small`, `medium`, `large`, and `long_horizon` tiers rather than commercial model names. `long_horizon` is manual-only.

The local `quattroagents` MCP is SQLite/WAL-backed and exposes a small task/lease control plane. No remote service or secret is needed for baseline operation.

## Safety

Configuration generation backs up replaced files below `.quattroagents/backups/`; runtime data and credentials are ignored. Protected-kernel paths require medium-or-higher implementation, independent review and human approval. Never force-push.

## Self-hosting roadmap

- **0.2: dogfooding** — low-risk local tasks only.
- **0.3: self-hosting** — planned stable workflow and immutable run snapshots.
- **0.4: controlled self-configuration proposals** — never automatic activation.
- **0.5: assisted optimization** — benchmark-backed recommendations.

See [architecture](docs/architecture.md), [benchmarking](docs/benchmarking.md), [providers](docs/providers.md), [MCP](docs/mcp.md), [self-hosting](docs/self-hosting.md), and [roadmap](docs/roadmap.md).

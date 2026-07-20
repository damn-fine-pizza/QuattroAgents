# QuattroAgents

QuattroAgents configures a small, provider-neutral coding-agent fleet from one canonical local state directory. Its name is a nod to quattro formaggi. Large models decide; bounded small-model work is verified by deterministic gates.

## Install and quick start

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m quattroagents setup --project . --providers codex,claude --profile economy --install-mcp recommended --yes
```

The `qagents` console command provides `init`, `analyze`, `interview`, `propose`, `apply`, `setup`, `doctor`, `validate`, `diff`, `rollback`, `reconfigure`, `benchmark`, agent/task views, MCP serving and metrics reporting. Add `--help` to every command.

For a brownfield task, run `qagents analyze --format json`, then `qagents interview --interactive --format markdown` to collect confirmed user intent. Copy the resulting interview record into the task contract, then run `qagents swarm plan TASK-ID`. The planner refuses to create worker packets without that confirmed record. `swarm plan` is plan-only: it produces local, deterministic, reference-only worker packets and never launches agents.

In the 0.4 Codex coordinator workflow, Codex's native multi-agent tools launch and wait for bounded workers. QuattroAgents MCP separately records task/claim/lease/run/snapshot/artifact/evidence state. A configured `max_threads` is only the coordinator's concurrency ceiling, never an automatic-spawn instruction or a QuattroAgents worker-count promise. See [Codex multi-agent coordination](docs/codex-multi-agent.md).

### Orchestration quickstart

The explicit setup command above generates `qagents-orchestrate` for the selected provider: `.agents/skills/qagents-orchestrate/SKILL.md` for Codex and the provider skill directory for Claude. If the project was configured before this skill existed, rerun setup or use `qagents apply --providers codex` or `qagents apply --providers claude`; installing or upgrading the package alone does not retrofit generated files.

Then ask the agent to start or continue a milestone with QAG. It asks only for material missing answers, records the confirmed interview and contract, then continues autonomously through planning, claim/lease, bounded worker waves, evidence, independent review, gates and snapshots. It pauses only for a genuine blocker or a human decision that materially changes scope, risk, or protected-path approval. It is not a daemon, generic dispatcher, automatic configuration mechanism, remote service, or LLM runner.

## Optional local tools

Setup safely detects, but never installs or configures, optional `rtk` and `codebase-memory-mcp` executables. Re-run `scripts/detect-rtk.sh` or `scripts/detect-codebase-memory-mcp.sh` at any time; absence is reported and is not an error. `qagents doctor --format json` exposes their availability as `rtk` and `codebase_memory_mcp`.

Setup installs `pytest`, `ruff`, and `mypy` in the project `.[dev]` virtualenv; it does not require global installations. RTK resolves tools from `PATH`, so use `scripts/rtk.sh ruff check .` (and the analogous `pytest` or `mypy` commands) to expose `.venv/bin` to it. Keep the authoritative project checks on `.venv/bin/python -m pytest`, `.venv/bin/python -m ruff`, and `.venv/bin/python -m mypy`.

### QuattroAgents MCP

QuattroAgents exposes its local task and metrics control plane as a stdio MCP server. See the [MCP installation guide](docs/quattroagents-mcp.md) for direct `mcp add` commands that retrieve QuattroAgents from GitHub on first use, plus project-local and manual alternatives.

## Metrics report

Use `.venv/bin/python -m quattroagents metrics report --format markdown` for a deterministic, human-readable benchmark summary. It reports recorded benchmark evidence only: QuattroAgents does not infer savings, speedups, or outcomes from plans or snapshots. The default JSON format remains available for machine consumers.

## Canonical state and providers

`.quattroagents/` is authoritative; Codex (`AGENTS.md`, `.codex/`, `.agents/`) and Claude Code (`CLAUDE.md`, `.claude/`, `.mcp.json`) are generated adapters. The core uses abstract `small`, `medium`, `large`, and `long_horizon` tiers rather than commercial model names. `long_horizon` is manual-only.

`qagents-orchestrate` is opt-in generated provider guidance: an explicit setup or
render of Codex creates `.agents/skills/qagents-orchestrate/SKILL.md`, and an
explicit setup or render of Claude creates its `.claude/skills/` counterpart.
It is not retroactively added when QuattroAgents is installed or upgraded in an
already configured project. Once the material task answers are known, the skill
continues normal in-scope lifecycle work without routine permission prompts; it
stops only for a genuine blocker or a human decision that materially changes
scope, risk, or protected-path approval. It never supplies a daemon, generic
dispatcher, automatic configuration, remote service, or LLM runner.

The local `quattroagents` MCP is SQLite/WAL-backed and exposes a small task/lease control plane. Task contracts may include a release milestone such as `0.2.0`; query the deterministic mapping with `qagents tasks list --milestone 0.2.0 --format json`. No remote service or secret is needed for baseline operation.

## Safety

Configuration generation backs up replaced files below `.quattroagents/backups/`; runtime data and credentials are ignored. Protected-kernel paths require medium-or-higher implementation, independent review and human approval. Never force-push.

## Self-hosting roadmap

- **0.2: dogfooding** — low-risk local tasks only; user-intent interviews and swarm plans are local, deterministic and plan-only.
- **0.3: self-hosting** — an explicit `plan → execute → review → integrate` record with immutable, verifiable run snapshots. Recording a run never launches an agent or activates configuration; protected changes require human approval before integration.
- **0.4: controlled Codex coordination** — native Codex dispatch with QuattroAgents task, lease, evidence and snapshot records; self-configuration remains proposal-only and never activates automatically.
- **0.5: local skills and assisted optimization** — evaluate repeatable local scripts as agent skills and make recommendations only from reproducible benchmarks.

See [architecture](docs/architecture.md), [benchmarking](docs/benchmarking.md), [providers](docs/providers.md), [MCP](docs/mcp.md), [swarm planning](docs/swarm.md), [Codex coordination](docs/codex-multi-agent.md), [self-hosting](docs/self-hosting.md), and [roadmap](docs/roadmap.md).

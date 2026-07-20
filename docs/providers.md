# Providers

Codex generation uses trusted project `.codex/config.toml`, `AGENTS.md`, skills and agents. Existing Codex MCP servers are retained while QuattroAgents is configured through `.venv/bin/qagents`. Claude generation uses `CLAUDE.md`, `.claude/agents`, skills, settings and project `.mcp.json`. The adapter does not store credentials. Setup writes project-local Git hooks that use `.venv/bin/python` for validation, tests, linting and type checks.

For Codex multi-agent work, agent lifecycle is intentionally provider-specific: the
Codex coordinator uses the native Codex multi-agent tools to spawn, message and wait
for workers. QuattroAgents MCP does not launch agents; it coordinates the durable
task contract, claim, lease, run, snapshot, artifact and evidence records. The
`qagents swarm plan` command remains plan-only. `max_threads`, where configured, is
a concurrency ceiling chosen by the coordinator, not an automatic spawning command
and not a number promised by QuattroAgents. See [Codex multi-agent coordination](codex-multi-agent.md).

`scripts/setup.sh` optionally detects installed `rtk` and `codebase-memory-mcp` commands. Detection is re-runnable, makes no installation or MCP configuration changes, and reports a missing command without failing setup. Development tools (`pytest`, `ruff`, and `mypy`) are installed in `.venv`; use `scripts/rtk.sh` to make them available to RTK without global installs. `qagents doctor --format json` reports executable availability; it does not assert that an MCP server is configured or reachable.

CI validates both generated adapters: Codex configuration, roles, skills and MCP preservation; and Claude settings, agents, skills and MCP configuration. See [quality gates](gates.md) for the exact installation, verification and delivery checks.

For the QuattroAgents MCP server, see the [installation guide](quattroagents-mcp.md). It covers direct `mcp add` configuration for Codex and Claude with either an isolated GitHub-backed runner or a project virtualenv.

## Orchestration skill

`qagents-orchestrate` is a generated provider skill. It is written to
`.agents/skills/` only when QuattroAgents explicitly sets up or renders the
`codex` provider, and to `.claude/skills/` only when it explicitly sets up or
renders `claude`. Installing or upgrading QuattroAgents does not add it to an
already configured project; rerun setup or explicitly render the relevant
provider to opt in.

The skill is conversationally autonomous once the task, project state, and any
required confirmed interview provide the material answers. It does not pause for
routine status checks or permission for ordinary in-scope work. Its hard stops
are a genuine blocker or a human decision that materially changes scope, risk,
or protected-path approval. It does not introduce a daemon, generic dispatcher,
automatic configuration, remote service, or LLM runner: provider-native agents
remain provider-managed, while the QuattroAgents MCP records the control-plane
state only.

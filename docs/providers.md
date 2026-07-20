# Providers

Codex generation uses trusted project `.codex/config.toml`, `AGENTS.md`, skills and agents. Existing Codex MCP servers are retained while QuattroAgents is configured through `.venv/bin/qagents`. Claude generation uses `CLAUDE.md`, `.claude/agents`, skills, settings and project `.mcp.json`. The adapter does not store credentials. Setup writes project-local Git hooks that use `.venv/bin/python` for validation, tests, linting and type checks.

`scripts/setup.sh` optionally detects installed `rtk` and `codebase-memory-mcp` commands. Detection is re-runnable, makes no installation or MCP configuration changes, and reports a missing command without failing setup. Development tools (`pytest`, `ruff`, and `mypy`) are installed in `.venv`; use `scripts/rtk.sh` to make them available to RTK without global installs. `qagents doctor --json` reports executable availability; it does not assert that an MCP server is configured or reachable.

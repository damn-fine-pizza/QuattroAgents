# Providers

Codex generation uses trusted project `.codex/config.toml`, `AGENTS.md`, skills and agents. Existing Codex MCP servers are retained while QuattroAgents is configured through `.venv/bin/qagents`. Claude generation uses `CLAUDE.md`, `.claude/agents`, skills, settings and project `.mcp.json`. The adapter does not store credentials. Setup writes project-local Git hooks that use `.venv/bin/python` for validation, tests, linting and type checks.

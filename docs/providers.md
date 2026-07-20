# Providers

Codex generation uses trusted project `.codex/config.toml`, `AGENTS.md`, skills and agents. Claude generation uses `CLAUDE.md`, `.claude/agents`, skills, settings and project `.mcp.json`. The adapter does not store credentials. Where lifecycle hooks differ, CLI validation, hooks and the MCP control plane provide the portable gate.

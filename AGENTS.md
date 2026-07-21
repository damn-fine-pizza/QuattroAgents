# QuattroAgents

QuattroAgents is a Project Agent Factory: an MCP server and CLI that analyze a
target repository, interview the user, and generate/update tailored Claude and
Codex agents and skills on disk. Canonical state per project lives in
`.agent-factory/` (profile snapshots, decisions, interview sessions, the last
generated manifest); rendered `.claude/agents/*.md`, `.claude/skills/*/SKILL.md`,
`.codex/agents/*.toml`, `AGENTS.md` and `CLAUDE.md` are generated, derived
output — treat manual edits to them as overrides the next `setup`/`generate_*`
run will detect and refuse to silently clobber, not as source of truth.
Validate with `qagents validate`.

The MCP server (`qagents mcp serve`) exposes the same tool surface the CLI
wraps — `analyze_project`, `setup`, `generate_agents`/`generate_skills`,
`start_project_interview` and its follow-on interview tools, `record_decision`,
`generate_swarm_plan`, `validate_generated_configuration`,
`show_generation_diff` — one JSON-RPC `tools/call` per action, never blocking
on interactive stdin. It does not spawn, dispatch, or wait for agents itself;
use the Codex coordinator's native tools for that.

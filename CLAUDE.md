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

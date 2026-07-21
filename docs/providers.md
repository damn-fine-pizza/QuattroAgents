# Providers

Agents and skills are rendered from a shared internal domain model (`AgentDefinition` and `SkillDefinition`) through per-provider adapters: `render_claude()` and `render_codex()`. Each adapter writes provider-specific configuration files to its corresponding directory tree.

## Adapter outputs

**Claude adapter** (`src/quattroagents/adapters/claude.py`) writes:
- `.claude/agents/{agent.id}.md` — agent definition with YAML frontmatter and responsibilities, scope, tools, completion/escalation criteria, and collaboration notes
- `.claude/skills/{skill.id}/SKILL.md` — skill definition with workflow, inputs, outputs, required tools, validation criteria, and usable-by list
- `.claude/settings.json` — Claude Code permissions and hooks configuration, merged with any existing content
- `.mcp.json` — MCP server configuration including the QuattroAgents server entry, merged with existing servers

**Codex adapter** (`src/quattroagents/adapters/codex.py`) writes:
- `.codex/agents/{agent.id}.toml` — agent definition in Codex TOML format with description, model reasoning effort, and developer instructions
- `.agents/skills/{skill.id}/SKILL.md` — skill definition in markdown (same format as Claude)
- `.codex/config.toml` — Codex configuration with MCP server settings; existing Codex MCP servers are preserved, and the QuattroAgents server entry is added or updated
- `AGENTS.md` — project documentation noting that generated agents and skills live in `.codex/agents/` and `.agents/skills/`, and that state lives in `.agent-factory/`

## Generated-file protection

Both adapters use `GeneratedFileGuard` (from `src/quattroagents/persistence.py`) to prevent silently clobbering hand-edited files. The guard implements a "generated base + manual overrides" pattern:

1. When a file is first generated, its SHA-256 hash is recorded in `.agent-factory/overrides/{sanitized-relative-path}.json`
2. Before regenerating, the guard compares the on-disk file's hash against the recorded hash
3. If the hashes match, the file is safe to overwrite (no manual edits since generation)
4. If they differ, the file has been manually edited — the guard refuses to overwrite and reports a conflict instead

This ensures that hand-edits to generated files are never silently lost.

## Credentials and configuration

The adapters do not store credentials. Both adapters perform a shallow merge when writing configuration files (`.claude/settings.json`, `.claude/.mcp.json`, `.codex/config.toml`), preserving any pre-existing top-level keys while replacing only their own namespace. This allows manual configuration (credentials, additional servers, or settings) to coexist with generated content.

## Orchestration skill

`qagents-orchestrate` is a generated provider skill. It is written to `.agents/skills/` only when QuattroAgents explicitly sets up or renders the `codex` provider, and to `.claude/skills/` only when it explicitly sets up or renders `claude`. Installing or upgrading QuattroAgents does not add it to an already-configured project; rerun setup or explicitly render the relevant provider to opt in.

For the QuattroAgents MCP server, see the [installation guide](quattroagents-mcp.md). It covers direct `mcp add` configuration for Codex and Claude with either an isolated GitHub-backed runner or a project virtualenv.

# Changelog

## 0.7.0 — Project Agent Factory

- Replaced the task/lease/swarm control-plane architecture with a Project Agent Factory: analyzes a target repository, interviews the user, and generates/updates tailored Claude and Codex agents and skills.
- Added a provider-independent domain model, local JSON persistence under `.agent-factory/`, an adaptive interview engine, and agent/skill generation with wave-scheduled swarm planning.
- Rewrote the MCP server and CLI as thin wrappers over a shared tool-dispatch table.
- Removed the old SQLite/WAL control-plane, task-lease-run model, and protected-kernel gate system.
- Changed the agent display-line grammar from `<agent-name> [<model>] <description>` to `<role> (<tier>)`.

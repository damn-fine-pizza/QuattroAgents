# Changelog

## 0.7.0 — Project Agent Factory

- Replaced the task/lease/swarm control-plane architecture with a Project Agent Factory: analyzes a target repository, interviews the user, and generates/updates tailored Claude and Codex agents and skills.
- Added a provider-independent domain model, local JSON persistence under `.agent-factory/`, an adaptive interview engine, and agent/skill generation with wave-scheduled swarm planning.
- Rewrote the MCP server and CLI as thin wrappers over a shared tool-dispatch table.
- Removed the old SQLite/WAL control-plane, task-lease-run model, and protected-kernel gate system.
- Changed the agent display-line grammar from `<agent-name> [<model>] <description>` to `<role> (<tier>)`.

## 0.2.0 — Minimum Dogfooding Point

- Added provider-neutral canonical state, routing, gates, task contracts and result envelopes.
- Added Codex and Claude Code renderers, SQLite/WAL control-plane MCP, atomic task claims and file leases.
- Added bootstrap, validation, hooks, CI and dogfooding status.

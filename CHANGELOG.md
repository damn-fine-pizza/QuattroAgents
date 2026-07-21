# Changelog

## 0.7.1

- Fixed duplicate-implementation detection to exclude nested `build`, `node_modules`, `.venv`, `dist`, `.git`, `worktrees`, and `_deps` directories instead of only skipping exact top-level matches.
- `submit_interview_answers` now rejects answers missing the required `value` field instead of silently defaulting to an empty string.
- `resolve_decision_conflict` now actually supersedes the losing decisions when a `user_vs_user` conflict is resolved with "keep the most recent decision and supersede the others", instead of only updating the conflict record.
- Knowledge gaps for duplicate-implementation risks now get a unique topic per duplicate name, so unrelated duplicates are no longer bundled into a single conflict.
- The interview flow now attaches a roster of sibling agents to the `project-orchestrator`'s collaboration notes, so it knows about and can direct the rest of the generated team.
- Generated agent files and names are now prefixed with `qag-` (e.g. `.claude/agents/qag-repository-cartographer.md`) to distinguish them from hand-authored agents.

## 0.7.0 — Project Agent Factory

- Replaced the task/lease/swarm control-plane architecture with a Project Agent Factory: analyzes a target repository, interviews the user, and generates/updates tailored Claude and Codex agents and skills.
- Added a provider-independent domain model, local JSON persistence under `.agent-factory/`, an adaptive interview engine, and agent/skill generation with wave-scheduled swarm planning.
- Rewrote the MCP server and CLI as thin wrappers over a shared tool-dispatch table.
- Removed the old SQLite/WAL control-plane, task-lease-run model, and protected-kernel gate system.
- Changed the agent display-line grammar from `<agent-name> [<model>] <description>` to `<role> (<tier>)`.

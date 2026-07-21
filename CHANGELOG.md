# Changelog

## 0.7.2 — Archetypes, tiers, and hand-off validation

- Replaced the flat `CANDIDATE_ROLES` catalog with an **archetype/tier system**: 13 reference archetypes (`project-orchestrator`, `repository-cartographer`, `architecture-guardian`, `implementation-agent`, `test-agent`, `bdd-feature-agent`, `code-reviewer`, `documentation-agent`, `dependency-agent`, `ci-build-agent`, `performance-agent`, `security-reviewer`, `release-agent`), each generating a Haiku-tier variant for bounded, mechanically-verifiable work and a Sonnet-tier variant for ambiguous, trade-off-driven work. `select_agents` now instantiates both tier variants of every selected archetype, so generated teams lean on many narrow, fast Haiku agents for routine work while keeping Sonnet agents available for judgment calls. `project-orchestrator` also gets a Haiku variant that mechanically executes an already-computed swarm wave plan.
- Added a **Handoff mechanism**: agents now declare `expected_inputs`/`expected_outputs` as concrete artifact names (e.g. `repo-map.json`, `test-report.json`), rendered as a new "## Handoff" section in `.claude/agents/*.md` and folded into `.codex/agents/*.toml` `developer_instructions`. Agents read/write these artifact files directly instead of relaying full content through an orchestrator's context, reducing inter-agent token overhead.
- Added a generation-time **hand-off cycle check** (`qagents validate`): the producer/consumer graph derived from every agent's `expected_inputs`/`expected_outputs` is checked for cycles, so a generated team whose declared hand-offs can never be ordered is rejected before it can deadlock at runtime. Extracted a shared `find_dependency_cycle` helper (Kahn's algorithm) reused by both this new check and the existing swarm circular-dependency check.
- Added `AgentDefinition.archetype_id` to track which archetype a generated agent was derived from, independent of its own id.
- Documented a deferred agent-activity dashboard as a TODO in `docs/roadmap.md`, pending empirical verification of the `SubagentStop` hook payload/transcript schema.

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

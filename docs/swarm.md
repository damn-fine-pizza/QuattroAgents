# Swarm plan generation

`qagents swarm plan` generates deterministic wave-based schedules for agent groups. It is **plan-only**: it computes waves and lists required reviewers and completion criteria, but never launches, dispatches, or waits for agents.

## Invocation

Provide a task identifier, goal statement, and agent roster from `qagents agents list` or `qagents agents generate`:

```bash
qagents swarm plan \
  --task-id ID \
  --goal "..." \
  --agent-ids '[...]' \
  --phases '{"agent-id":"phase-name"}' \
  --depends-on '{"agent-id":["...","..."]}' \
  --file-ownership '{"agent-id":["path/..."]}' \
  --project .
```

The same arguments are available via MCP tool `generate_swarm_plan`.

## Wave-based scheduling

The planner computes conflict-free execution waves using Kahn's algorithm: agents whose dependencies are satisfied are considered for inclusion in the next wave, but only if their file-ownership paths do not overlap with others already selected for that wave. Agents within a wave may run in parallel; overlapping file sets are deferred to later waves.

The plan extracts mandatory reviewers (READ_ONLY agents) and completion criteria from agent definitions and active decisions.

## Boundaries

This is a planning tool only: it does not modify routing, gates, configuration, or run state. Agent selection, phase names, dependencies, and file ownership are caller-provided inputs; the plan validates these and outputs waves, but never enforces or executes them.

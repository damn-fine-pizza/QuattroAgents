# Communication protocol

Stable identifiers use `TASK-`, `REQ-`, `DEC-`, `ART-`, `EVD-`, `BLOCK-`, and `FIND-`. Task contracts are versioned JSON. Result envelopes distinguish facts, inferences, assumptions, blockers and confidence; agents pass references rather than source/diff/log dumps.

## Milestones

Each task contract may declare an optional `milestone` using the release identifier from the roadmap, for example `"0.2.0"`. QuattroAgents persists that value separately from the JSON payload so that task listings can be filtered deterministically. The task-create MCP call accepts the value either in the contract payload or as its top-level `milestone` argument; when both are provided, they must match.

```json
{
  "objective": "Add deterministic task reporting",
  "milestone": "0.2.0",
  "requirements": [{"id": "REQ-1", "text": "…"}]
}
```

Milestones group tasks; they do not replace task status. Record delivery evidence such as branch, commit and PR in the contract payload or result envelope. Use the package version together with the Git commit to identify the exact self-hosted runtime. In a Git checkout, `qagents --version` and the MCP `serverInfo` report `0.2.2+g<sha12>`; `.dirty` is appended when local source changes are present. Built distributions without Git metadata report the base package version.

## Brownfield intent

For an existing repository, run `qagents analyze` before `qagents interview`. Analysis contributes facts only; the interview collects the user's intended outcome, scope, acceptance evidence, constraints and parallelization choices. Copy confirmed answers into the task contract before creating any worker packets. Source code must not be treated as proof of user intent.

## Swarm work items

During 0.2, `swarm_work_items` is an optional plan-only part of a task contract. Each work item names an objective, requirements, allowed files, context references and dependencies. The planner can place items in the same wave only when their dependencies are satisfied and their allowed files do not overlap. It emits a reference-only context summary and an independent review stage; it does not launch agents or persist execution snapshots.

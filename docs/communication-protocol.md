# Communication protocol

Stable identifiers use `TASK-`, `REQ-`, `DEC-`, `ART-`, `EVD-`, `BLOCK-`, `FIND-`, `RUN-` and `SNAP-`. Task contracts are versioned JSON. Result envelopes distinguish facts, inferences, assumptions, blockers and confidence; agents pass references rather than source/diff/log dumps.

## Milestones

Each task contract may declare an optional `milestone` using the release identifier from the roadmap, for example `"0.2.0"`. QuattroAgents persists that value separately from the JSON payload so that task listings can be filtered deterministically. The task-create MCP call accepts the value either in the contract payload or as its top-level `milestone` argument; when both are provided, they must match.

```json
{
  "objective": "Add deterministic task reporting",
  "milestone": "0.2.0",
  "requirements": [{"id": "REQ-1", "text": "…"}]
}
```

Milestones group tasks; they do not replace task status. Record delivery evidence such as branch, commit and PR in the contract payload or result envelope. Use the package version together with the Git commit to identify the exact self-hosted runtime. In a Git checkout, `qagents --version` and the MCP `serverInfo` report `<package-version>+g<sha12>` (for example `0.5.2+g<sha12>`); `.dirty` is appended when local source changes are present. Built distributions without Git metadata report the base package version.

## Brownfield intent

For an existing repository, run `qagents analyze --format json` before `qagents interview --interactive`. Analysis contributes facts only; the interview collects the user's intended outcome, scope, acceptance evidence, constraints and parallelization choices. Copy the `interview.status = "confirmed"` record into the task contract before creating any worker packets. `swarm plan` rejects a task without all confirmed answers. Source code must not be treated as proof of user intent.

## Swarm work items

During 0.2, `swarm_work_items` is an optional plan-only part of a task contract. Each work item names an objective, requirements, allowed files, context references and dependencies. The planner can place items in the same wave only when their dependencies are satisfied and their allowed files do not overlap. It emits a reference-only context summary and an independent review stage; it does not launch agents or persist execution snapshots.

## Self-hosting run snapshots

A 0.3 run uses a `RUN-` identifier bound to `task_id`, `source_commit` and `runtime_version`. Each immutable snapshot has a `SNAP-` identifier and appends in the only permitted order: `plan`, `execute`, `review`, then `integrate`. A snapshot carries its stage and sequence, concise summary, changed-file references, artifact records and evidence records. Artifact records contain an ID, path, kind and SHA-256 digest; evidence records contain an ID, reference and SHA-256 digest. The snapshot also contains the preceding digest, producing a verifiable chain.

The protocol carries references and concise summaries, never full transcripts. `integrate` records an approved state; it does not itself merge, push, tag, execute an agent or activate configuration. For protected-kernel paths, its `human_approved` value must be explicitly true and is part of the immutable snapshot.

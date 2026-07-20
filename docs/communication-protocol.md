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

Milestones group tasks; they do not replace task status. Record delivery evidence such as branch, commit and PR in the contract payload or result envelope. Use the package version together with the Git commit to identify the exact self-hosted runtime. In a Git checkout, `qagents --version` and the MCP `serverInfo` report `0.2.0+g<sha12>`; `.dirty` is appended when local source changes are present. Built distributions without Git metadata report the base package version.

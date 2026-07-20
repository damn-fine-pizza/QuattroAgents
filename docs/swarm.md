# Swarm planning

Swarm planning is a 0.2 dogfooding aid for bounded local work. It creates deterministic worker packets; it does not execute a fleet.

## Brownfield flow

1. Run `qagents analyze --project . --format json` to collect repository facts.
2. Run `qagents interview --project . --interactive --format markdown` and collect the user's answers.
3. Copy the confirmed interview record, intent, constraints and acceptance evidence into a task contract.
4. Add optional `swarm_work_items` when work can be divided safely.
5. Run `qagents swarm plan TASK-ID --project . --format markdown`.

The interview is mandatory and enforced by `swarm plan`: source code describes the current system, not the user's desired outcome.

## Work-item shape

```json
{
  "id": "docs",
  "objective": "Document the new command",
  "requirements": ["REQ-2"],
  "allowed_files": ["README.md"],
  "context_refs": ["docs/communication-protocol.md"],
  "depends_on": []
}
```

Every swarm task contract also requires this record from `qagents interview --interactive`:

```json
{
  "interview": {
    "status": "confirmed",
    "answers": {
      "INTENT-1": "Desired outcome",
      "INTENT-2": "Scope and exclusions",
      "INTENT-3": "Acceptance evidence",
      "INTENT-4": "Constraints and approvals",
      "INTENT-5": "Parallel work and review choices"
    }
  }
}
```

The planner schedules independent, non-overlapping items in the same wave and postpones overlapping file sets to a later wave. Every plan ends with an independent reviewer after all worker packets.

## Boundaries

This capability is deliberately below self-hosting: it does not launch subagents, write immutable run snapshots, change routing or gates, activate configuration, or estimate optimization gains. In 0.3, an approved self-hosting workflow can record the corresponding immutable run snapshots as `plan → execute → review → integrate`; recording remains separate from dispatch and does not launch a fleet.

The 0.2 interview and bounded-worker controls remain in force. Protected-kernel integration needs explicit human approval. A future, separate milestone may turn repeated deterministic local operations into agent skills, but only benchmark evidence may support a token or execution-time efficiency claim.

---
name: qagents-plan
description: QuattroAgents qagents-plan workflow
---

Read `.quattroagents/` first. Keep L0/L1 concise; store L2 evidence by reference.

Produce and validate the task contract, confirmed interview record, non-overlapping
work items, dependency waves, allowed-file sets, context references and acceptance
checks. Run `qagents swarm plan TASK-ID` to create deterministic worker packets.
It is **plan-only**: it never launches agents. Do not dispatch, claim, lease, review
or integrate work in this skill; hand the validated packets to `qagents-execute`.

---
name: qagents-execute
description: QuattroAgents qagents-execute workflow
---

Read `.quattroagents/` first. Keep L0/L1 concise; store L2 evidence by reference.

## Codex coordinator procedure

This skill dispatches a validated plan. `qagents swarm plan TASK-ID` is **plan_only**:
it produces deterministic worker packets and never launches an agent. The Codex
coordinator uses Codex's native multi-agent tools (`spawn_agent`, `wait_agent`,
`send_message`, and `followup_task`) for agent lifecycle. QuattroAgents MCP is the
local control plane for tasks, claims, leases, runs, snapshots, artifacts, and
evidence; it does not spawn or wait for Codex agents. Do not describe or invent a
provider-neutral spawning API.

1. Confirm the task contract, interview, packets, dependency graph, allowed files,
   acceptance checks, protected paths, and current source state. Use the plan skill
   output; do not reinterpret planning here.
2. Create or locate the run with MCP, claim the task with `task_claim`, and acquire
   a lease with `lease_acquire` for each dispatchable packet before giving it to a
   worker. Record the plan stage with `run_snapshot`. If a claim or lease conflicts,
   do not dispatch that packet: resolve the conflict or move it to a later sequential
   wave.
3. Process waves deterministically. A wave contains only packets whose dependencies
   have completed and whose leased file scopes do not overlap. Sort eligible packets
   by the planner's stable order (then packet ID) before dispatch. Launch only that
   ordered, eligible set with native Codex tools. `max_threads`, when configured, is
   a concurrency ceiling for this set; it does not create, select, or automatically
   spawn workers. QuattroAgents is not associated with a worker-count promise.
4. Give each worker only its packet: objective, requirements, allowed files,
   context/evidence references, lease/claim identity, acceptance commands, and
   result-envelope format. Do not pass unrelated task transcripts or another
   worker's private context. A worker may make only its packet's scoped changes.
5. Wait with Codex's native wait mechanism. Collect a concise result envelope with
   status, changed files, commands and outcomes, artifact references, evidence
   references/digests, and blockers. Register durable artifacts with
   `artifact_register`; append evidence references and concise summaries to the
   execute `run_snapshot` rather than embedding raw transcripts.
6. Release every completed, failed, cancelled, or timed-out packet lease with
   `lease_release`, including on error. Do not release a lease before its envelope
   and evidence have been recorded. If a worker is still active, wait or explicitly
   cancel it before final release.
7. After all required worker envelopes are recorded, dispatch an independent
   reviewer with the final diff, packet boundaries, acceptance evidence, and run
   references. The reviewer reviews; it does not plan or silently broaden the
   implementation. Record its result in the review snapshot. Protected-kernel
   integration still requires recorded human approval before an integrate snapshot.
8. Escalate ambiguous scope, overlapping files, a lost lease, failed acceptance,
   protected-path work, missing evidence, or conflicting worker results. Re-plan or
   obtain the required human decision; never guess a merge of conflicting changes.
   When native multi-agent tools are unavailable, run the same packets one at a time
   in stable wave order, retaining claims, leases, envelopes, snapshots, evidence,
   review, and release discipline.

# Codex multi-agent coordination

## Scope and ownership

This is the 0.4 coordinator procedure for executing a validated QuattroAgents swarm
plan in Codex. `qagents swarm plan TASK-ID` is **plan-only**: it validates the task
contract and emits deterministic worker packets; it does not launch, dispatch, or
wait for agents.

Codex owns agent lifecycle with its native multi-agent tools: `spawn_agent` creates a
bounded worker, `wait_agent` waits for it, and `send_message` or `followup_task`
communicates only when needed. QuattroAgents MCP owns the durable control-plane
records: task, claim, lease, run, append-only snapshot, artifact, and evidence. It
does not provide a generic worker API and it never spawns or waits for Codex agents.

## Coordinator procedure

1. Start from a plan skill-validated contract: confirmed interview, packet IDs,
   stable packet order, dependencies, allowed-file scopes, context references,
   protected paths, and acceptance commands. The plan skill plans and validates;
   the execute skill dispatches; the review skill reviews.
2. Create or locate the run. Claim the task with QuattroAgents MCP and acquire a
   lease for each packet before dispatch. Save the concise plan reference in the
   immutable plan snapshot. A failed claim or lease is a conflict, not permission to
   proceed.
3. Build a deterministic wave from packets whose dependencies have completed and
   whose leased file scopes do not overlap. Order it by planner stable order and then
   packet ID. Dispatch the eligible ordered packets with Codex native tools. Where
   `max_threads` is configured, it caps this concurrent set only; it neither selects
   tasks nor automatically spawns agents. QuattroAgents makes no assertion about a
   particular number of workers.
4. Send each worker only its packet: objective, requirements, allowed files,
   context and evidence references, claim/lease identity, acceptance commands and
   required result envelope. Workers do not receive unrelated transcripts or sibling
   private context, and they may not extend their file scope.
5. Wait using Codex native waiting. Collect one concise worker envelope containing
   outcome, changed files, commands and results, artifact references, evidence
   references with digests, and blockers. Register durable artifacts and append the
   concise execute evidence to the run snapshot; do not put full transcripts in the
   snapshot.
6. Release the packet's lease only after its envelope and evidence are recorded.
   Release completed, failed, cancelled and timed-out packets; wait for or explicitly
   cancel an active worker before release. Continue only when the wave's required
   dependencies are evidenced.
7. Dispatch an independent reviewer after worker completion. It receives the final
   diff, packet boundaries, acceptance outcomes and evidence references, and returns
   a review envelope. Record that in the review snapshot. Integrate only after review;
   protected-kernel work additionally requires the recorded human approval described
   in the self-hosting workflow.

## Escalation and sequential fallback

Escalate an ambiguous contract, overlapping scopes, claim/lease conflict, lost lease,
missing envelope or evidence, failed acceptance check, protected-path change, or
conflicting worker result. The coordinator must re-plan, obtain the required human
decision, or place the packet in a later wave; it must not merge guesses.

If native Codex multi-agent tools are unavailable, run packets one at a time in the
same stable wave order. Retain the same claim, lease, packet-only context, envelope,
evidence, snapshot, review and release rules. Sequential execution is a fallback for
lifecycle availability, not a relaxation of the control plane.

## Required real multi-agent demonstration

Before documentation or release notes claim an operational multi-agent result, run a
real bounded demonstration against a confirmed, non-protected task with at least two
independent, non-overlapping packets in one deterministic wave and an independent
reviewer. Preserve references to:

- the confirmed task contract and plan-only packet output;
- task claim and per-packet lease identities, acquisition and release outcomes;
- native Codex worker and reviewer lifecycle evidence (without copying full private
  transcripts);
- worker and reviewer result envelopes, changed-file scopes, acceptance-command
  outputs, artifact/evidence digests, and all run snapshot IDs; and
- the run verification result plus any escalation or sequential-fallback record.

This is a demonstration requirement, not a claim that one has been performed. Do not
state a worker count, speedup, cost reduction, quality improvement, or successful
operational result until the corresponding evidence exists and is independently
reviewed.

## Recorded demonstration

`CODEX-DISPATCH-DEMO` satisfied this requirement with two independent, read-only
packets: `worker-docs` (`docs/`) and `worker-tests` (`tests/`). The Codex coordinator
created distinct native workers, collected their concise envelopes, released both
leases, and then used `CODEX-DISPATCH-DEMO-REVIEW` for an independent read-only
review. The worker-test envelope records six focused swarm tests passing; the
worker-docs envelope records a successful RTK documentation check. No planner launch is
claimed.

The immutable run `CODEX-DISPATCH-DEMO-RUN` verifies three chained snapshots:
`CODEX-DISPATCH-DEMO-PLAN-001`, `CODEX-DISPATCH-DEMO-EXECUTE-001`, and
`CODEX-DISPATCH-DEMO-REVIEW-001`. Its verification result is `valid: true` with
three snapshots. This documents lifecycle evidence only; it makes no speed, token,
cost, or quality claim.

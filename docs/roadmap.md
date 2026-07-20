# Roadmap

## 0.2.0

Minimum dogfooding point: canonical state, adapters, gates, local MCP, bootstrap and validation. It may develop noncritical pieces only.

## 0.2.1

Dogfooding maintenance release: task-to-milestone mapping, runtime source identity and tagged MCP installation targets.

## 0.2.2

Dogfooding planning release: brownfield user-intent interviews and deterministic, plan-only swarm work packets.

## 0.3.0

Stable self-hosting foundation:

- an explicit, ordered `plan → execute → review → integrate` workflow;
- append-only run snapshots with stable IDs, task/commit/runtime-version references, artifact and evidence references, and a SHA-256 digest chain;
- verification of the stored chain without retaining full agent transcripts;
- an integration gate for protected-kernel paths that requires recorded human approval.

Run recording is observational: it neither launches agents nor activates configuration. The 0.2 task contract, confirmed user interview and bounded-worker model remain authoritative.

## 0.4.0

Controlled Codex coordinator dispatch on top of the 0.3 audit record:

- `qagents swarm plan` remains deterministic and plan-only; it validates and emits
  packets but never launches agents;
- Codex native multi-agent tools perform bounded worker lifecycle, while
  QuattroAgents MCP records task claims, leases, runs, snapshots, artifacts and
  evidence;
- deterministic dependency waves, packet-only worker context, result envelopes,
  lease release, independent review, and sequential fallback make dispatch auditable;
- `max_threads` is a configured concurrency ceiling only, not an automatic spawning
  mechanism or a QuattroAgents worker-count guarantee;
- a real multi-agent demonstration must be recorded with evidence before claiming
  operational results; the documentation defines the required evidence but does not
  claim that demonstration has already occurred.

Controlled self-configuration continues to be proposal-only, gated by independent
review and human approval; it never activates configuration automatically.

## 0.5.0

Local skills and assisted optimization: identify repeated, deterministic operations that can be implemented as local scripts and exposed to agents as skills. Any claim about token reduction, speed, cost, or quality requires a reproducible benchmark; unverified theoretical savings are not reported. This remains separate from 0.3 self-hosting and does not permit automatic configuration activation.

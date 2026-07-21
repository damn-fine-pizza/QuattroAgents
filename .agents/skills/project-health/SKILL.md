---
name: project-health
description: Declarative protocol for collecting reproducible local project-health observations.
---

# Project health

`scripts/project-health.sh [PROJECT_ROOT]` emits the local `doctor` and
`validate` JSON observations for the supplied project root (or the current
directory). It is a deterministic local script; it does not render registry
configuration, dispatch work, invoke an LLM, or change project state.

## Paired observation protocol

Compare a `baseline` condition with an `assisted` condition only when both use:

- the same fixed commit and the same tracked/untracked worktree state;
- the same environment, including OS, shell, Python virtual environment,
  dependency versions, relevant environment variables, and machine resources;
- equivalent inputs, task scope, commands, acceptance criteria, and human
  decisions;
- the same number of repetitions, recorded separately; and
- the same failure policy: retain failed, timed-out, and invalid runs rather
  than silently retrying or excluding them.

Preserve the complete raw stdout, stderr, exit status, invocation, timestamps,
and condition label for every repetition. Summaries must link back to those raw
outputs and distinguish a script failure from a failed health check.

## Limitations

These observations describe only the recorded local checks under the stated
conditions. They are not claims about token use, cost savings, speed,
throughput, correctness, quality, or general performance. A paired result is
not comparable when commit, environment, equivalence, repetition count, or
failure handling differs.

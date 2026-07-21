# Benchmarking

Compare A: one medium agent; B: medium orchestrator plus small worker; C: B plus context manifest; D: C plus MCP; and later E: adaptive parallelism. Report accepted tasks per quota unit only from real data, with duration, retries, escalation, summaries and repeated reads.

## Project-health paired observations

Use `scripts/project-health.sh [PROJECT_ROOT]` to record local `doctor` and
`validate` JSON for a `baseline` and an `assisted` condition. It is an
observation script only: it does not configure a registry, auto-dispatch work,
or invoke an LLM.

For a valid pair, pin the same commit and worktree state, use the same complete
environment (including virtualenv, dependencies, variables, machine and
resource conditions), and make inputs, task scope, commands, acceptance
criteria, and human decisions equivalent. Run each condition for the same
number of repetitions. Keep every failure, timeout, and invalid run under one
shared failure policy; do not hide them with unrecorded retries or exclusions.

For every repetition, retain raw stdout, stderr, exit status, command,
timestamps, and condition label. A summary must point to those raw outputs and
separate script failures from failed health checks.

### Limitations

These paired observations are limited to the checks recorded under the fixed
conditions. They are not token, cost-saving, speed, throughput, correctness,
quality, or general-performance claims. Do not compare results when the fixed
commit, environment, equivalence, repetition count, or failure treatment
differs.

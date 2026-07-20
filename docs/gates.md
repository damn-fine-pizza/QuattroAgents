# Gates

Hard gates protect the central routing, configuration, control-plane, validation and canonical policy files. Runtime gates require contracts, scope, evidence and acceptance commands. The strictest gate wins.

## CI quality gates

The GitHub Actions workflow makes the following checks required for pull requests to `main`. They are intentionally split so failures are precise while the total run remains short.

| Gate | Command or evidence | Purpose |
| --- | --- | --- |
| Install smoke | `.venv/bin/python -m pip install .` and `-m quattroagents --help` on Python 3.11 and 3.12 | Verify a clean runtime installation on the supported range. |
| Test suite | `.venv/bin/python -m pytest` | Verify unit and integration behavior. |
| Static quality | Ruff check, Ruff format check, and mypy | Enforce lint, formatting, and strict types. |
| QuattroAgents validation | `.venv/bin/python -m quattroagents validate --json` | Verify canonical project state. |
| Delivery artifact | `.venv/bin/python -m build` plus uploaded `dist/` artifact | Verify that an installable sdist and wheel can be produced. |
| Provider adapters | Targeted adapter/setup tests for Codex and Claude | Verify generated configuration, skills, agents, MCP settings, and hooks. |

The CI workflow is a versioned operational policy, not a replacement for `.quattroagents/quality-gates.json`. Changes to that authoritative protected configuration still require human approval.

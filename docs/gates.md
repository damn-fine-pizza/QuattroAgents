# Gates

Hard gates protect the central routing, configuration, control-plane, validation and canonical policy files. Runtime gates require contracts, scope, evidence and acceptance commands. The strictest gate wins.

## CI quality gates

The GitHub Actions workflow runs after a push to `main` and can be started manually. With a protected `main` that accepts only pull-request merges, this runs once per merge and avoids duplicate PR compute. It intentionally provides post-merge evidence, not a GitHub pre-merge check.

Maintainers can also start the complete workflow from the repository **Actions** page: select **Quality gates**, choose **Run workflow**, and select the `main` branch or another branch containing the workflow file.

| Gate | Command or evidence | Purpose |
| --- | --- | --- |
| Install smoke | `.venv/bin/python -m pip install .` and `-m quattroagents --help` on Python 3.11 and 3.12 | Verify a clean runtime installation on the supported range. |
| Test suite | `.venv/bin/python -m pytest` | Verify unit and integration behavior. |
| Static quality | Ruff check, Ruff format check, and mypy | Enforce lint, formatting, and strict types. |
| QuattroAgents validation | `.venv/bin/python -m quattroagents validate --format json` | Verify canonical project state. |
| Delivery artifact | `.venv/bin/python -m build` plus uploaded `dist/` artifact | Verify that an installable sdist and wheel can be produced. |
| Provider adapters | Targeted adapter/setup tests for Codex and Claude | Verify generated configuration, skills, agents, MCP settings, and hooks. |

The CI workflow is a versioned operational policy, not a replacement for `.quattroagents/quality-gates.json`. Changes to that authoritative protected configuration still require human approval.

`qagents setup --yes` writes the same project-local `.githooks/pre-push` suite and activates it through `git config core.hooksPath .githooks` when the target is a Git repository. It runs the test suite, Ruff check and format check, mypy, QuattroAgents validation, and build before a push. Git hooks are a local safety net and can be bypassed, so maintainers should also protect `main` against direct pushes. Do not configure this workflow's status checks as required for PR merges: it does not run on `pull_request` events.

## Install local gate tools

Install all Python gate tools in the project virtual environment; do not rely on globally installed Python packages.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
```

This one command installs the package itself (`quattroagents` and `qagents`) and every Python command used by the gates:

| Command | Installation |
| --- | --- |
| `.venv/bin/python -m pytest` | Included in `.[dev]`. |
| `.venv/bin/python -m ruff` | Included in `.[dev]`. |
| `.venv/bin/python -m mypy` | Included in `.[dev]`. |
| `.venv/bin/python -m build` | Included in `.[dev]`. |
| `.venv/bin/python -m quattroagents` | Installed from this checkout by `-e ".[dev]"`; use it instead of a global `qagents`. |

`actionlint` checks GitHub Actions YAML and is optional for local work; GitHub remains the final workflow runner. Install it outside the Python environment with one of the official methods:

```sh
# macOS or Linux with Homebrew
brew install actionlint

# Any platform with Go installed; ensure "$(go env GOPATH)/bin" is on PATH
go install github.com/rhysd/actionlint/cmd/actionlint@latest
```

Then run `actionlint .github/workflows/ci.yml`. The [actionlint project documentation](https://github.com/rhysd/actionlint#readme) also provides signed release binaries and container-based alternatives.

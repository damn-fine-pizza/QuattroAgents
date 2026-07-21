# Gates

The quality gates run in two places: locally via Git hooks (fast feedback during development) and on GitHub Actions (authoritative post-merge verification). Both gates are designed to catch configuration issues, code quality problems, and test failures before they land on the main branch.

## GitHub Actions workflow

The workflow defined in `.github/workflows/ci.yml` runs after a push to `main` and can be started manually. With a protected `main` that accepts only pull-request merges, this ensures that the gates run once per merge and produce authoritative post-merge evidence (not a GitHub pre-merge check).

Maintainers can also manually trigger the workflow from the repository **Actions** page: select **Quality gates**, choose **Run workflow**, and select the `main` branch (or another branch containing the workflow file).

### CI jobs

| Job | Steps | Purpose |
| --- | --- | --- |
| Install smoke test | `.venv/bin/python -m pip install .` and `.venv/bin/python -m quattroagents --help` on Python 3.11 and 3.12 | Verify clean runtime installation across supported Python versions. |
| Quality gates | pytest, ruff check, ruff format check, mypy, qagents validate, build | Run the complete quality suite and verify deliverable artifacts. |
| Provider gates | pytest on `tests/integration/test_adapters_claude.py` and `tests/integration/test_adapters_codex.py` | Verify generated configuration, skills, agents, MCP settings, and hook output for both providers. |

## Local Git hooks

`scripts/setup.sh` (or manual `git config core.hooksPath .githooks`) activates project-local Git hooks. This is a repository dev-bootstrap step, separate from `qagents setup`, which only analyzes and renders agent/skill configuration and never touches Git hook configuration. These hooks are a fast, local safety net; they can be bypassed, so maintainers should also protect `main` against direct pushes.

### Pre-commit hook

`.githooks/pre-commit` runs three lightweight checks:
- `.venv/bin/python -m quattroagents validate --project .` — verify agent and skill definitions
- `.venv/bin/python -m ruff check .` — lint check
- `.venv/bin/python -m ruff format --check .` — formatting check

This hook catches configuration and formatting issues before a commit is created.

### Pre-push hook

`.githooks/pre-push` runs the complete quality suite before a push:
- `.venv/bin/python -m quattroagents validate --project .` — verify agent and skill definitions
- `.venv/bin/python -m pytest` — run all tests
- `.venv/bin/python -m ruff check .` — lint check
- `.venv/bin/python -m ruff format --check .` — formatting check
- `.venv/bin/python -m mypy src` — strict type checking
- `.venv/bin/python -m build` — verify the package can be built

## Configuration validation

`qagents validate --project .` (or `python -m quattroagents validate`) performs the following checks:

1. **Duplicate identifiers** — detects duplicate agent or skill IDs
2. **Completion criteria** — ensures all agents declare completion criteria
3. **Skill triggers or workflow** — ensures skills declare either a trigger or workflow steps
4. **Write-mode limits** — checks that write-enabled agents declare constraints or relevant paths
5. **Valid references** — ensures skills and swarm agents reference known agents
6. **Circular dependencies** — detects cycles in swarm agent dependencies
7. **Tool availability** — verifies that agents' mandatory tools are available
8. **Agent display format** — validates agent display lines follow the canonical format

The validation produces a report that indicates whether the configuration is valid or lists violations by code, message, and path.

## Manual releases

`.github/workflows/release.yml` is deliberately manual and produces no automatic releases. To release:

1. Merge the version change to `main`
2. Create and push the matching tag (e.g., `v1.0.0`)
3. Dispatch the workflow with that tag and a numeric build identifier
4. The workflow checks out that exact tag, verifies the package version matches, reruns the complete quality suite, builds the sdist and wheel, and creates a GitHub release

The workflow never creates, moves, or deletes tags — it only packages and releases a tag you provide.

## Install local gate tools

Install all Python gate tools in the project virtual environment; do not rely on globally installed packages.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
```

This single command installs the package (`quattroagents` and `qagents`) and all Python tools used by the gates:

| Command | Source |
| --- | --- |
| `.venv/bin/python -m pytest` | Included in `.[dev]` extras |
| `.venv/bin/python -m ruff` | Included in `.[dev]` extras |
| `.venv/bin/python -m mypy` | Included in `.[dev]` extras |
| `.venv/bin/python -m build` | Included in `.[dev]` extras |
| `.venv/bin/python -m quattroagents` | Installed from this checkout via `-e ".[dev]"` |

### Optional: actionlint

`actionlint` validates GitHub Actions YAML and is optional for local work (GitHub Actions remains the authoritative runner). Install it outside the Python environment:

```sh
# macOS or Linux with Homebrew
brew install actionlint

# Any platform with Go installed (ensure "$(go env GOPATH)/bin" is on PATH)
go install github.com/rhysd/actionlint/cmd/actionlint@latest
```

Then run: `actionlint .github/workflows/ci.yml .github/workflows/release.yml`

See the [actionlint documentation](https://github.com/rhysd/actionlint#readme) for signed release binaries and container-based alternatives.

# QuattroAgents MCP installation

QuattroAgents is a local **stdio** MCP server. `/mcp` in Codex shows server status; it does not add servers. Add servers from a terminal with `codex mcp add` or `claude mcp add`.

The direct commands below do **not** require a QuattroAgents checkout or a pre-installed `qagents`. Choose either `uvx` or `pipx`; each fetches QuattroAgents from GitHub on first server start and reuses an isolated cache afterwards. `mcp add --url` is not appropriate: the GitHub repository is source code, not a streamable HTTP MCP endpoint.

## Prerequisite: a local runner

An MCP configuration records an executable to start, so one local runner is still necessary. Either option below avoids cloning or installing QuattroAgents itself.

- [`uvx`](https://docs.astral.sh/uv/getting-started/installation/) runs a Python command from an isolated cached environment.
- [`pipx run`](https://pipx.pypa.io/stable/how-to/run-scripts/) does the same with a temporary cached environment and accepts Git sources through `--spec`.

```sh
uvx --version    # option A
pipx --version   # option B
```

## Direct `mcp add`

Run these commands from the repository you want QuattroAgents to manage. They store an absolute project path so the server does not depend on a later shell working directory.

```sh
QA_ROOT=$(pwd)
QA_SOURCE="git+https://github.com/damn-fine-pizza/QuattroAgents.git@main"
```

### Codex

```sh
codex mcp add quattroagents -- \
  uvx --from "$QA_SOURCE" qagents mcp serve --project "$QA_ROOT"

codex mcp list
```

Without `uvx`, use `pipx` instead:

```sh
codex mcp add quattroagents -- \
  pipx run --spec "$QA_SOURCE" qagents mcp serve --project "$QA_ROOT"
```

Restart Codex, then use `/mcp` to inspect the connected server.

### Claude Code

Use `project` to share configuration with the repository, `user` for every local project, or `local` for the current project only.

```sh
claude mcp add --scope project quattroagents -- \
  uvx --from "$QA_SOURCE" qagents mcp serve --project "$QA_ROOT"

claude mcp list
```

Without `uvx`, use `pipx` instead:

```sh
claude mcp add --scope project quattroagents -- \
  pipx run --spec "$QA_SOURCE" qagents mcp serve --project "$QA_ROOT"
```

Restart Claude Code after adding the server.

## Project checkout alternative

For development of QuattroAgents itself, use its virtualenv and generate both provider adapters in one command:

```sh
.venv/bin/python -m quattroagents setup \
  --project . \
  --providers codex,claude \
  --profile economy \
  --install-mcp recommended \
  --yes
```

## Manual configuration

The same direct runner can be recorded without CLI helpers.

For Codex, add this table to `.codex/config.toml`:

```toml
[mcp_servers.quattroagents]
command = "uvx"
args = [
  "--from",
  "git+https://github.com/damn-fine-pizza/QuattroAgents.git@main",
  "qagents",
  "mcp",
  "serve",
  "--project",
  ".",
]
cwd = "."
startup_timeout_sec = 10
```

For Claude, add this entry to project `.mcp.json`:

```json
{
  "mcpServers": {
    "quattroagents": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/damn-fine-pizza/QuattroAgents.git@main",
        "qagents",
        "mcp",
        "serve",
        "--project",
        "."
      ]
    }
  }
}
```

For either manual configuration, the `pipx` variant uses `command = "pipx"` (or JSON `"command": "pipx"`) and replaces the initial `--from`, Git-source pair with `run`, `--spec`, Git-source.

## Verify and update

```sh
codex mcp list
claude mcp list
```

The commands report configuration and connection status. For reproducible environments, replace `@main` in every command with a Git tag or commit SHA. To force a fresh dependency resolution while debugging, use the runner's documented cache controls (for example, `pipx run --no-cache`).

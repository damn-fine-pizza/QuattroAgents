---
name: rtk
description: Use RTK for concise, token-efficient repository diagnostics when the optional rtk CLI is installed. Trigger for compact Git status, test, Ruff, mypy, or ripgrep output; retain native commands when exact output or a project virtualenv command is required.
---

# RTK

Run `scripts/detect-rtk.sh` before relying on RTK. If it is unavailable, use the native command; never install RTK automatically.

Use `scripts/rtk.sh` for dedicated RTK commands such as `git`, `pytest`, `ruff`, `mypy`, and `rg`; the launcher exposes the project's `.venv/bin` tools. Do not use `rtk run`, because it evaluates a shell command.

For project verification, run the required `.venv/bin/python -m ...` command directly rather than a condensed RTK invocation.

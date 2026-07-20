---
name: rtk
description: Use RTK for concise, token-efficient repository diagnostics when the optional rtk CLI is installed. Trigger for compact Git status, test, Ruff, mypy, or ripgrep output; retain native commands when exact output or a project virtualenv command is required.
---

# RTK

Run `scripts/detect-rtk.sh` before relying on RTK. If it is unavailable, use the native command; never install RTK automatically.

Use dedicated RTK commands such as `rtk git`, `rtk pytest`, `rtk ruff`, `rtk mypy`, and `rtk rg` for concise diagnostics. Do not use `rtk run`, because it evaluates a shell command.

RTK discovers underlying executables through `PATH`. For project verification that must use the virtual environment, run the required `.venv/bin/python -m ...` command directly, especially when a formatter or linter is not globally installed.

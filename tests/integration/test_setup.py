from pathlib import Path

from quattroagents.cli import write_hooks


def test_write_hooks_uses_project_virtualenv_and_full_quality_suite(tmp_path: Path) -> None:
    write_hooks(tmp_path)

    hooks = tmp_path / ".githooks"
    assert (hooks / "commit-msg").read_text().startswith("#!/bin/sh\nset -eu\n")
    assert (
        ".venv/bin/python -m quattroagents validate --project . --json"
        in (hooks / "pre-commit").read_text()
    )
    pre_push = (hooks / "pre-push").read_text()
    assert ".venv/bin/python -m pytest" in pre_push
    assert ".venv/bin/python -m ruff check ." in pre_push
    assert ".venv/bin/python -m mypy src" in pre_push

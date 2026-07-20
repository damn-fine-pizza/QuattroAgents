import subprocess
from pathlib import Path

from quattroagents.cli import enable_project_hooks, write_hooks


def test_write_hooks_uses_project_virtualenv_and_full_quality_suite(tmp_path: Path) -> None:
    write_hooks(tmp_path)

    hooks = tmp_path / ".githooks"
    assert (hooks / "commit-msg").read_text().startswith("#!/bin/sh\nset -eu\n")
    assert (
        ".venv/bin/python -m quattroagents validate --project . --format json"
        in (hooks / "pre-commit").read_text()
    )
    pre_push = (hooks / "pre-push").read_text()
    assert ".venv/bin/python -m pytest" in pre_push
    assert ".venv/bin/python -m ruff check ." in pre_push
    assert ".venv/bin/python -m ruff format --check ." in pre_push
    assert ".venv/bin/python -m mypy src" in pre_push
    assert ".venv/bin/python -m build" in pre_push


def test_enable_project_hooks_configures_only_a_git_repository(tmp_path: Path) -> None:
    assert enable_project_hooks(tmp_path) is False

    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True, text=True)

    assert enable_project_hooks(tmp_path) is True
    result = subprocess.run(
        ["git", "-C", str(tmp_path), "config", "--get", "core.hooksPath"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == ".githooks"

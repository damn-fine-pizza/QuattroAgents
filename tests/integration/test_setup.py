import json
import subprocess
from pathlib import Path

from quattroagents.adapters.registry import render
from quattroagents.cli import configure_generated_agents, enable_project_hooks, write_hooks
from quattroagents.core.setup_history import SetupHistoryStore


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


def test_orchestration_skill_requires_explicit_provider_render(tmp_path: Path) -> None:
    already_configured = tmp_path / "already-configured"
    (already_configured / ".codex").mkdir(parents=True)
    (already_configured / ".codex/config.toml").write_text("agents.max_threads = 2\n")
    (already_configured / ".claude").mkdir()
    (already_configured / ".claude/settings.json").write_text("{}\n")
    codex_skill = already_configured / ".agents/skills/qagents-orchestrate/SKILL.md"
    claude_skill = already_configured / ".claude/skills/qagents-orchestrate/SKILL.md"

    assert not codex_skill.exists()
    assert not claude_skill.exists()

    render(already_configured, ["codex"])

    assert codex_skill.exists()
    assert not claude_skill.exists()


def test_configure_generated_agents_baseline_matches_default_manifest(tmp_path: Path) -> None:
    files = configure_generated_agents(tmp_path, ["claude"], "economy")

    assert ".claude" in files
    latest = SetupHistoryStore().latest(tmp_path)
    assert latest is not None
    assert latest["interview"]["status"] == "default"
    assert all(skill["source"] == "fleet-default" for skill in latest["manifest"]["skills"])


def test_configure_generated_agents_answers_file_produces_tailored_manifest(tmp_path: Path) -> None:
    answers_file = tmp_path / "answers.json"
    answers_file.write_text(
        json.dumps({"SETUP-1": "Ship a CLI.", "SETUP-2": "Small changes only.", "SETUP-3": "rtk"})
    )

    configure_generated_agents(tmp_path, ["claude"], "economy", answers_file=str(answers_file))

    latest = SetupHistoryStore().latest(tmp_path)
    assert latest is not None
    assert latest["interview"]["status"] == "confirmed"
    tooling_skill = next(
        skill for skill in latest["manifest"]["skills"] if skill["name"] == "qagents-tooling"
    )
    assert tooling_skill["source"] == "adhoc"
    bounded_worker = (tmp_path / ".claude/agents/bounded-worker.md").read_text()
    assert "Ship a CLI." in bounded_worker


def test_configure_generated_agents_carries_forward_history_on_a_second_run(tmp_path: Path) -> None:
    answers_file = tmp_path / "answers.json"
    answers_file.write_text(
        json.dumps({"SETUP-1": "Ship a CLI.", "SETUP-2": "x", "SETUP-3": "rtk"})
    )
    configure_generated_agents(tmp_path, ["claude"], "economy", answers_file=str(answers_file))

    configure_generated_agents(tmp_path, ["claude"], "economy")

    history = SetupHistoryStore().recent(tmp_path)
    assert len(history) == 2
    assert history[0]["interview"]["status"] == "carried_forward"
    assert history[0]["interview"]["answers"]["SETUP-1"] == "Ship a CLI."

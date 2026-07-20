import json
import subprocess
import sys
from pathlib import Path

import pytest

from quattroagents.cli import _maximum_parallel_workers
from quattroagents.control_plane.tasks import ControlPlane


def test_swarm_plan_and_interview_cli(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    config_dir = tmp_path / ".codex"
    config_dir.mkdir()
    config_path = config_dir / "config.toml"
    tasks = ControlPlane(tmp_path / ".quattroagents" / "control-plane.sqlite3")
    tasks.create(
        "TASK-001",
        {
            "objective": "Document swarm planning",
            "milestone": "0.2.0",
            "requirements": [{"id": "REQ-1", "text": "Render a plan"}],
            "acceptance_commands": ["pytest"],
            "interview": {
                "status": "confirmed",
                "answers": {
                    "INTENT-1": "Document the plan.",
                    "INTENT-2": "Only documentation is in scope.",
                    "INTENT-3": "The CLI test passes.",
                    "INTENT-4": "Do not alter protected files.",
                    "INTENT-5": "No parallel worker is needed.",
                },
            },
            "swarm_work_items": [
                {
                    "id": "docs",
                    "objective": "Write documentation",
                    "requirements": ["REQ-1"],
                    "allowed_files": ["README.md"],
                    "context_refs": ["docs/swarm.md"],
                    "depends_on": [],
                }
            ],
        },
    )
    with pytest.raises(ValueError, match="missing required scheduling configuration"):
        _maximum_parallel_workers(tmp_path)
    config_path.write_text("agents.max_threads = 1\n", encoding="utf-8")

    plan = subprocess.run(
        [
            sys.executable,
            "-m",
            "quattroagents",
            "swarm",
            "plan",
            "TASK-001",
            "--project",
            str(tmp_path),
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    interview = subprocess.run(
        [
            sys.executable,
            "-m",
            "quattroagents",
            "interview",
            "--project",
            str(root),
            "--format",
            "markdown",
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    interactive = subprocess.run(
        [
            sys.executable,
            "-m",
            "quattroagents",
            "interview",
            "--project",
            str(root),
            "--interactive",
            "--format",
            "json",
        ],
        cwd=root,
        check=True,
        input="\n".join(
            [
                "Document a command.",
                "Only local files.",
                "Tests pass.",
                "No protected changes.",
                "Review after planning.",
            ]
        )
        + "\n",
        capture_output=True,
        text=True,
    )
    legacy = subprocess.run(
        [sys.executable, "-m", "quattroagents", "analyze", "--project", str(root), "--json"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )

    rendered_plan = json.loads(plan.stdout)
    assert rendered_plan["waves"][0]["workers"][0]["id"] == "docs"
    assert rendered_plan["scheduling"] == {
        "maximum_parallel_workers": 1,
    }
    assert "codex" not in json.dumps(rendered_plan).lower()
    config_path.write_text("agents.max_threads = 0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="agents.max_threads must be a positive integer"):
        _maximum_parallel_workers(tmp_path)
    assert "# User-intent interview" in interview.stdout
    assert json.loads(interactive.stdout)["status"] == "confirmed"
    assert legacy.returncode == 2
    assert "unrecognized arguments: --json" in legacy.stderr

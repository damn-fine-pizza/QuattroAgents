import json
import subprocess
import sys
from pathlib import Path

from quattroagents.control_plane.tasks import ControlPlane


def test_swarm_plan_and_interview_cli(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
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

    assert json.loads(plan.stdout)["waves"][0]["workers"][0]["id"] == "docs"
    assert "# User-intent interview" in interview.stdout
    assert json.loads(interactive.stdout)["status"] == "confirmed"
    assert legacy.returncode == 2
    assert "unrecognized arguments: --json" in legacy.stderr

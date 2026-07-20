import json
import subprocess
import sys
from pathlib import Path

from quattroagents.control_plane.tasks import ControlPlane


def _run(root: Path, project: Path, *args: str) -> dict[str, object]:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "quattroagents",
            *args,
            "--project",
            str(project),
            "--format",
            "json",
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def test_self_hosting_run_cli_creates_and_verifies_snapshot(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    ControlPlane(tmp_path / ".quattroagents" / "control-plane.sqlite3").create("TASK-001", {})

    created = _run(
        root,
        tmp_path,
        "self-hosting",
        "run",
        "create",
        "RUN-001",
        "TASK-001",
        "--source-commit",
        "ff8905149062",
        "--runtime-version",
        "0.2.2+gff8905149062",
    )
    snapshot = _run(
        root,
        tmp_path,
        "self-hosting",
        "run",
        "snapshot",
        "RUN-001",
        "SNAP-001",
        "plan",
        "--summary",
        "Plan prepared without launching an agent.",
    )
    verified = _run(root, tmp_path, "self-hosting", "run", "verify", "RUN-001")

    assert created["id"] == "RUN-001"
    assert snapshot["stage"] == "plan"
    assert verified == {"valid": True, "run_id": "RUN-001", "snapshots": 1}

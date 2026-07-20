import json
import subprocess
import sys
from pathlib import Path


def test_tasks_list_filters_by_milestone(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    database = tmp_path / ".quattroagents" / "control-plane.sqlite3"
    database.parent.mkdir()
    requests = "\n".join(
        (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "task_create",
                        "arguments": {
                            "task_id": "TASK-001",
                            "payload": {"milestone": "0.2.0"},
                        },
                    },
                }
            ),
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "task_create",
                        "arguments": {
                            "task_id": "TASK-002",
                            "payload": {"milestone": "0.3.0"},
                        },
                    },
                }
            ),
        )
    )
    subprocess.run(
        [sys.executable, "-m", "quattroagents", "mcp", "serve", "--project", str(tmp_path)],
        cwd=root,
        input=f"{requests}\n",
        check=True,
        capture_output=True,
        text=True,
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "quattroagents",
            "tasks",
            "list",
            "--project",
            str(tmp_path),
            "--milestone",
            "0.2.0",
            "--json",
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(result.stdout) == [
        {
            "id": "TASK-001",
            "payload": {"milestone": "0.2.0"},
            "milestone": "0.2.0",
            "status": "ready",
            "claimant": None,
        }
    ]

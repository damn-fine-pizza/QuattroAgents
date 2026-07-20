import json
import subprocess
import sys
from pathlib import Path

from quattroagents import runtime_version


def test_mcp_server_does_not_respond_to_initialized_notification() -> None:
    root = Path(__file__).parents[2]
    requests = "\n".join(
        (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {},
                        "clientInfo": {"name": "codex", "version": "0.144.6"},
                    },
                }
            ),
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
        )
    )
    result = subprocess.run(
        [sys.executable, "-m", "quattroagents", "mcp", "serve", "--project", "."],
        cwd=root,
        input=f"{requests}\n",
        check=True,
        capture_output=True,
        text=True,
    )

    responses = [json.loads(line) for line in result.stdout.splitlines()]
    assert responses[0] == {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "quattroagents", "version": runtime_version()},
            "capabilities": {"tools": {}, "resources": {}},
        },
    }
    assert responses[1]["jsonrpc"] == "2.0"
    assert responses[1]["id"] == 2
    assert responses[1]["result"]["tools"] == [
        {
            "name": name,
            "description": name.replace("_", " "),
            "inputSchema": {"type": "object", "additionalProperties": True},
        }
        for name in (
            "task_create",
            "task_claim",
            "task_update",
            "task_query",
            "run_create",
            "run_snapshot",
            "run_query",
            "run_verify",
            "artifact_register",
            "lease_acquire",
            "lease_release",
            "decision_propose",
        )
    ]


def test_mcp_server_persists_and_queries_task_milestones(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
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
                        "name": "task_query",
                        "arguments": {"milestone": "0.2.0"},
                    },
                }
            ),
        )
    )
    result = subprocess.run(
        [sys.executable, "-m", "quattroagents", "mcp", "serve", "--project", str(tmp_path)],
        cwd=root,
        input=f"{requests}\n",
        check=True,
        capture_output=True,
        text=True,
    )

    responses = [json.loads(line) for line in result.stdout.splitlines()]
    query = json.loads(responses[1]["result"]["content"][0]["text"])
    assert query == [
        {
            "id": "TASK-001",
            "payload": {"milestone": "0.2.0"},
            "milestone": "0.2.0",
            "status": "ready",
            "claimant": None,
        }
    ]


def test_mcp_server_records_and_verifies_run_snapshots(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    requests = "\n".join(
        (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "task_create",
                        "arguments": {"task_id": "TASK-001", "payload": {}},
                    },
                }
            ),
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "run_create",
                        "arguments": {
                            "run_id": "RUN-001",
                            "task_id": "TASK-001",
                            "source_commit": "ff8905149062",
                            "runtime_version": "0.2.2+gff8905149062",
                        },
                    },
                }
            ),
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "run_snapshot",
                        "arguments": {
                            "run_id": "RUN-001",
                            "snapshot_id": "SNAP-001",
                            "stage": "plan",
                            "summary": "Plan is ready for bounded execution.",
                            "artifacts": [],
                            "evidence": [],
                            "changed_files": [],
                        },
                    },
                }
            ),
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {"name": "run_verify", "arguments": {"run_id": "RUN-001"}},
                }
            ),
        )
    )
    result = subprocess.run(
        [sys.executable, "-m", "quattroagents", "mcp", "serve", "--project", str(tmp_path)],
        cwd=root,
        input=f"{requests}\n",
        check=True,
        capture_output=True,
        text=True,
    )

    responses = [json.loads(line) for line in result.stdout.splitlines()]
    verified = json.loads(responses[3]["result"]["content"][0]["text"])
    assert verified == {"valid": True, "run_id": "RUN-001", "snapshots": 1}


def test_mcp_server_preserves_request_id_on_tool_error(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    request = {
        "jsonrpc": "2.0",
        "id": 42,
        "method": "tools/call",
        "params": {"name": "task_create", "arguments": {}},
    }

    result = subprocess.run(
        [sys.executable, "-m", "quattroagents", "mcp", "serve", "--project", str(tmp_path)],
        cwd=root,
        input=f"{json.dumps(request)}\n",
        check=True,
        capture_output=True,
        text=True,
    )

    response = json.loads(result.stdout)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 42
    assert response["error"]["code"] == -32000
    assert "task_id" in response["error"]["message"]

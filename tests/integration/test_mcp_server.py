import json
import subprocess
import sys
from pathlib import Path


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
            "serverInfo": {"name": "quattroagents", "version": "0.2.0"},
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
            "artifact_register",
            "lease_acquire",
            "lease_release",
            "decision_propose",
        )
    ]

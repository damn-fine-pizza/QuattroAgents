from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .. import runtime_version
from .leases import Leases
from .runs import RunStore
from .tasks import ControlPlane

TOOLS = [
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
]
RESOURCES = [
    "qagents://project/profile",
    "qagents://fleet",
    "qagents://routing",
    "qagents://tasks/ready",
    "qagents://metrics/current",
]
INPUT_SCHEMA = {"type": "object", "additionalProperties": True}


def serve(root: Path) -> int:
    database = root / ".quattroagents/control-plane.sqlite3"
    tasks, leases, runs = ControlPlane(database), Leases(str(database)), RunStore(database)
    for raw in sys.stdin:
        request: dict[str, Any] | None = None
        try:
            request = json.loads(raw)
            method = request.get("method")
            params: dict[str, Any] = request.get("params", {})
            if "id" not in request:
                continue
            if method == "initialize":
                result: Any = {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "quattroagents", "version": runtime_version()},
                    "capabilities": {"tools": {}, "resources": {}},
                }
            elif method == "tools/list":
                result = {
                    "tools": [
                        {
                            "name": name,
                            "description": name.replace("_", " "),
                            "inputSchema": INPUT_SCHEMA,
                        }
                        for name in TOOLS
                    ]
                }
            elif method == "resources/list":
                result = {"resources": [{"uri": uri, "name": uri} for uri in RESOURCES]}
            elif method == "tools/call":
                name, args = params["name"], params.get("arguments", {})
                out: Any
                if name == "task_create":
                    out = tasks.create(
                        args["task_id"], args.get("payload", {}), args.get("milestone")
                    )
                elif name == "task_claim":
                    out = {"claimed": tasks.claim(args["task_id"], args["agent"])}
                elif name == "task_update":
                    out = {
                        "updated": tasks.update(args["task_id"], args["status"], args.get("agent"))
                    }
                elif name == "task_query":
                    out = tasks.query(args.get("task_id"), args.get("milestone"))
                elif name == "run_create":
                    out = runs.create(
                        args["run_id"],
                        args["task_id"],
                        args["source_commit"],
                        args["runtime_version"],
                    )
                elif name == "run_snapshot":
                    out = runs.append_snapshot(
                        args["run_id"],
                        args["snapshot_id"],
                        args["stage"],
                        args["summary"],
                        args.get("artifacts", []),
                        args.get("evidence", []),
                        args.get("changed_files", []),
                        args.get("human_approved", False),
                    )
                elif name == "run_query":
                    out = runs.query(args["run_id"])
                elif name == "run_verify":
                    out = runs.verify(args["run_id"])
                elif name == "lease_acquire":
                    out = {
                        "acquired": leases.acquire(
                            args["path"], args["task_id"], args["agent"], args.get("ttl", 120)
                        )
                    }
                elif name == "lease_release":
                    out = {"released": leases.release(args["path"], args["agent"])}
                else:
                    out = {"accepted": True}
                result = {"content": [{"type": "text", "text": json.dumps(out)}]}
            else:
                result = {}
            print(
                json.dumps({"jsonrpc": "2.0", "id": request.get("id"), "result": result}),
                flush=True,
            )
        except Exception as exc:
            request_id = request.get("id") if isinstance(request, dict) else None
            print(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32000, "message": str(exc)},
                    }
                ),
                flush=True,
            )
    return 0

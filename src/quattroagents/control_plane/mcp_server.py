from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .leases import Leases
from .tasks import ControlPlane

TOOLS = [
    "task_create",
    "task_claim",
    "task_update",
    "task_query",
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


def serve(root: Path) -> int:
    database = root / ".quattroagents/control-plane.sqlite3"
    tasks, leases = ControlPlane(database), Leases(str(database))
    for raw in sys.stdin:
        try:
            request = json.loads(raw)
            method = request.get("method")
            params: dict[str, Any] = request.get("params", {})
            if method == "initialize":
                result: Any = {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "quattroagents", "version": "0.2.0"},
                    "capabilities": {"tools": {}, "resources": {}},
                }
            elif method == "tools/list":
                result = {"tools": [{"name": name, "description": name} for name in TOOLS]}
            elif method == "resources/list":
                result = {"resources": [{"uri": uri, "name": uri} for uri in RESOURCES]}
            elif method == "tools/call":
                name, args = params["name"], params.get("arguments", {})
                out: Any
                if name == "task_create":
                    out = tasks.create(args["task_id"], args.get("payload", {}))
                elif name == "task_claim":
                    out = {"claimed": tasks.claim(args["task_id"], args["agent"])}
                elif name == "task_update":
                    out = {
                        "updated": tasks.update(args["task_id"], args["status"], args.get("agent"))
                    }
                elif name == "task_query":
                    out = tasks.query(args.get("task_id"))
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
            print(
                json.dumps(
                    {"jsonrpc": "2.0", "id": None, "error": {"code": -32000, "message": str(exc)}}
                ),
                flush=True,
            )
    return 0

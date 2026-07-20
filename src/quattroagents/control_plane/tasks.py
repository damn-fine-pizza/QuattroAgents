from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .database import connect


class ControlPlane:
    def __init__(self, database: Path) -> None:
        self.database = database

    def create(self, task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with connect(self.database) as con:
            con.execute(
                "INSERT INTO tasks VALUES (?, ?, 'ready', NULL, ?)",
                (task_id, json.dumps(payload), time.time()),
            )
        result = self.query(task_id)
        assert isinstance(result, dict)
        return result

    def claim(self, task_id: str, agent: str) -> bool:
        with connect(self.database) as con:
            cur = con.execute(
                "UPDATE tasks SET status='claimed', claimant=?, updated_at=? WHERE id=? AND status='ready'",
                (agent, time.time(), task_id),
            )
            return cur.rowcount == 1

    def update(self, task_id: str, status: str, agent: str | None = None) -> bool:
        if status not in {
            "ready",
            "claimed",
            "completed",
            "blocked",
            "failed",
            "released",
            "heartbeat",
        }:
            raise ValueError("invalid task status")
        target = (
            "ready" if status == "released" else ("claimed" if status == "heartbeat" else status)
        )
        with connect(self.database) as con:
            cur = con.execute(
                "UPDATE tasks SET status=?, claimant=COALESCE(?, claimant), updated_at=? WHERE id=?",
                (target, agent, time.time(), task_id),
            )
            return cur.rowcount == 1

    def query(self, task_id: str | None = None) -> dict[str, Any] | list[dict[str, Any]]:
        with connect(self.database) as con:
            rows = con.execute(
                "SELECT * FROM tasks" + (" WHERE id=?" if task_id else " ORDER BY id"),
                (() if not task_id else (task_id,)),
            ).fetchall()
        values = [
            {
                "id": r["id"],
                "payload": json.loads(r["payload"]),
                "status": r["status"],
                "claimant": r["claimant"],
            }
            for r in rows
        ]
        if task_id:
            if not values:
                raise KeyError(task_id)
            return values[0]
        return values

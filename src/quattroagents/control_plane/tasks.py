from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .database import connect


class ControlPlane:
    def __init__(self, database: Path) -> None:
        self.database = database

    def create(
        self, task_id: str, payload: dict[str, Any], milestone: str | None = None
    ) -> dict[str, Any]:
        payload_milestone = payload.get("milestone")
        if payload_milestone is not None and not isinstance(payload_milestone, str):
            raise ValueError("milestone must be a string")
        if milestone is not None and not isinstance(milestone, str):
            raise ValueError("milestone must be a string")
        if (
            milestone is not None
            and payload_milestone is not None
            and milestone != payload_milestone
        ):
            raise ValueError("milestone must match the task contract")
        selected_milestone = milestone if milestone is not None else payload_milestone
        if selected_milestone is not None and not selected_milestone.strip():
            raise ValueError("milestone must not be empty")
        with connect(self.database) as con:
            con.execute(
                "INSERT INTO tasks (id, payload, milestone, status, claimant, updated_at) "
                "VALUES (?, ?, ?, 'ready', NULL, ?)",
                (task_id, json.dumps(payload), selected_milestone, time.time()),
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

    def query(
        self, task_id: str | None = None, milestone: str | None = None
    ) -> dict[str, Any] | list[dict[str, Any]]:
        with connect(self.database) as con:
            conditions: list[str] = []
            parameters: list[str] = []
            if task_id:
                conditions.append("id=?")
                parameters.append(task_id)
            if milestone is not None:
                conditions.append("milestone=?")
                parameters.append(milestone)
            statement = "SELECT * FROM tasks"
            if conditions:
                statement += " WHERE " + " AND ".join(conditions)
            rows = con.execute(statement + " ORDER BY id", parameters).fetchall()
        values = [
            {
                "id": r["id"],
                "payload": json.loads(r["payload"]),
                "milestone": r["milestone"],
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

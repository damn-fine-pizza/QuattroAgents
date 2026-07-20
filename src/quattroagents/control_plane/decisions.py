from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .database import connect

_STATUSES = {"proposed", "accepted", "rejected", "superseded"}


class DecisionStore:
    """Lifecycle-tracked decision proposals, reusing the existing `decisions` table."""

    def __init__(self, database: Path) -> None:
        self.database = database

    def propose(
        self,
        decision_id: str,
        kind: str,
        summary: str,
        payload: dict[str, Any] | None = None,
        requested_by: str | None = None,
    ) -> dict[str, Any]:
        record = {
            "schema_version": 1,
            "id": decision_id,
            "kind": kind,
            "summary": summary,
            "payload": payload or {},
            "requested_by": requested_by,
            "proposed_at": time.time(),
            "decided_by": None,
            "decided_at": None,
            "rationale": None,
        }
        with connect(self.database) as con:
            con.execute(
                "INSERT INTO decisions (id, proposal, status) VALUES (?, ?, 'proposed')",
                (decision_id, json.dumps(record)),
            )
        result = self.query(decision_id)
        assert isinstance(result, dict)
        return result

    def resolve(
        self,
        decision_id: str,
        status: str,
        decided_by: str | None = None,
        rationale: str | None = None,
    ) -> dict[str, Any]:
        if status not in _STATUSES - {"proposed"}:
            raise ValueError(
                f"status must be one of: {', '.join(sorted(_STATUSES - {'proposed'}))}"
            )
        existing = self.query(decision_id)
        assert isinstance(existing, dict)
        record = {
            **existing,
            "decided_by": decided_by,
            "decided_at": time.time(),
            "rationale": rationale,
        }
        with connect(self.database) as con:
            cur = con.execute(
                "UPDATE decisions SET proposal=?, status=? WHERE id=?",
                (json.dumps(record), status, decision_id),
            )
            if cur.rowcount != 1:
                raise KeyError(decision_id)
        result = self.query(decision_id)
        assert isinstance(result, dict)
        return result

    def query(
        self, decision_id: str | None = None, status: str | None = None
    ) -> dict[str, Any] | list[dict[str, Any]]:
        with connect(self.database) as con:
            conditions: list[str] = []
            parameters: list[str] = []
            if decision_id:
                conditions.append("id=?")
                parameters.append(decision_id)
            if status is not None:
                conditions.append("status=?")
                parameters.append(status)
            statement = "SELECT * FROM decisions"
            if conditions:
                statement += " WHERE " + " AND ".join(conditions)
            rows = con.execute(statement + " ORDER BY id", parameters).fetchall()
        values = [{**json.loads(r["proposal"]), "status": r["status"]} for r in rows]
        if decision_id:
            if not values:
                raise KeyError(decision_id)
            return values[0]
        return values

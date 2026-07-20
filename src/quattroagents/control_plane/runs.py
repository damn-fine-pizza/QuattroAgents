from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, cast

from ..core.gates import allow_integration
from ..core.models import RunStage
from .database import connect

_STAGES = tuple(stage.value for stage in RunStage)


def _canonical(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _identifier(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _artifacts(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ValueError("artifacts must be a list")
    values: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("artifact must be an object")
        values.append(
            {
                "id": _identifier(item.get("id"), "artifact id"),
                "path": _identifier(item.get("path"), "artifact path"),
                "kind": _identifier(item.get("kind"), "artifact kind"),
                "sha256": _sha256(item.get("sha256"), "artifact sha256"),
            }
        )
    if len({item["id"] for item in values}) != len(values):
        raise ValueError("artifact ids must be unique within a snapshot")
    return values


def _evidence(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ValueError("evidence must be a list")
    values: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("evidence item must be an object")
        values.append(
            {
                "id": _identifier(item.get("id"), "evidence id"),
                "ref": _identifier(item.get("ref"), "evidence ref"),
                "sha256": _sha256(item.get("sha256"), "evidence sha256"),
            }
        )
    if len({item["id"] for item in values}) != len(values):
        raise ValueError("evidence ids must be unique within a snapshot")
    return values


def _changed_files(value: object) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError("changed_files must be a list of non-empty strings")
    return list(value)


class RunStore:
    """Append-only self-hosting run and snapshot persistence."""

    def __init__(self, database: Path) -> None:
        self.database = database

    def create(
        self, run_id: str, task_id: str, source_commit: str, runtime_version: str
    ) -> dict[str, Any]:
        run_id = _identifier(run_id, "run id")
        task_id = _identifier(task_id, "task id")
        source_commit = _identifier(source_commit, "source_commit")
        runtime_version = _identifier(runtime_version, "runtime_version")
        with connect(self.database) as con:
            if con.execute("SELECT 1 FROM tasks WHERE id=?", (task_id,)).fetchone() is None:
                raise KeyError(task_id)
            con.execute(
                "INSERT INTO runs (id, task_id, source_commit, runtime_version, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (run_id, task_id, source_commit, runtime_version, time.time()),
            )
        return self.query(run_id)

    def append_snapshot(
        self,
        run_id: str,
        snapshot_id: str,
        stage: str,
        summary: str,
        artifacts: object,
        evidence: object,
        changed_files: object,
        human_approved: bool = False,
    ) -> dict[str, Any]:
        run_id = _identifier(run_id, "run id")
        snapshot_id = _identifier(snapshot_id, "snapshot id")
        if stage not in _STAGES:
            raise ValueError(f"stage must be one of: {', '.join(_STAGES)}")
        summary = _identifier(summary, "summary")
        if not isinstance(human_approved, bool):
            raise ValueError("human_approved must be a boolean")
        artifact_values = _artifacts(artifacts)
        evidence_values = _evidence(evidence)
        changed = _changed_files(changed_files)
        with connect(self.database) as con:
            run = con.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if run is None:
                raise KeyError(run_id)
            previous = con.execute(
                "SELECT sequence, digest FROM run_snapshots WHERE run_id=? ORDER BY sequence DESC LIMIT 1",
                (run_id,),
            ).fetchone()
            sequence = 1 if previous is None else int(previous["sequence"]) + 1
            expected_stage = _STAGES[sequence - 1] if sequence <= len(_STAGES) else None
            if stage != expected_stage:
                raise ValueError(f"expected next stage {expected_stage!r}, got {stage!r}")
            if stage == RunStage.INTEGRATE.value:
                allowed, reason = allow_integration(changed, human_approved)
                if not allowed:
                    raise ValueError(reason)
            payload: dict[str, Any] = {
                "schema_version": 1,
                "id": snapshot_id,
                "run_id": run_id,
                "task_id": str(run["task_id"]),
                "source_commit": str(run["source_commit"]),
                "runtime_version": str(run["runtime_version"]),
                "sequence": sequence,
                "stage": stage,
                "summary": summary,
                "changed_files": changed,
                "human_approved": human_approved,
                "artifacts": artifact_values,
                "evidence": evidence_values,
                "previous_digest": None if previous is None else str(previous["digest"]),
            }
            digest = _digest(payload)
            created_at = time.time()
            con.execute(
                "INSERT INTO run_snapshots (id, run_id, sequence, stage, payload, digest, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (snapshot_id, run_id, sequence, stage, _canonical(payload), digest, created_at),
            )
            con.executemany(
                "INSERT INTO run_artifacts (snapshot_id, id, path, kind, sha256) VALUES (?, ?, ?, ?, ?)",
                [
                    (snapshot_id, item["id"], item["path"], item["kind"], item["sha256"])
                    for item in artifact_values
                ],
            )
            con.executemany(
                "INSERT INTO run_evidence (snapshot_id, id, ref, sha256) VALUES (?, ?, ?, ?)",
                [
                    (snapshot_id, item["id"], item["ref"], item["sha256"])
                    for item in evidence_values
                ],
            )
        snapshots = self.query(run_id)["snapshots"]
        assert isinstance(snapshots, list) and snapshots
        return cast(dict[str, Any], snapshots[-1])

    def query(self, run_id: str) -> dict[str, Any]:
        with connect(self.database) as con:
            run = con.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if run is None:
                raise KeyError(run_id)
            snapshots = con.execute(
                "SELECT * FROM run_snapshots WHERE run_id=? ORDER BY sequence", (run_id,)
            ).fetchall()
        return {
            "id": str(run["id"]),
            "task_id": str(run["task_id"]),
            "source_commit": str(run["source_commit"]),
            "runtime_version": str(run["runtime_version"]),
            "snapshots": [
                {**json.loads(str(snapshot["payload"])), "digest": str(snapshot["digest"])}
                for snapshot in snapshots
            ],
        }

    def verify(self, run_id: str) -> dict[str, Any]:
        run = self.query(run_id)
        previous_digest: str | None = None
        for expected_sequence, snapshot in enumerate(run["snapshots"], start=1):
            payload = {key: value for key, value in snapshot.items() if key != "digest"}
            if (
                payload["sequence"] != expected_sequence
                or payload["stage"] != _STAGES[expected_sequence - 1]
            ):
                return {"valid": False, "run_id": run_id, "reason": "invalid stage sequence"}
            if (
                payload["previous_digest"] != previous_digest
                or _digest(payload) != snapshot["digest"]
            ):
                return {"valid": False, "run_id": run_id, "reason": "invalid snapshot digest chain"}
            with connect(self.database) as con:
                artifacts = [
                    dict(row)
                    for row in con.execute(
                        "SELECT id, path, kind, sha256 FROM run_artifacts "
                        "WHERE snapshot_id=? ORDER BY id",
                        (snapshot["id"],),
                    )
                ]
                evidence = [
                    dict(row)
                    for row in con.execute(
                        "SELECT id, ref, sha256 FROM run_evidence WHERE snapshot_id=? ORDER BY id",
                        (snapshot["id"],),
                    )
                ]
            if artifacts != sorted(payload["artifacts"], key=lambda item: item["id"]):
                return {"valid": False, "run_id": run_id, "reason": "invalid artifact references"}
            if evidence != sorted(payload["evidence"], key=lambda item: item["id"]):
                return {"valid": False, "run_id": run_id, "reason": "invalid evidence references"}
            previous_digest = str(snapshot["digest"])
        return {"valid": True, "run_id": run_id, "snapshots": len(run["snapshots"])}

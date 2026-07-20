import sqlite3
from pathlib import Path

import pytest

from quattroagents.control_plane.leases import Leases
from quattroagents.control_plane.runs import RunStore
from quattroagents.control_plane.tasks import ControlPlane

_DIGEST = "a" * 64


def _snapshot_inputs() -> dict[str, object]:
    return {
        "artifacts": [
            {
                "id": "artifact-1",
                "path": "docs/self-hosting.md",
                "kind": "document",
                "sha256": _DIGEST,
            }
        ],
        "evidence": [{"id": "evidence-1", "ref": "pytest://selfhost", "sha256": _DIGEST}],
    }


def test_atomic_claim_and_lease(tmp_path: Path) -> None:
    database = tmp_path / "state.sqlite3"
    tasks = ControlPlane(database)
    leases = Leases(str(database))
    tasks.create("TASK-001", {"objective": "x"})
    assert tasks.claim("TASK-001", "a")
    assert not tasks.claim("TASK-001", "b")
    assert leases.acquire("src/a.py", "TASK-001", "a")
    assert not leases.acquire("src", "TASK-002", "b")
    assert leases.release("src/a.py", "a")


def test_tasks_persist_and_filter_by_milestone(tmp_path: Path) -> None:
    tasks = ControlPlane(tmp_path / "state.sqlite3")
    from_contract = tasks.create("TASK-001", {"milestone": "0.2.0"})
    from_argument = tasks.create("TASK-002", {}, "0.3.0")

    assert from_contract["milestone"] == "0.2.0"
    assert from_argument["milestone"] == "0.3.0"
    assert [task["id"] for task in tasks.query(milestone="0.2.0")] == ["TASK-001"]
    with pytest.raises(ValueError, match="must match"):
        tasks.create("TASK-003", {"milestone": "0.2.0"}, "0.3.0")


def test_legacy_task_database_is_migrated_without_data_loss(tmp_path: Path) -> None:
    database = tmp_path / "state.sqlite3"
    with sqlite3.connect(database) as con:
        con.execute(
            "CREATE TABLE tasks (id TEXT PRIMARY KEY, payload TEXT NOT NULL, status TEXT NOT NULL, "
            "claimant TEXT, updated_at REAL NOT NULL)"
        )
        con.execute(
            "INSERT INTO tasks VALUES "
            "('TASK-LEGACY', '{\"milestone\": \"0.2.0\"}', 'completed', 'codex', 0)"
        )

    task = ControlPlane(database).query("TASK-LEGACY")

    assert task["id"] == "TASK-LEGACY"
    assert task["milestone"] == "0.2.0"


def test_run_snapshots_follow_lifecycle_verify_digest_and_are_immutable(tmp_path: Path) -> None:
    database = tmp_path / "state.sqlite3"
    ControlPlane(database).create("SELFHOST-001", {"objective": "self-hosting"}, "0.3.0")
    runs = RunStore(database)
    runs.create("run-001", "SELFHOST-001", "ff89051", "0.3.0")
    inputs = _snapshot_inputs()

    with pytest.raises(ValueError, match="expected next stage 'plan'"):
        runs.append_snapshot(
            "run-001", "snapshot-0", "execute", "wrong order", **inputs, changed_files=[]
        )

    for sequence, stage in enumerate(("plan", "execute", "review"), start=1):
        snapshot = runs.append_snapshot(
            "run-001",
            f"snapshot-{sequence}",
            stage,
            f"{stage} summary",
            **inputs,
            changed_files=[],
        )
        assert snapshot["sequence"] == sequence
        assert snapshot["stage"] == stage

    with pytest.raises(ValueError, match="explicit human approval"):
        runs.append_snapshot(
            "run-001",
            "snapshot-4",
            "integrate",
            "protected integration",
            **inputs,
            changed_files=["src/quattroagents/control_plane/database.py"],
        )

    integrated = runs.append_snapshot(
        "run-001",
        "snapshot-4",
        "integrate",
        "approved protected integration",
        **inputs,
        changed_files=["src/quattroagents/control_plane/database.py"],
        human_approved=True,
    )
    assert integrated["previous_digest"]
    assert runs.verify("run-001") == {"valid": True, "run_id": "run-001", "snapshots": 4}

    with sqlite3.connect(database) as con:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            con.execute("UPDATE run_snapshots SET digest='tampered' WHERE id='snapshot-1'")
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            con.execute("DELETE FROM run_artifacts WHERE snapshot_id='snapshot-1'")


def test_run_snapshot_migration_preserves_legacy_task_data(tmp_path: Path) -> None:
    database = tmp_path / "state.sqlite3"
    with sqlite3.connect(database) as con:
        con.execute(
            "CREATE TABLE tasks (id TEXT PRIMARY KEY, payload TEXT NOT NULL, status TEXT NOT NULL, "
            "claimant TEXT, updated_at REAL NOT NULL)"
        )
        con.execute(
            "INSERT INTO tasks VALUES "
            "('TASK-LEGACY', '{\"milestone\": \"0.2.0\"}', 'completed', 'codex', 0)"
        )

    runs = RunStore(database)
    runs.create("run-legacy", "TASK-LEGACY", "ff89051", "0.3.0")

    task = ControlPlane(database).query("TASK-LEGACY")
    assert task["payload"] == {"milestone": "0.2.0"}
    assert task["milestone"] == "0.2.0"
    assert runs.query("run-legacy")["snapshots"] == []

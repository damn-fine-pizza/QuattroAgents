import sqlite3
from pathlib import Path

import pytest

from quattroagents.control_plane.leases import Leases
from quattroagents.control_plane.tasks import ControlPlane


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

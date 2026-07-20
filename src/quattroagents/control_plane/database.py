from __future__ import annotations

import json
import sqlite3
from pathlib import Path


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=5, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript("""
    CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, payload TEXT NOT NULL, milestone TEXT, status TEXT NOT NULL, claimant TEXT, updated_at REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS leases (path TEXT PRIMARY KEY, task_id TEXT NOT NULL, agent TEXT NOT NULL, expires_at REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS artifacts (id TEXT PRIMARY KEY, task_id TEXT NOT NULL, path TEXT NOT NULL, kind TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS decisions (id TEXT PRIMARY KEY, proposal TEXT NOT NULL, status TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS runs (
        id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL REFERENCES tasks(id),
        source_commit TEXT NOT NULL,
        runtime_version TEXT NOT NULL,
        created_at REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS run_snapshots (
        id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL REFERENCES runs(id),
        sequence INTEGER NOT NULL,
        stage TEXT NOT NULL CHECK(stage IN ('plan', 'execute', 'review', 'integrate')),
        payload TEXT NOT NULL,
        digest TEXT NOT NULL,
        created_at REAL NOT NULL,
        UNIQUE(run_id, sequence),
        UNIQUE(run_id, stage)
    );
    CREATE TABLE IF NOT EXISTS run_artifacts (
        snapshot_id TEXT NOT NULL REFERENCES run_snapshots(id),
        id TEXT NOT NULL,
        path TEXT NOT NULL,
        kind TEXT NOT NULL,
        sha256 TEXT NOT NULL,
        PRIMARY KEY(snapshot_id, id)
    );
    CREATE TABLE IF NOT EXISTS run_evidence (
        snapshot_id TEXT NOT NULL REFERENCES run_snapshots(id),
        id TEXT NOT NULL,
        ref TEXT NOT NULL,
        sha256 TEXT NOT NULL,
        PRIMARY KEY(snapshot_id, id)
    );
    CREATE TRIGGER IF NOT EXISTS runs_no_update
    BEFORE UPDATE ON runs BEGIN SELECT RAISE(ABORT, 'runs are immutable'); END;
    CREATE TRIGGER IF NOT EXISTS runs_no_delete
    BEFORE DELETE ON runs BEGIN SELECT RAISE(ABORT, 'runs are immutable'); END;
    CREATE TRIGGER IF NOT EXISTS run_snapshots_no_update
    BEFORE UPDATE ON run_snapshots BEGIN SELECT RAISE(ABORT, 'run snapshots are immutable'); END;
    CREATE TRIGGER IF NOT EXISTS run_snapshots_no_delete
    BEFORE DELETE ON run_snapshots BEGIN SELECT RAISE(ABORT, 'run snapshots are immutable'); END;
    CREATE TRIGGER IF NOT EXISTS run_artifacts_no_update
    BEFORE UPDATE ON run_artifacts BEGIN SELECT RAISE(ABORT, 'run artifacts are immutable'); END;
    CREATE TRIGGER IF NOT EXISTS run_artifacts_no_delete
    BEFORE DELETE ON run_artifacts BEGIN SELECT RAISE(ABORT, 'run artifacts are immutable'); END;
    CREATE TRIGGER IF NOT EXISTS run_evidence_no_update
    BEFORE UPDATE ON run_evidence BEGIN SELECT RAISE(ABORT, 'run evidence is immutable'); END;
    CREATE TRIGGER IF NOT EXISTS run_evidence_no_delete
    BEFORE DELETE ON run_evidence BEGIN SELECT RAISE(ABORT, 'run evidence is immutable'); END;
    """)
    columns = {str(row["name"]) for row in con.execute("PRAGMA table_info(tasks)")}
    if "milestone" not in columns:
        con.execute("ALTER TABLE tasks ADD COLUMN milestone TEXT")
    for row in con.execute("SELECT id, payload FROM tasks WHERE milestone IS NULL"):
        try:
            milestone = json.loads(str(row["payload"])).get("milestone")
        except json.JSONDecodeError:
            continue
        if isinstance(milestone, str) and milestone.strip():
            con.execute("UPDATE tasks SET milestone=? WHERE id=?", (milestone, row["id"]))
    return con

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

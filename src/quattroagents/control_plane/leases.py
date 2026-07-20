from __future__ import annotations

import time
from pathlib import PurePosixPath

from .database import connect


def _overlap(first: str, second: str) -> bool:
    a, b = PurePosixPath(first), PurePosixPath(second)
    return a == b or a in b.parents or b in a.parents


class Leases:
    def __init__(self, database: str) -> None:
        self.database = database

    def acquire(self, path: str, task_id: str, agent: str, ttl: int = 120) -> bool:
        now = time.time()
        with connect(__import__("pathlib").Path(self.database)) as con:
            con.execute("DELETE FROM leases WHERE expires_at < ?", (now,))
            existing = [r[0] for r in con.execute("SELECT path FROM leases").fetchall()]
            if any(_overlap(path, p) for p in existing):
                return False
            con.execute("INSERT INTO leases VALUES (?, ?, ?, ?)", (path, task_id, agent, now + ttl))
        return True

    def release(self, path: str, agent: str) -> bool:
        with connect(__import__("pathlib").Path(self.database)) as con:
            return (
                con.execute("DELETE FROM leases WHERE path=? AND agent=?", (path, agent)).rowcount
                == 1
            )

from pathlib import Path

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

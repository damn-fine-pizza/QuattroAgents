from pathlib import Path

import pytest

from quattroagents.control_plane.decisions import DecisionStore


def test_propose_persists_and_query_reads_it_back(tmp_path: Path) -> None:
    store = DecisionStore(tmp_path / "state.sqlite3")

    proposed = store.propose(
        "DEC-001",
        "tooling",
        "Adopt codebase-memory-mcp",
        {"tool": "codebase-memory-mcp"},
        "agent-a",
    )

    assert proposed["id"] == "DEC-001"
    assert proposed["status"] == "proposed"
    assert proposed["payload"] == {"tool": "codebase-memory-mcp"}

    queried = store.query("DEC-001")
    assert queried == proposed


def test_resolve_updates_status_and_records_rationale(tmp_path: Path) -> None:
    store = DecisionStore(tmp_path / "state.sqlite3")
    store.propose("DEC-001", "tooling", "Adopt rtk", {}, "agent-a")

    resolved = store.resolve("DEC-001", "accepted", decided_by="human", rationale="Saves tokens.")

    assert resolved["status"] == "accepted"
    assert resolved["decided_by"] == "human"
    assert resolved["rationale"] == "Saves tokens."
    assert resolved["decided_at"] is not None


def test_resolve_rejects_invalid_status(tmp_path: Path) -> None:
    store = DecisionStore(tmp_path / "state.sqlite3")
    store.propose("DEC-001", "tooling", "Adopt rtk", {}, "agent-a")

    with pytest.raises(ValueError, match="status must be one of"):
        store.resolve("DEC-001", "proposed")


def test_resolve_unknown_decision_raises_key_error(tmp_path: Path) -> None:
    store = DecisionStore(tmp_path / "state.sqlite3")

    with pytest.raises(KeyError):
        store.resolve("DEC-MISSING", "accepted")


def test_query_filters_by_status(tmp_path: Path) -> None:
    store = DecisionStore(tmp_path / "state.sqlite3")
    store.propose("DEC-001", "tooling", "Adopt rtk", {}, "agent-a")
    store.propose("DEC-002", "tooling", "Adopt codebase-memory-mcp", {}, "agent-a")
    store.resolve("DEC-002", "accepted")

    assert [d["id"] for d in store.query(status="proposed")] == ["DEC-001"]
    assert [d["id"] for d in store.query(status="accepted")] == ["DEC-002"]

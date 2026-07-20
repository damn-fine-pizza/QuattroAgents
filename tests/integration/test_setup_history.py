from pathlib import Path

from quattroagents.core.setup_history import SetupHistoryStore


def test_latest_and_recent_return_none_or_empty_without_prior_runs(tmp_path: Path) -> None:
    store = SetupHistoryStore()

    assert store.latest(tmp_path) is None
    assert store.recent(tmp_path) == []


def test_append_persists_a_record_that_recent_and_latest_can_read_back(tmp_path: Path) -> None:
    store = SetupHistoryStore()
    analysis = {"languages": ["python"]}
    interview = {"schema_version": 1, "status": "default", "answers": {}, "analysis": {}}
    manifest = {"schema_version": 1, "roles": [], "skills": []}

    record = store.append(tmp_path, analysis, interview, manifest)

    assert record["analysis"] == analysis
    assert record["interview"] == interview
    assert record["manifest"] == manifest
    assert record["previous_record"] is None

    latest = store.latest(tmp_path)
    assert latest is not None
    assert latest["manifest"] == manifest

    on_disk = list((tmp_path / ".quattroagents" / "decisions" / "setup").glob("*.json"))
    assert len(on_disk) == 1


def test_previous_record_links_to_the_prior_entry(tmp_path: Path) -> None:
    store = SetupHistoryStore()
    interview = {"schema_version": 1, "status": "default", "answers": {}, "analysis": {}}

    first = store.append(tmp_path, {"languages": []}, interview, {"schema_version": 1})
    second = store.append(tmp_path, {"languages": ["python"]}, interview, {"schema_version": 1})

    assert second["previous_record"] == f"setup/{first['_filename']}"

    recent = store.recent(tmp_path)
    assert len(recent) == 2
    assert recent[0]["analysis"] == {"languages": ["python"]}
    assert recent[1]["analysis"] == {"languages": []}


def test_recent_respects_limit(tmp_path: Path) -> None:
    store = SetupHistoryStore()
    interview = {"schema_version": 1, "status": "default", "answers": {}, "analysis": {}}
    for _ in range(3):
        store.append(tmp_path, {"languages": []}, interview, {"schema_version": 1})

    assert len(store.recent(tmp_path, limit=2)) == 2

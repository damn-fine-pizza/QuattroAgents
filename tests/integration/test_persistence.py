"""Tests for local, file-based persistence (AgentFactoryStore, GeneratedFileGuard, etc.)."""

from pathlib import Path

import pytest

from quattroagents.domain import (
    Decision,
    DecisionScope,
    DecisionSource,
    DecisionSourceType,
    DecisionStatus,
    InterviewSession,
    ProjectProfile,
    SessionType,
)
from quattroagents.persistence import (
    AgentFactoryStore,
    GeneratedFileGuard,
    read_json,
    safe_path,
    write_json,
)

# --------------------------------------------------------------------------
# Fixtures: minimal valid domain objects
# --------------------------------------------------------------------------


@pytest.fixture
def minimal_profile() -> ProjectProfile:
    """Minimal valid ProjectProfile with only required fields."""
    return ProjectProfile(fingerprint="test-fingerprint-123")


@pytest.fixture
def minimal_decision() -> Decision:
    """Minimal valid Decision with only required fields."""
    return Decision(
        id="decision-001",
        title="Test Decision",
        value={"key": "value"},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="For testing",
    )


@pytest.fixture
def minimal_session() -> InterviewSession:
    """Minimal valid InterviewSession with only required fields."""
    return InterviewSession(
        id="session-001",
        type=SessionType.INITIAL_SETUP,
        project_fingerprint="test-fp",
        started_at="2024-01-01T00:00:00Z",
    )


# --------------------------------------------------------------------------
# Tests: write_json / read_json round-trip
# --------------------------------------------------------------------------


def test_write_json_creates_file_with_valid_json(tmp_path: Path) -> None:
    """write_json creates a valid JSON file with indentation and trailing newline."""
    path = tmp_path / "test.json"
    data = {"name": "test", "items": [1, 2, 3]}

    write_json(path, data)

    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert content.endswith("\n")
    assert "name" in content
    assert "test" in content


def test_write_json_creates_parent_directories(tmp_path: Path) -> None:
    """write_json creates parent directories if they don't exist."""
    path = tmp_path / "a" / "b" / "c" / "test.json"

    write_json(path, {"key": "value"})

    assert path.exists()
    assert path.parent == tmp_path / "a" / "b" / "c"


def test_read_json_returns_default_when_file_missing(tmp_path: Path) -> None:
    """read_json returns the default value when file doesn't exist."""
    path = tmp_path / "missing.json"
    default = {"fallback": True}

    result = read_json(path, default)

    assert result == default


def test_read_json_parses_existing_file(tmp_path: Path) -> None:
    """read_json reads and parses an existing JSON file."""
    path = tmp_path / "data.json"
    data = {"name": "test", "count": 42}
    write_json(path, data)

    result = read_json(path, {})

    assert result == data


def test_write_and_read_json_round_trip(tmp_path: Path) -> None:
    """write_json and read_json preserve data through round-trip."""
    path = tmp_path / "roundtrip.json"
    original = {"nested": {"key": "value"}, "list": [1, 2, 3], "null_field": None}

    write_json(path, original)
    read_back = read_json(path, {})

    assert read_back == original


# --------------------------------------------------------------------------
# Tests: safe_path
# --------------------------------------------------------------------------


def test_safe_path_allows_file_inside_root(tmp_path: Path) -> None:
    """safe_path allows a path inside the root directory."""
    root = tmp_path / "project"
    candidate = root / "src" / "module.py"

    result = safe_path(root, candidate)

    assert result == candidate.resolve()


def test_safe_path_allows_root_itself(tmp_path: Path) -> None:
    """safe_path allows the root path itself."""
    root = tmp_path / "project"
    root.mkdir()

    result = safe_path(root, root)

    assert result == root.resolve()


def test_safe_path_rejects_path_escaping_root(tmp_path: Path) -> None:
    """safe_path raises ValueError when path tries to escape root."""
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside.txt"

    with pytest.raises(ValueError, match="path escapes project root"):
        safe_path(root, outside)


def test_safe_path_rejects_parent_directory_escape(tmp_path: Path) -> None:
    """safe_path rejects path with .. that escapes root."""
    root = tmp_path / "project"
    root.mkdir()
    candidate = root / ".." / "outside"

    with pytest.raises(ValueError, match="path escapes project root"):
        safe_path(root, candidate)


# --------------------------------------------------------------------------
# Tests: GeneratedFileGuard.write()
# --------------------------------------------------------------------------


def test_guard_write_creates_file_on_first_write(tmp_path: Path) -> None:
    """First write on a fresh file returns status='written'."""
    guard = GeneratedFileGuard(tmp_path)
    target = tmp_path / "output.py"
    content = "print('hello')\n"

    result = guard.write("output.py", content)

    assert result.status == "written"
    assert result.relative_path == "output.py"
    assert target.exists()
    assert target.read_text(encoding="utf-8") == content


def test_guard_write_same_content_twice_returns_written(tmp_path: Path) -> None:
    """Writing identical content a second time also returns status='written'."""
    guard = GeneratedFileGuard(tmp_path)
    content = "print('hello')\n"

    result1 = guard.write("output.py", content)
    result2 = guard.write("output.py", content)

    assert result1.status == "written"
    assert result2.status == "written"


def test_guard_write_safe_regenerate_when_unchanged_on_disk(tmp_path: Path) -> None:
    """Regenerating different content when on-disk matches last generation returns 'written'."""
    guard = GeneratedFileGuard(tmp_path)
    target = tmp_path / "output.py"
    content1 = "print('v1')\n"
    content2 = "print('v2')\n"

    result1 = guard.write("output.py", content1)
    assert result1.status == "written"

    result2 = guard.write("output.py", content2)

    assert result2.status == "written"
    assert target.read_text(encoding="utf-8") == content2


def test_guard_write_conflict_when_manually_edited(tmp_path: Path) -> None:
    """Manual edit between writes with different content returns status='conflict'."""
    guard = GeneratedFileGuard(tmp_path)
    target = tmp_path / "output.py"
    content1 = "print('v1')\n"
    content2_generated = "print('v2')\n"
    content_manual = "print('manual edit')\n"

    result1 = guard.write("output.py", content1)
    assert result1.status == "written"

    target.write_text(content_manual, encoding="utf-8")

    result2 = guard.write("output.py", content2_generated)

    assert result2.status == "conflict"
    assert result2.previous_content == content_manual
    assert result2.attempted_content == content2_generated
    assert target.read_text(encoding="utf-8") == content_manual


def test_guard_write_unchanged_after_manual_edit_with_matching_content(tmp_path: Path) -> None:
    """Manual edit that matches what we try to write returns 'unchanged'."""
    guard = GeneratedFileGuard(tmp_path)
    target = tmp_path / "output.py"
    content_v1 = "print('v1')\n"
    content_v2 = "print('v2')\n"

    guard.write("output.py", content_v1)

    target.write_text(content_v2, encoding="utf-8")

    result = guard.write("output.py", content_v2)

    assert result.status == "unchanged"


# --------------------------------------------------------------------------
# Tests: AgentFactoryStore profile save/load
# --------------------------------------------------------------------------


def test_store_load_profile_returns_none_when_nothing_saved(tmp_path: Path) -> None:
    """load_profile returns None when no profile has been saved yet."""
    store = AgentFactoryStore(tmp_path)

    result = store.load_profile()

    assert result is None


def test_store_save_load_profile_round_trip(
    tmp_path: Path, minimal_profile: ProjectProfile
) -> None:
    """save_profile and load_profile preserve data through round-trip."""
    store = AgentFactoryStore(tmp_path)

    store.save_profile(minimal_profile)
    loaded = store.load_profile()

    assert loaded is not None
    assert loaded.fingerprint == minimal_profile.fingerprint


def test_store_save_profile_creates_snapshot_in_history(
    tmp_path: Path, minimal_profile: ProjectProfile
) -> None:
    """save_profile writes a timestamped snapshot under history/."""
    store = AgentFactoryStore(tmp_path)

    store.save_profile(minimal_profile)

    history_dir = store.base / "history"
    assert history_dir.exists()
    snapshots = list(history_dir.glob("*-analysis.json"))
    assert len(snapshots) >= 1


def test_store_profile_history_returns_empty_when_none_saved(tmp_path: Path) -> None:
    """profile_history returns empty list when no snapshots exist."""
    store = AgentFactoryStore(tmp_path)

    result = store.profile_history()

    assert result == []


def test_store_profile_history_returns_profiles(
    tmp_path: Path, minimal_profile: ProjectProfile
) -> None:
    """profile_history returns saved ProfileProject instances."""
    store = AgentFactoryStore(tmp_path)

    store.save_profile(minimal_profile)
    history = store.profile_history()

    assert len(history) >= 1
    assert history[0].fingerprint == minimal_profile.fingerprint


def test_store_profile_history_respects_limit(tmp_path: Path) -> None:
    """profile_history respects the limit argument."""
    store = AgentFactoryStore(tmp_path)

    for i in range(5):
        profile = ProjectProfile(fingerprint=f"fp-{i}")
        store.save_profile(profile)

    limited = store.profile_history(limit=2)

    assert len(limited) == 2


# --------------------------------------------------------------------------
# Tests: AgentFactoryStore decision save/load
# --------------------------------------------------------------------------


def test_store_load_decision_returns_none_when_unknown(tmp_path: Path) -> None:
    """load_decision returns None for an unknown decision id."""
    store = AgentFactoryStore(tmp_path)

    result = store.load_decision("unknown-id")

    assert result is None


def test_store_save_load_decision_round_trip(tmp_path: Path, minimal_decision: Decision) -> None:
    """save_decision and load_decision preserve data through round-trip."""
    store = AgentFactoryStore(tmp_path)

    store.save_decision(minimal_decision)
    loaded = store.load_decision(minimal_decision.id)

    assert loaded is not None
    assert loaded.id == minimal_decision.id
    assert loaded.title == minimal_decision.title
    assert loaded.value == minimal_decision.value


def test_store_list_decisions_empty_when_none_saved(tmp_path: Path) -> None:
    """list_decisions returns empty list when no decisions saved."""
    store = AgentFactoryStore(tmp_path)

    result = store.list_decisions()

    assert result == []


def test_store_list_decisions_returns_all_decisions(tmp_path: Path) -> None:
    """list_decisions returns all saved decisions."""
    store = AgentFactoryStore(tmp_path)
    decision1 = Decision(
        id="d1",
        title="Decision 1",
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Test 1",
    )
    decision2 = Decision(
        id="d2",
        title="Decision 2",
        value={},
        source=DecisionSource(type=DecisionSourceType.INFERRED),
        reason="Test 2",
    )

    store.save_decision(decision1)
    store.save_decision(decision2)
    decisions = store.list_decisions()

    assert len(decisions) == 2
    assert any(d.id == "d1" for d in decisions)
    assert any(d.id == "d2" for d in decisions)


def test_store_list_decisions_filters_by_status(tmp_path: Path) -> None:
    """list_decisions filters correctly by status."""
    store = AgentFactoryStore(tmp_path)
    active_decision = Decision(
        id="active",
        title="Active",
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Active",
        status=DecisionStatus.ACTIVE,
    )
    uncertain_decision = Decision(
        id="uncertain",
        title="Uncertain",
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Uncertain",
        status=DecisionStatus.UNCERTAIN,
    )

    store.save_decision(active_decision)
    store.save_decision(uncertain_decision)

    active = store.list_decisions(status=DecisionStatus.ACTIVE)
    uncertain = store.list_decisions(status=DecisionStatus.UNCERTAIN)

    assert len(active) == 1
    assert active[0].id == "active"
    assert len(uncertain) == 1
    assert uncertain[0].id == "uncertain"


def test_store_list_decisions_filters_by_decision_scope(tmp_path: Path) -> None:
    """list_decisions filters correctly by decision_scope."""
    store = AgentFactoryStore(tmp_path)
    project_wide = Decision(
        id="pw",
        title="Project Wide",
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Project wide",
        decision_scope=DecisionScope.PROJECT_WIDE,
    )
    task_local = Decision(
        id="tl",
        title="Task Local",
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Task local",
        decision_scope=DecisionScope.TASK_LOCAL,
    )

    store.save_decision(project_wide)
    store.save_decision(task_local)

    pw = store.list_decisions(decision_scope=DecisionScope.PROJECT_WIDE)
    tl = store.list_decisions(decision_scope=DecisionScope.TASK_LOCAL)

    assert len(pw) == 1
    assert pw[0].id == "pw"
    assert len(tl) == 1
    assert tl[0].id == "tl"


# --------------------------------------------------------------------------
# Tests: AgentFactoryStore supersede_decision
# --------------------------------------------------------------------------


def test_store_supersede_decision_updates_status(tmp_path: Path) -> None:
    """supersede_decision sets old decision status to SUPERSEDED."""
    store = AgentFactoryStore(tmp_path)
    old_decision = Decision(
        id="old",
        title="Old",
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Old",
        status=DecisionStatus.ACTIVE,
    )
    new_decision = Decision(
        id="new",
        title="New",
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="New",
    )

    store.save_decision(old_decision)
    store.supersede_decision("old", new_decision)

    old_loaded = store.load_decision("old")
    assert old_loaded is not None
    assert old_loaded.status == DecisionStatus.SUPERSEDED


def test_store_supersede_decision_links_decisions(tmp_path: Path) -> None:
    """supersede_decision sets superseded_by and supersedes links."""
    store = AgentFactoryStore(tmp_path)
    old_decision = Decision(
        id="old",
        title="Old",
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Old",
    )
    new_decision = Decision(
        id="new",
        title="New",
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="New",
    )

    store.save_decision(old_decision)
    store.supersede_decision("old", new_decision)

    old_loaded = store.load_decision("old")
    new_loaded = store.load_decision("new")

    assert old_loaded is not None
    assert old_loaded.superseded_by == "new"
    assert new_loaded is not None
    assert new_loaded.supersedes == "old"


def test_store_supersede_decision_raises_for_unknown_old(tmp_path: Path) -> None:
    """supersede_decision raises KeyError for unknown old decision."""
    store = AgentFactoryStore(tmp_path)
    new_decision = Decision(
        id="new",
        title="New",
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="New",
    )

    with pytest.raises(KeyError, match="unknown decision"):
        store.supersede_decision("unknown", new_decision)


# --------------------------------------------------------------------------
# Tests: AgentFactoryStore reopen_decision
# --------------------------------------------------------------------------


def test_store_reopen_decision_sets_status_to_uncertain(tmp_path: Path) -> None:
    """reopen_decision sets status to UNCERTAIN."""
    store = AgentFactoryStore(tmp_path)
    decision = Decision(
        id="d1",
        title="Test",
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Original reason",
        status=DecisionStatus.ACTIVE,
    )

    store.save_decision(decision)
    reopened = store.reopen_decision("d1", "Reopen reason")

    assert reopened.status == DecisionStatus.UNCERTAIN


def test_store_reopen_decision_updates_reason(tmp_path: Path) -> None:
    """reopen_decision updates the reason field."""
    store = AgentFactoryStore(tmp_path)
    decision = Decision(
        id="d1",
        title="Test",
        value={},
        source=DecisionSource(type=DecisionSourceType.USER),
        reason="Original",
    )

    store.save_decision(decision)
    reopened = store.reopen_decision("d1", "New reason")

    assert reopened.reason == "New reason"


def test_store_reopen_decision_raises_for_unknown(tmp_path: Path) -> None:
    """reopen_decision raises KeyError for unknown decision."""
    store = AgentFactoryStore(tmp_path)

    with pytest.raises(KeyError, match="unknown decision"):
        store.reopen_decision("unknown", "Reason")


# --------------------------------------------------------------------------
# Tests: AgentFactoryStore session save/load
# --------------------------------------------------------------------------


def test_store_load_session_returns_none_when_unknown(tmp_path: Path) -> None:
    """load_session returns None for unknown session id."""
    store = AgentFactoryStore(tmp_path)

    result = store.load_session("unknown")

    assert result is None


def test_store_save_load_session_round_trip(
    tmp_path: Path, minimal_session: InterviewSession
) -> None:
    """save_session and load_session preserve data through round-trip."""
    store = AgentFactoryStore(tmp_path)

    store.save_session(minimal_session)
    loaded = store.load_session(minimal_session.id)

    assert loaded is not None
    assert loaded.id == minimal_session.id
    assert loaded.type == minimal_session.type
    assert loaded.project_fingerprint == minimal_session.project_fingerprint


def test_store_list_sessions_empty_when_none_saved(tmp_path: Path) -> None:
    """list_sessions returns empty list when no sessions saved."""
    store = AgentFactoryStore(tmp_path)

    result = store.list_sessions()

    assert result == []


def test_store_list_sessions_returns_newest_first(tmp_path: Path) -> None:
    """list_sessions returns sessions sorted newest-first."""
    store = AgentFactoryStore(tmp_path)
    session1 = InterviewSession(
        id="s1",
        type=SessionType.INITIAL_SETUP,
        project_fingerprint="fp",
        started_at="2024-01-01T00:00:00Z",
    )
    session2 = InterviewSession(
        id="s2",
        type=SessionType.TASK_PREPARATION,
        project_fingerprint="fp",
        started_at="2024-01-02T00:00:00Z",
    )

    store.save_session(session1)
    store.save_session(session2)
    sessions = store.list_sessions()

    assert len(sessions) == 2
    assert sessions[0].id == "s2"
    assert sessions[1].id == "s1"


def test_store_list_sessions_respects_limit(tmp_path: Path) -> None:
    """list_sessions respects the limit argument."""
    store = AgentFactoryStore(tmp_path)

    for i in range(5):
        session = InterviewSession(
            id=f"s{i}",
            type=SessionType.INITIAL_SETUP,
            project_fingerprint="fp",
            started_at=f"2024-01-{i + 1:02d}T00:00:00Z",
        )
        store.save_session(session)

    limited = store.list_sessions(limit=2)

    assert len(limited) == 2


def test_store_latest_session_returns_none_when_empty(tmp_path: Path) -> None:
    """latest_session returns None when no sessions exist."""
    store = AgentFactoryStore(tmp_path)

    result = store.latest_session()

    assert result is None


def test_store_latest_session_returns_most_recent(tmp_path: Path) -> None:
    """latest_session returns the most recent session."""
    store = AgentFactoryStore(tmp_path)
    session1 = InterviewSession(
        id="s1",
        type=SessionType.INITIAL_SETUP,
        project_fingerprint="fp",
        started_at="2024-01-01T00:00:00Z",
    )
    session2 = InterviewSession(
        id="s2",
        type=SessionType.TASK_PREPARATION,
        project_fingerprint="fp",
        started_at="2024-01-02T00:00:00Z",
    )

    store.save_session(session1)
    store.save_session(session2)
    latest = store.latest_session()

    assert latest is not None
    assert latest.id == "s2"


# --------------------------------------------------------------------------
# Tests: AgentFactoryStore generated manifest
# --------------------------------------------------------------------------


def test_store_load_manifest_returns_none_when_nothing_saved(tmp_path: Path) -> None:
    """load_generated_manifest returns None when nothing saved yet."""
    store = AgentFactoryStore(tmp_path)

    result = store.load_generated_manifest()

    assert result is None


def test_store_save_load_manifest_round_trip(tmp_path: Path) -> None:
    """save_generated_manifest and load_generated_manifest preserve data."""
    store = AgentFactoryStore(tmp_path)
    manifest = {
        "agents": ["agent-1", "agent-2"],
        "skills": ["skill-1"],
        "swarm": {"phases": []},
    }

    store.save_generated_manifest(manifest)
    loaded = store.load_generated_manifest()

    assert loaded == manifest

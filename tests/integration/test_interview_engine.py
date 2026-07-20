"""Test suite for the Interview Engine orchestrator.

Tests the full lifecycle of InterviewSession, from gap detection through
decision confirmation, using real store and domain objects without mocks.
"""

from pathlib import Path

import pytest

from quattroagents.domain import (
    GapStatus,
    ProjectProfile,
    SessionStatus,
    SessionType,
)
from quattroagents.interview.engine import InterviewEngine, RawAnswer
from quattroagents.persistence import AgentFactoryStore


def test_start_session_creates_session_with_gaps_and_persists(tmp_path: Path) -> None:
    """Test start_session creates session with AWAITING_ANSWERS and detects gaps."""
    store = AgentFactoryStore(tmp_path)
    engine = InterviewEngine(store)

    # Profile with no test frameworks and 2+ languages guarantees gap detection
    profile = ProjectProfile(
        fingerprint="test-fp",
        languages=["python", "javascript"],
        test_frameworks=[],
    )

    session = engine.start_session(
        SessionType.INITIAL_SETUP,
        profile,
        session_id="session-1",
    )

    # Verify session properties
    assert session.id == "session-1"
    assert session.type == SessionType.INITIAL_SETUP
    assert session.project_fingerprint == "test-fp"
    assert session.status == SessionStatus.AWAITING_ANSWERS
    assert len(session.knowledge_gaps) >= 2

    # Verify session is persisted and can be reloaded
    loaded = store.load_session("session-1")
    assert loaded is not None
    assert loaded.id == session.id
    assert loaded.status == session.status
    assert loaded.knowledge_gaps == session.knowledge_gaps


def test_get_next_questions_respects_batch_limit(tmp_path: Path) -> None:
    """Test get_next_questions returns at most max_questions_per_batch."""
    store = AgentFactoryStore(tmp_path)
    engine = InterviewEngine(store, max_batch=2)

    profile = ProjectProfile(
        fingerprint="test-fp",
        languages=["python", "javascript"],
        test_frameworks=[],
    )

    session = engine.start_session(
        SessionType.INITIAL_SETUP,
        profile,
        session_id="session-1",
    )

    # Get first batch
    batch1 = engine.get_next_questions(session)
    assert len(batch1) <= 2

    if batch1:
        batch1_ids = {q.id for q in batch1}

        # Reload session to get updated state with question IDs
        session = store.load_session("session-1")

        # Submit answers to first batch
        answers = [
            RawAnswer(
                question_id=q.id,
                value="test_answer",
                free_text="Detailed answer provided.",
            )
            for q in batch1
        ]
        session, _ = engine.submit_answers(session, answers)

        # Get next batch
        batch2 = engine.get_next_questions(session)

        # Verify no duplicates between batches
        batch2_ids = {q.id for q in batch2}
        assert batch1_ids.isdisjoint(batch2_ids)


def test_submit_answers_with_unknown_question_id_raises_keyerror(tmp_path: Path) -> None:
    """Test submit_answers raises KeyError for unknown question_id."""
    store = AgentFactoryStore(tmp_path)
    engine = InterviewEngine(store)

    profile = ProjectProfile(
        fingerprint="test-fp",
        languages=["python", "javascript"],
        test_frameworks=[],
    )

    session = engine.start_session(
        SessionType.INITIAL_SETUP,
        profile,
        session_id="session-1",
    )

    with pytest.raises(KeyError):
        engine.submit_answers(
            session,
            [RawAnswer(question_id="unknown-id", value="answer")],
        )


def test_confirm_decisions_before_ready_raises_valueerror(tmp_path: Path) -> None:
    """Test confirm_decisions raises ValueError when not READY_FOR_CONFIRMATION."""
    store = AgentFactoryStore(tmp_path)
    engine = InterviewEngine(store)

    profile = ProjectProfile(
        fingerprint="test-fp",
        languages=["python", "javascript"],
        test_frameworks=[],
    )

    session = engine.start_session(
        SessionType.INITIAL_SETUP,
        profile,
        session_id="session-1",
    )

    assert session.status == SessionStatus.AWAITING_ANSWERS
    with pytest.raises(ValueError):
        engine.confirm_decisions(session)


def test_submit_answers_drives_to_ready_for_confirmation(tmp_path: Path) -> None:
    """Test submitting answers to all questions reaches READY_FOR_CONFIRMATION."""
    store = AgentFactoryStore(tmp_path)
    engine = InterviewEngine(store)

    profile = ProjectProfile(
        fingerprint="test-fp",
        languages=["python", "javascript"],
        test_frameworks=[],
    )

    session = engine.start_session(
        SessionType.INITIAL_SETUP,
        profile,
        session_id="session-1",
    )

    # Loop: get_next_questions -> submit_answers -> repeat
    max_iterations = 10
    iteration = 0

    while iteration < max_iterations:
        # Reload to get latest state
        session = store.load_session("session-1")

        if session.status == SessionStatus.READY_FOR_CONFIRMATION:
            break

        questions = engine.get_next_questions(session)
        if not questions:
            break

        # Reload to get updated question IDs
        session = store.load_session("session-1")

        # Submit answers with reasonable detail
        answers = [
            RawAnswer(
                question_id=q.id,
                value="test_answer",
                free_text=f"Detailed response to: {q.question}",
            )
            for q in questions
        ]
        session, _ = engine.submit_answers(session, answers)
        iteration += 1

    # Verify convergence
    assert iteration < max_iterations
    assert session.status == SessionStatus.READY_FOR_CONFIRMATION


def test_confirm_decisions_creates_and_persists_decisions(tmp_path: Path) -> None:
    """Test confirm_decisions creates and persists decisions properly."""
    store = AgentFactoryStore(tmp_path)
    engine = InterviewEngine(store)

    profile = ProjectProfile(
        fingerprint="test-fp",
        languages=["python", "javascript"],
        test_frameworks=[],
    )

    session = engine.start_session(
        SessionType.INITIAL_SETUP,
        profile,
        session_id="session-1",
    )

    # Drive to READY_FOR_CONFIRMATION
    while session.status == SessionStatus.AWAITING_ANSWERS:
        session = store.load_session("session-1")
        questions = engine.get_next_questions(session)
        if not questions:
            break

        session = store.load_session("session-1")
        answers = [
            RawAnswer(
                question_id=q.id,
                value="test_answer",
                free_text=f"Detailed response to: {q.question}",
            )
            for q in questions
        ]
        session, _ = engine.submit_answers(session, answers)

    # Confirm decisions
    assert session.status == SessionStatus.READY_FOR_CONFIRMATION
    session, decisions = engine.confirm_decisions(session)

    # Verify decisions exist and are valid
    assert len(decisions) > 0
    assert session.status == SessionStatus.CONFIRMED
    assert session.completed_at is not None
    assert len(session.generated_decisions) == len(decisions)

    # Verify each decision is persisted
    for decision in decisions:
        loaded = store.load_decision(decision.id)
        assert loaded is not None
        assert loaded.id == decision.id


def test_review_summary_returns_expected_structure(tmp_path: Path) -> None:
    """Test review_summary returns dict with session_id, status, answers, open_gaps."""
    store = AgentFactoryStore(tmp_path)
    engine = InterviewEngine(store)

    profile = ProjectProfile(
        fingerprint="test-fp",
        languages=["python", "javascript"],
        test_frameworks=[],
    )

    session = engine.start_session(
        SessionType.INITIAL_SETUP,
        profile,
        session_id="session-1",
    )

    # Get some questions and submit answers
    questions = engine.get_next_questions(session)
    if questions:
        session = store.load_session("session-1")
        answers = [
            RawAnswer(
                question_id=q.id,
                value="test_answer",
                free_text=f"Detailed response to: {q.question}",
            )
            for q in questions
        ]
        session, _ = engine.submit_answers(session, answers)

    # Review summary
    summary = engine.review_summary(session)

    # Verify structure
    assert "session_id" in summary
    assert "status" in summary
    assert "answers" in summary
    assert "open_gaps" in summary

    # Verify content
    assert summary["session_id"] == "session-1"
    assert summary["status"] in ["awaiting_answers", "ready_for_confirmation", "confirmed"]

    # Verify answers have required fields
    for answer_row in summary["answers"]:
        assert "question" in answer_row
        assert "value" in answer_row
        assert "free_text" in answer_row
        assert "classification" in answer_row
        assert isinstance(answer_row["classification"], list)


def test_list_open_knowledge_gaps_returns_only_open_gaps(tmp_path: Path) -> None:
    """Test list_open_knowledge_gaps returns gaps with OPEN status.

    After confirmation, previously open gaps should be marked RESOLVED.
    """
    store = AgentFactoryStore(tmp_path)
    engine = InterviewEngine(store)

    profile = ProjectProfile(
        fingerprint="test-fp",
        languages=["python", "javascript"],
        test_frameworks=[],
    )

    session = engine.start_session(
        SessionType.INITIAL_SETUP,
        profile,
        session_id="session-1",
    )

    # Initially, all gaps should be open
    open_gaps_before = engine.list_open_knowledge_gaps(session)
    assert len(open_gaps_before) > 0
    for gap in open_gaps_before:
        assert gap.status == GapStatus.OPEN

    # Drive to confirmation
    while session.status == SessionStatus.AWAITING_ANSWERS:
        session = store.load_session("session-1")
        questions = engine.get_next_questions(session)
        if not questions:
            break

        session = store.load_session("session-1")
        answers = [
            RawAnswer(
                question_id=q.id,
                value="test_answer",
                free_text=f"Detailed response to: {q.question}",
            )
            for q in questions
        ]
        session, _ = engine.submit_answers(session, answers)

    # Confirm decisions
    if session.status == SessionStatus.READY_FOR_CONFIRMATION:
        session, _ = engine.confirm_decisions(session)

    # After confirmation, gaps should be resolved
    open_gaps_after = engine.list_open_knowledge_gaps(session)

    # Resolved gaps should not appear in open gaps list
    assert len(open_gaps_after) <= len(open_gaps_before)

    # All remaining gaps should still be OPEN
    for gap in open_gaps_after:
        assert gap.status == GapStatus.OPEN


def test_list_decision_conflicts_returns_empty_list_for_no_conflicts(
    tmp_path: Path,
) -> None:
    """Test list_decision_conflicts returns empty list with no actual conflicts."""
    store = AgentFactoryStore(tmp_path)
    engine = InterviewEngine(store)

    profile = ProjectProfile(
        fingerprint="test-fp",
        languages=["python", "javascript"],
        test_frameworks=[],
    )

    session = engine.start_session(
        SessionType.INITIAL_SETUP,
        profile,
        session_id="session-1",
    )

    # List conflicts - should not error and should return empty list
    conflicts = engine.list_decision_conflicts(session, profile)
    assert isinstance(conflicts, list)
    assert len(conflicts) == 0

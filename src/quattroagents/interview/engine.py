"""Adaptive Interview Engine orchestrator.

Ties together gap detection, question planning, answer processing, and
contradiction detection (interview/gaps.py, questions.py, answers.py,
conflicts.py) around the persisted `InterviewSession` lifecycle.

An `InterviewSession` only stores gap/question *ids* (see domain.py) — the
full `KnowledgeGap`/`Question` objects for a session are persisted alongside
it, under the same `.agent-factory/sessions/` directory, so a session can be
resumed across MCP server calls without keeping engine state in memory.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from ..domain import (
    Answer,
    ConflictRecord,
    Decision,
    DecisionStatus,
    GapStatus,
    InterviewSession,
    KnowledgeGap,
    ProjectProfile,
    Question,
    SessionStatus,
    SessionType,
)
from ..persistence import AgentFactoryStore, read_json, write_json
from .answers import answer_to_decision, classify_answer, normalize_answer
from .conflicts import detect_conflicts
from .gaps import detect_knowledge_gaps, find_stale_decisions
from .questions import (
    build_follow_up_question,
    needs_follow_up,
    plan_question_batch,
)

DEFAULT_MAX_FOLLOW_UP_DEPTH = 2


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class RawAnswer:
    question_id: str
    value: str
    free_text: str = ""
    repository_contradicts: bool = False


class InterviewEngine:
    def __init__(self, store: AgentFactoryStore, *, max_batch: int = 5):
        self.store = store
        self.max_batch = max_batch

    # -- side-storage for gaps/questions, keyed by session id -------------

    def _gaps_path(self, session_id: str) -> Any:
        return self.store.base / "sessions" / f"{session_id}-gaps.json"

    def _questions_path(self, session_id: str) -> Any:
        return self.store.base / "sessions" / f"{session_id}-questions.json"

    def _save_gaps(self, session_id: str, gaps: list[KnowledgeGap]) -> None:
        write_json(self._gaps_path(session_id), [g.to_dict() for g in gaps])

    def _load_gaps(self, session_id: str) -> list[KnowledgeGap]:
        data = read_json(self._gaps_path(session_id), [])
        return [KnowledgeGap.from_dict(d) for d in data]

    def _save_questions(self, session_id: str, questions: list[Question]) -> None:
        write_json(self._questions_path(session_id), [q.to_dict() for q in questions])

    def _load_questions(self, session_id: str) -> list[Question]:
        data = read_json(self._questions_path(session_id), [])
        return [Question.from_dict(d) for d in data]

    # -- session lifecycle --------------------------------------------------

    def start_session(
        self,
        session_type: SessionType,
        profile: ProjectProfile,
        *,
        session_id: str,
    ) -> InterviewSession:
        active_decisions = self.store.list_decisions(status=DecisionStatus.ACTIVE)
        gaps = detect_knowledge_gaps(profile, active_decisions)
        gaps += find_stale_decisions(active_decisions, profile)

        session = InterviewSession(
            id=session_id,
            type=session_type,
            project_fingerprint=profile.fingerprint,
            started_at=_utc_now(),
            status=SessionStatus.AWAITING_ANSWERS,
            knowledge_gaps=[g.id for g in gaps],
            max_questions_per_batch=self.max_batch,
        )
        self._save_gaps(session_id, gaps)
        self._save_questions(session_id, [])
        self.store.save_session(session)
        return session

    def get_next_questions(self, session: InterviewSession) -> list[Question]:
        gaps = self._load_gaps(session.id)
        already_asked = set(session.questions)
        batch = plan_question_batch(gaps, session.max_questions_per_batch, already_asked)
        if not batch:
            return []
        existing = self._load_questions(session.id)
        self._save_questions(session.id, existing + batch)
        session.questions = list(session.questions) + [q.id for q in batch]
        self.store.save_session(session)
        return batch

    def submit_answers(
        self,
        session: InterviewSession,
        raw_answers: list[RawAnswer],
        *,
        max_follow_up_depth: int = DEFAULT_MAX_FOLLOW_UP_DEPTH,
    ) -> tuple[InterviewSession, list[Question]]:
        questions_by_id = {q.id: q for q in self._load_questions(session.id)}
        new_answers: list[Answer] = []
        follow_ups: list[Question] = []

        for raw in raw_answers:
            question = questions_by_id.get(raw.question_id)
            if question is None:
                raise KeyError(f"unknown question id in this session: {raw.question_id}")
            answer = normalize_answer(question, raw.value, raw.free_text)
            answer.classification = classify_answer(question, answer)
            new_answers.append(answer)

            if needs_follow_up(question, answer, raw.repository_contradicts):
                follow_up = build_follow_up_question(question, answer, max_follow_up_depth)
                if follow_up is not None:
                    follow_ups.append(follow_up)

        session.answers = list(session.answers) + new_answers

        if follow_ups:
            existing = self._load_questions(session.id)
            self._save_questions(session.id, existing + follow_ups)
            session.questions = list(session.questions) + [q.id for q in follow_ups]

        pending_gap_ids = self._pending_gap_ids(session)
        session.status = (
            SessionStatus.AWAITING_ANSWERS
            if pending_gap_ids
            else SessionStatus.READY_FOR_CONFIRMATION
        )
        self.store.save_session(session)
        return session, follow_ups

    def _pending_gap_ids(self, session: InterviewSession) -> set[str]:
        answered_question_ids = {a.question_id for a in session.answers}
        asked_questions = self._load_questions(session.id)
        unanswered = [q for q in asked_questions if q.id not in answered_question_ids]
        return {q.gap_id for q in unanswered}

    def review_summary(self, session: InterviewSession) -> dict[str, Any]:
        questions_by_id = {q.id: q for q in self._load_questions(session.id)}
        rows = []
        for answer in session.answers:
            question = questions_by_id.get(answer.question_id)
            rows.append(
                {
                    "question": question.question if question else answer.question_id,
                    "value": answer.value,
                    "free_text": answer.free_text,
                    "classification": [c.value for c in answer.classification],
                }
            )
        return {
            "session_id": session.id,
            "status": session.status.value,
            "answers": rows,
            "open_gaps": sorted(self._pending_gap_ids(session)),
        }

    def confirm_decisions(
        self, session: InterviewSession
    ) -> tuple[InterviewSession, list[Decision]]:
        if session.status != SessionStatus.READY_FOR_CONFIRMATION:
            raise ValueError(
                f"session {session.id} is not ready for confirmation (status={session.status.value})"
            )

        gaps_by_id = {g.id: g for g in self._load_gaps(session.id)}
        questions_by_id = {q.id: q for q in self._load_questions(session.id)}
        decisions: list[Decision] = []

        for index, answer in enumerate(session.answers):
            question = questions_by_id.get(answer.question_id)
            if question is None:
                continue
            gap = gaps_by_id.get(question.gap_id)
            if gap is None:
                continue
            decision_id = f"{session.id}-decision-{index}"
            decision = answer_to_decision(question, answer, gap, session.id, decision_id)
            self.store.save_decision(decision)
            decisions.append(decision)
            gap.status = GapStatus.RESOLVED
            gap.updated_at = _utc_now()

        self._save_gaps(session.id, list(gaps_by_id.values()))
        session.generated_decisions = list(session.generated_decisions) + [d.id for d in decisions]
        session.status = SessionStatus.CONFIRMED
        session.completed_at = _utc_now()
        self.store.save_session(session)
        return session, decisions

    def list_open_knowledge_gaps(self, session: InterviewSession) -> list[KnowledgeGap]:
        return [g for g in self._load_gaps(session.id) if g.status == GapStatus.OPEN]

    def list_decision_conflicts(
        self, session: InterviewSession, profile: ProjectProfile
    ) -> list[ConflictRecord]:
        active_decisions = self.store.list_decisions(status=DecisionStatus.ACTIVE)
        return detect_conflicts(active_decisions, profile)

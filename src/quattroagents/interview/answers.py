"""Answer normalization, classification, and decision conversion for the interview engine.

Converts raw user input into normalized answers, classifies answers by type,
and generates decisions from interview responses.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from quattroagents.domain import (
    Answer,
    AnswerClassification,
    Decision,
    DecisionScope,
    DecisionSource,
    DecisionSourceType,
    DecisionStatus,
    QuestionType,
)

if TYPE_CHECKING:
    from quattroagents.domain import KnowledgeGap, Question


def normalize_answer(question: Question, raw_value: str, raw_free_text: str = "") -> Answer:
    """Normalize raw user input into a structured Answer.

    For BOOLEAN questions, normalizes true/false variants to option IDs or literals.
    For choice types with options, normalizes to canonical option IDs (case-insensitive).
    For other types, preserves stripped raw value.

    Args:
        question: The question being answered.
        raw_value: The raw value provided by the user.
        raw_free_text: Optional free-text explanation.

    Returns:
        An Answer with normalized value and metadata.
    """
    value = raw_value.strip()
    free_text = raw_free_text.strip()
    now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    if question.type == QuestionType.BOOLEAN:
        normalized = value.lower().strip()
        option_ids = {opt.id.lower(): opt.id for opt in question.options}

        if normalized in option_ids:
            value = option_ids[normalized]
        elif normalized in ("true", "yes", "y", "1"):
            if question.options:
                value = question.options[0].id
            else:
                value = "yes"
        elif normalized in ("false", "no", "n", "0"):
            if question.options:
                value = (
                    question.options[1].id if len(question.options) > 1 else question.options[0].id
                )
            else:
                value = "no"
        else:
            value = raw_value.strip()

    elif question.type in (
        QuestionType.SINGLE_CHOICE,
        QuestionType.MULTIPLE_CHOICE,
        QuestionType.TOOL_SELECTION,
        QuestionType.AGENT_SELECTION,
    ):
        if question.options:
            option_ids_map = {opt.id.lower(): opt.id for opt in question.options}
            normalized = value.lower().strip()
            if normalized in option_ids_map:
                value = option_ids_map[normalized]
            else:
                value = raw_value.strip()
        else:
            value = raw_value.strip()

    return Answer(
        question_id=question.id,
        value=value,
        free_text=free_text,
        source="user",
        confidence=1.0,
        scope=[],
        valid_from=now_iso,
        valid_until=None,
        classification=[],
    )


def classify_answer(question: Question, answer: Answer) -> list[AnswerClassification]:
    """Classify an answer by examining question gap_id and content.

    Applies multiple classification rules:
    - VALIDATION_RULE for missing-test-policy or keywords validation/criteria
    - OWNERSHIP for legacy-area-ownership or avoid modifying
    - POLICY for agent-autonomy, autonomy, or write permission
    - TOOL_POLICY for tool-policy gap_id
    - PRIORITY for multi-language-priority gap_id
    - CONSTRAINT for legacy-authority gap_id
    - PREFERENCE for simple yes/no/required/not_required values (fallback if no specific classification)
    - FACT as final fallback

    Args:
        question: The question that was answered.
        answer: The normalized answer.

    Returns:
        A deduplicated list of classifications in first-seen order.
    """
    classifications: list[AnswerClassification] = []

    gap_id_lower = question.gap_id.lower()
    question_lower = question.question.lower()

    if gap_id_lower.startswith("missing-test-policy") or (
        "validation" in question_lower or "criteri" in question_lower
    ):
        classifications.append(AnswerClassification.VALIDATION_RULE)

    if gap_id_lower.startswith("legacy-area-ownership") or ("avoid modifying" in question_lower):
        classifications.append(AnswerClassification.OWNERSHIP)

    if gap_id_lower.startswith("agent-autonomy") or (
        "autonomy" in question_lower or "write permission" in question_lower
    ):
        classifications.append(AnswerClassification.POLICY)

    if gap_id_lower.startswith("tool-policy"):
        classifications.append(AnswerClassification.TOOL_POLICY)

    if gap_id_lower.startswith("multi-language-priority"):
        classifications.append(AnswerClassification.PRIORITY)

    if gap_id_lower.startswith("legacy-authority"):
        classifications.append(AnswerClassification.CONSTRAINT)

    if not classifications and (
        answer.value in ("yes", "no", "required", "not_required", "still-valid", "obsolete")
        or answer.free_text
    ):
        classifications.append(AnswerClassification.PREFERENCE)

    if not classifications:
        classifications.append(AnswerClassification.FACT)

    seen: set[AnswerClassification] = set()
    deduped: list[AnswerClassification] = []
    for c in classifications:
        if c not in seen:
            seen.add(c)
            deduped.append(c)

    return deduped


def answer_to_decision(
    question: Question,
    answer: Answer,
    gap: KnowledgeGap,
    session_id: str,
    decision_id: str,
) -> Decision:
    """Convert an answer to a Decision record.

    Builds a Decision from the question, answer, gap context, and session info.

    Args:
        question: The question that was answered.
        answer: The normalized answer.
        gap: The knowledge gap being addressed.
        session_id: The interview session ID.
        decision_id: The ID for the new decision.

    Returns:
        A Decision record ready for storage/use.
    """
    now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    classifications = classify_answer(question, answer)

    value: dict[str, object] = {
        "question": question.question,
        "answer": answer.value,
        "detail": answer.free_text,
        "classification": [c.value for c in classifications],
    }

    reason = answer.free_text or f"User selected '{answer.value}' for: {question.question}"

    return Decision(
        id=decision_id,
        title=gap.topic,
        value=value,
        source=DecisionSource(
            type=DecisionSourceType.USER,
            interview_session=session_id,
            question_id=question.id,
        ),
        reason=reason,
        scope_paths=list(gap.evidence),
        decision_scope=DecisionScope.PROJECT_WIDE,
        confidence=answer.confidence,
        status=DecisionStatus.ACTIVE,
        effects={"agents": [], "skills": [], "validations": []},
        created_at=now_iso,
        updated_at=now_iso,
    )

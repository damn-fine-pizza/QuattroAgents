"""Interview Engine: knowledge gap to question generation, ranking, and follow-up logic.

This module transforms KnowledgeGap instances into structured Question objects,
ranks gaps by priority and impact, batches questions intelligently, and manages
adaptive follow-up chains based on answer quality and repository contradictions.
"""

from __future__ import annotations

from quattroagents.domain import (
    Answer,
    GapStatus,
    GapType,
    KnowledgeGap,
    Question,
    QuestionOption,
    QuestionType,
)


def question_for_gap(gap: KnowledgeGap) -> Question:
    """Generate a Question from a KnowledgeGap.

    Constructs the question structure, including type, options, and reasoning,
    based on the gap's type and impact profile.

    Args:
        gap: A KnowledgeGap to transform.

    Returns:
        A Question with all required fields initialized.
    """
    question_id = f"question-{gap.id}"
    impact_list = [k for k, v in gap.impact.items() if v in ("high", "medium")]
    reason = (
        f"This affects: {', '.join(impact_list)}."
        if impact_list
        else "This gap affects decision-making."
    )

    # Determine question type and options based on gap_type.
    if gap.gap_type in (
        GapType.AMBIGUOUS_ARCHITECTURE,
        GapType.CONFLICTING_EVIDENCE,
    ):
        question_type = QuestionType.FREE_TEXT
        options: list[QuestionOption] = []
        allow_free_text = True
    elif gap.gap_type == GapType.MISSING_OWNERSHIP:
        question_type = QuestionType.BOOLEAN
        options = [
            QuestionOption(
                id="yes",
                label="Yes, avoid modifying it unless explicitly instructed",
            ),
            QuestionOption(id="no", label="No, treat it like any other code"),
        ]
        allow_free_text = False
    elif gap.gap_type == GapType.MISSING_VALIDATION_RULE:
        question_type = QuestionType.BOOLEAN
        options = [
            QuestionOption(id="required", label="Yes, require tests"),
            QuestionOption(id="not_required", label="No, not required"),
        ]
        allow_free_text = True
    elif gap.gap_type == GapType.MISSING_PRIORITY:
        question_type = QuestionType.SINGLE_CHOICE
        options = []
        allow_free_text = True
    elif gap.gap_type == GapType.MISSING_TOOL_POLICY:
        question_type = QuestionType.SINGLE_CHOICE
        options = [
            QuestionOption(
                id="assume-available-later",
                label="Assume it may become available later",
            ),
            QuestionOption(id="omit", label="Omit all references to it"),
        ]
        allow_free_text = False
    elif gap.gap_type == GapType.STALE_DECISION:
        question_type = QuestionType.BOOLEAN
        options = [
            QuestionOption(id="still-valid", label="Yes, still valid"),
            QuestionOption(id="obsolete", label="No, obsolete"),
        ]
        allow_free_text = True
    else:
        # Covers: MISSING_FACT, MISSING_PREFERENCE, MISSING_CONSTRAINT, MISSING_WORKFLOW
        question_type = QuestionType.FREE_TEXT
        options = []
        allow_free_text = True

    return Question(
        id=question_id,
        gap_id=gap.id,
        question=gap.description,
        type=question_type,
        options=options,
        allow_free_text=allow_free_text,
        reason=reason,
        evidence=list(gap.evidence),
        impact=impact_list,
        follow_up_of=None,
        depth=0,
    )


def rank_gaps(gaps: list[KnowledgeGap]) -> list[KnowledgeGap]:
    """Rank knowledge gaps by priority, uncertainty, and impact.

    Computes a numeric score for each gap based on:
    - Priority weight (high=3, medium=2, low=1)
    - Uncertainty (1.0 - confidence)
    - Impact weight (sum of high/medium/low impact scores)

    Returns gaps sorted by score (descending), with ties broken by gap ID
    (ascending) for determinism.

    Args:
        gaps: List of KnowledgeGap instances to rank.

    Returns:
        Sorted list of gaps (highest score first).
    """
    priority_weights = {"high": 3, "medium": 2, "low": 1}
    impact_weights_map = {"high": 3, "medium": 2, "low": 1}

    def compute_score(gap: KnowledgeGap) -> tuple[float, str]:
        priority_weight = priority_weights[gap.priority.value]
        uncertainty = 1.0 - gap.confidence
        impact_weight = sum(impact_weights_map.get(v, 0) for v in gap.impact.values())
        score = priority_weight * (1 + uncertainty) * (1 + impact_weight)
        return (score, gap.id)

    sorted_gaps = sorted(gaps, key=compute_score, reverse=True)
    return sorted_gaps


def plan_question_batch(
    gaps: list[KnowledgeGap],
    max_batch: int,
    already_asked_question_ids: set[str],
) -> list[Question]:
    """Plan a batch of questions from knowledge gaps.

    Ranks gaps, filters by status (OPEN only), generates questions,
    excludes already-asked questions, and returns up to max_batch questions
    in priority order.

    Args:
        gaps: List of KnowledgeGap instances.
        max_batch: Maximum number of questions to return. Must be >= 1.
        already_asked_question_ids: Set of question IDs to exclude.

    Returns:
        List of up to max_batch Question objects.

    Raises:
        ValueError: If max_batch < 1.
    """
    if max_batch < 1:
        raise ValueError("max_batch must be at least 1")

    ranked = rank_gaps(gaps)

    open_gaps = [g for g in ranked if g.status == GapStatus.OPEN]

    questions = [
        question_for_gap(gap)
        for gap in open_gaps
        if question_for_gap(gap).id not in already_asked_question_ids
    ]

    return questions[:max_batch]


def needs_follow_up(question: Question, answer: Answer, repository_contradicts: bool) -> bool:
    """Determine whether an answer needs a follow-up question.

    Returns True if:
    - Answer is empty or ambiguous (both value and free_text are empty)
    - Question type is FREE_TEXT and answer is too short (<8 chars)
    - Repository contradicts the answer

    Args:
        question: The Question that was asked.
        answer: The Answer provided.
        repository_contradicts: Flag indicating repository conflict.

    Returns:
        True if a follow-up is needed, False otherwise.
    """
    if repository_contradicts:
        return True

    is_empty = not answer.value.strip() and not answer.free_text.strip()
    if is_empty:
        return True

    if question.type == QuestionType.FREE_TEXT:
        if len(answer.free_text.strip()) < 8:
            return True

    return False


def build_follow_up_question(original: Question, answer: Answer, max_depth: int) -> Question | None:
    """Build an adaptive follow-up question.

    Creates a new FREE_TEXT question asking for clarification on the previous
    answer, if the depth limit has not been exceeded.

    Args:
        original: The original Question.
        answer: The Answer to that question.
        max_depth: Maximum follow-up chain depth. If original.depth + 1 > max_depth,
                  returns None.

    Returns:
        A new Question for follow-up, or None if depth limit reached.
    """
    if original.depth + 1 > max_depth:
        return None

    followup_id = f"{original.id}-followup-{original.depth + 1}"
    answer_text = answer.value or answer.free_text
    followup_question = (
        f"Following up on '{original.question}': you answered "
        f"'{answer_text}'. Can you be more specific about scope or constraints?"
    )

    return Question(
        id=followup_id,
        gap_id=original.gap_id,
        question=followup_question,
        type=QuestionType.FREE_TEXT,
        options=[],
        allow_free_text=True,
        reason="Your previous answer needs more detail to become an operative policy.",
        evidence=list(original.evidence),
        impact=list(original.impact),
        follow_up_of=original.id,
        depth=original.depth + 1,
    )

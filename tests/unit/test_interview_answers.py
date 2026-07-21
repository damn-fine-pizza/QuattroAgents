"""Tests for interview answer normalization, classification, and decision conversion."""

from datetime import UTC, datetime

from quattroagents.domain import (
    Answer,
    AnswerClassification,
    DecisionScope,
    DecisionSourceType,
    DecisionStatus,
    GapStatus,
    GapType,
    KnowledgeGap,
    Priority,
    Question,
    QuestionOption,
    QuestionType,
)
from quattroagents.interview.answers import (
    answer_to_decision,
    classify_answer,
    normalize_answer,
)

# ============================================================================
# normalize_answer tests
# ============================================================================


def test_normalize_answer_boolean_with_declared_options_matching_option_id() -> None:
    """BOOLEAN question with options: raw value matching option id (case-insensitive)."""
    question = Question(
        id="q1",
        gap_id="test-gap",
        question="Is this enabled?",
        type=QuestionType.BOOLEAN,
        options=[
            QuestionOption(id="enabled", label="Yes, enabled"),
            QuestionOption(id="disabled", label="No, disabled"),
        ],
    )

    # Test case-insensitive matching
    answer = normalize_answer(question, "ENABLED", "")
    assert answer.value == "enabled"
    assert answer.question_id == "q1"
    assert answer.source == "user"
    assert answer.confidence == 1.0
    assert answer.valid_from
    assert answer.valid_until is None
    assert answer.classification == []
    assert answer.free_text == ""

    # Test lowercase matching
    answer = normalize_answer(question, "disabled", "")
    assert answer.value == "disabled"


def test_normalize_answer_boolean_with_yes_no_variants() -> None:
    """BOOLEAN question with options: yes/no variants map to first/second option."""
    question = Question(
        id="q2",
        gap_id="test-gap",
        question="Do you want this?",
        type=QuestionType.BOOLEAN,
        options=[
            QuestionOption(id="affirmative", label="Yes"),
            QuestionOption(id="negative", label="No"),
        ],
    )

    # Test "yes" variants map to first option
    for raw in ["yes", "y", "true", "1"]:
        answer = normalize_answer(question, raw, "")
        assert answer.value == "affirmative", f"Expected 'affirmative' for '{raw}'"

    # Test "no" variants map to second option
    for raw in ["no", "n", "false", "0"]:
        answer = normalize_answer(question, raw, "")
        assert answer.value == "negative", f"Expected 'negative' for '{raw}'"


def test_normalize_answer_single_choice_matching_option_id_case_insensitive() -> None:
    """SINGLE_CHOICE with options: matching option id normalized to canonical-cased id."""
    question = Question(
        id="q3",
        gap_id="test-gap",
        question="Choose one",
        type=QuestionType.SINGLE_CHOICE,
        options=[
            QuestionOption(id="option_a", label="Option A"),
            QuestionOption(id="option_b", label="Option B"),
        ],
    )

    # Case-insensitive matching normalizes to canonical case
    answer = normalize_answer(question, "OPTION_A", "")
    assert answer.value == "option_a"

    answer = normalize_answer(question, "Option_B", "")
    assert answer.value == "option_b"

    # Non-matching value stays as-is (stripped)
    answer = normalize_answer(question, "unknown_option", "")
    assert answer.value == "unknown_option"


def test_normalize_answer_free_text_question() -> None:
    """FREE_TEXT question: value is stripped raw value."""
    question = Question(
        id="q4",
        gap_id="test-gap",
        question="Describe something",
        type=QuestionType.FREE_TEXT,
    )

    answer = normalize_answer(question, "  some response  ", "")
    assert answer.value == "some response"
    assert answer.question_id == "q4"


def test_normalize_answer_free_text_field_always_stripped() -> None:
    """free_text field is always the stripped raw_free_text regardless of question type."""
    question = Question(
        id="q5",
        gap_id="test-gap",
        question="What is your opinion?",
        type=QuestionType.SINGLE_CHOICE,
        options=[QuestionOption(id="opt1", label="Option 1")],
    )

    # Test with various types - free_text should always be stripped
    answer = normalize_answer(question, "opt1", "  explanatory text  ")
    assert answer.free_text == "explanatory text"

    answer = normalize_answer(question, "opt1", "")
    assert answer.free_text == ""


def test_normalize_answer_has_correct_metadata() -> None:
    """Result has source='user', confidence=1.0, valid_from set, valid_until=None, empty classification."""
    question = Question(
        id="q6",
        gap_id="test-gap",
        question="A question",
        type=QuestionType.FREE_TEXT,
    )

    before = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    answer = normalize_answer(question, "test value", "test text")
    after = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    assert answer.source == "user"
    assert answer.confidence == 1.0
    # valid_from should be in ISO format and within expected range
    assert "T" in answer.valid_from
    assert "Z" in answer.valid_from
    assert before <= answer.valid_from <= after
    assert answer.valid_until is None
    assert answer.classification == []


# ============================================================================
# classify_answer tests
# ============================================================================


def test_classify_answer_missing_test_policy_gap_includes_validation_rule() -> None:
    """gap_id starting with 'missing-test-policy' includes VALIDATION_RULE."""
    question = Question(
        id="q7",
        gap_id="missing-test-policy-for-api",
        question="What is the test policy?",
        type=QuestionType.FREE_TEXT,
    )
    answer = Answer(
        question_id="q7",
        value="comprehensive",
        free_text="All endpoints tested",
    )

    classifications = classify_answer(question, answer)
    assert AnswerClassification.VALIDATION_RULE in classifications


def test_classify_answer_legacy_area_ownership_gap_includes_ownership() -> None:
    """gap_id starting with 'legacy-area-ownership' includes OWNERSHIP."""
    question = Question(
        id="q8",
        gap_id="legacy-area-ownership-core",
        question="Who owns this area?",
        type=QuestionType.FREE_TEXT,
    )
    answer = Answer(
        question_id="q8",
        value="team-a",
    )

    classifications = classify_answer(question, answer)
    assert AnswerClassification.OWNERSHIP in classifications


def test_classify_answer_agent_autonomy_gap_includes_policy() -> None:
    """gap_id starting with 'agent-autonomy' includes POLICY."""
    question = Question(
        id="q9",
        gap_id="agent-autonomy-level",
        question="What is the agent autonomy level?",
        type=QuestionType.SINGLE_CHOICE,
        options=[
            QuestionOption(id="full", label="Full autonomy"),
            QuestionOption(id="limited", label="Limited autonomy"),
        ],
    )
    answer = Answer(
        question_id="q9",
        value="limited",
    )

    classifications = classify_answer(question, answer)
    assert AnswerClassification.POLICY in classifications


def test_classify_answer_gap_id_specific_prefixes() -> None:
    """gap_ids starting with tool-policy, multi-language-priority, legacy-authority map correctly."""
    # tool-policy -> TOOL_POLICY
    question1 = Question(
        id="q10a",
        gap_id="tool-policy-for-git",
        question="Git policy?",
        type=QuestionType.FREE_TEXT,
    )
    answer1 = Answer(question_id="q10a", value="no-force-push")
    assert classify_answer(question1, answer1) == [AnswerClassification.TOOL_POLICY]

    # multi-language-priority -> PRIORITY
    question2 = Question(
        id="q10b",
        gap_id="multi-language-priority-ranking",
        question="Language priority?",
        type=QuestionType.FREE_TEXT,
    )
    answer2 = Answer(question_id="q10b", value="python-first")
    assert classify_answer(question2, answer2) == [AnswerClassification.PRIORITY]

    # legacy-authority -> CONSTRAINT
    question3 = Question(
        id="q10c",
        gap_id="legacy-authority-source",
        question="Legacy authority?",
        type=QuestionType.FREE_TEXT,
    )
    answer3 = Answer(question_id="q10c", value="original-design")
    assert classify_answer(question3, answer3) == [AnswerClassification.CONSTRAINT]


def test_classify_answer_fallback_to_preference() -> None:
    """Non-matching gap_id with plain answer value falls back to PREFERENCE; empty everything falls to FACT."""
    # Plain answer with free_text -> PREFERENCE
    question1 = Question(
        id="q11a",
        gap_id="custom-gap-id",
        question="Custom question?",
        type=QuestionType.FREE_TEXT,
    )
    answer1 = Answer(question_id="q11a", value="yes", free_text="reasoning here")
    assert classify_answer(question1, answer1) == [AnswerClassification.PREFERENCE]

    # Answer with value in preference list and no free_text -> PREFERENCE
    question2 = Question(
        id="q11b",
        gap_id="another-gap",
        question="Another question?",
        type=QuestionType.FREE_TEXT,
    )
    answer2 = Answer(question_id="q11b", value="required")
    assert classify_answer(question2, answer2) == [AnswerClassification.PREFERENCE]

    # Empty answer, empty free_text, unrecognized gap_id -> FACT
    question3 = Question(
        id="q11c",
        gap_id="unrecognized-gap",
        question="Another question?",
        type=QuestionType.FREE_TEXT,
    )
    answer3 = Answer(question_id="q11c", value="")
    assert classify_answer(question3, answer3) == [AnswerClassification.FACT]


def test_classify_answer_no_duplicate_classifications() -> None:
    """Result list has no duplicate classifications."""
    # Create a question that might trigger multiple rules, but ensure no dupes
    question = Question(
        id="q12",
        gap_id="tool-policy-git-rules",  # triggers TOOL_POLICY
        question="Tool policy question?",
        type=QuestionType.FREE_TEXT,
    )
    answer = Answer(question_id="q12", value="yes")  # could trigger PREFERENCE fallback

    classifications = classify_answer(question, answer)
    # Should have TOOL_POLICY + PREFERENCE but no duplicates
    seen = set()
    for c in classifications:
        assert c not in seen, f"Duplicate classification: {c}"
        seen.add(c)


# ============================================================================
# answer_to_decision tests
# ============================================================================


def test_answer_to_decision_structure_and_fields() -> None:
    """Decision has correct title, value, source, status, scope_paths, and reason."""
    question = Question(
        id="q13-question",
        gap_id="test-decision-gap",
        question="What is the architecture pattern?",
        type=QuestionType.SINGLE_CHOICE,
        options=[
            QuestionOption(id="monolith", label="Monolith"),
            QuestionOption(id="microservices", label="Microservices"),
        ],
    )

    answer = normalize_answer(question, "microservices", "This is our strategic choice")

    gap = KnowledgeGap(
        id="gap-001",
        topic="Architecture Pattern Decision",
        description="Determine the overall architecture pattern",
        gap_type=GapType.MISSING_PREFERENCE,
        evidence=["src/architecture.md", "docs/design-decisions.md"],
        status=GapStatus.OPEN,
        priority=Priority.HIGH,
    )

    session_id = "session-001"
    decision_id = "decision-001"

    decision = answer_to_decision(question, answer, gap, session_id, decision_id)

    # Verify title matches gap.topic
    assert decision.title == "Architecture Pattern Decision"

    # Verify value contains required keys
    assert "question" in decision.value
    assert decision.value["question"] == "What is the architecture pattern?"
    assert "answer" in decision.value
    assert decision.value["answer"] == "microservices"
    assert "detail" in decision.value
    assert decision.value["detail"] == "This is our strategic choice"
    assert "classification" in decision.value
    assert isinstance(decision.value["classification"], list)

    # Verify source structure
    assert decision.source.type == DecisionSourceType.USER
    assert decision.source.interview_session == session_id
    assert decision.source.question_id == question.id

    # Verify status
    assert decision.status == DecisionStatus.ACTIVE

    # Verify scope_paths
    assert decision.scope_paths == list(gap.evidence)
    assert decision.scope_paths == ["src/architecture.md", "docs/design-decisions.md"]

    # Verify reason uses free_text
    assert decision.reason == "This is our strategic choice"


def test_answer_to_decision_reason_construction_fallback() -> None:
    """When answer.free_text is empty, reason falls back to constructed string."""
    question = Question(
        id="q14-question",
        gap_id="test-gap-fallback",
        question="Do you prefer async operations?",
        type=QuestionType.BOOLEAN,
        options=[
            QuestionOption(id="yes_async", label="Yes"),
            QuestionOption(id="no_sync", label="No"),
        ],
    )

    answer = normalize_answer(question, "yes_async", "")  # No free_text

    gap = KnowledgeGap(
        id="gap-002",
        topic="Async Operations Preference",
        description="User preference on async",
        gap_type=GapType.MISSING_PREFERENCE,
        evidence=["architecture.md"],
        status=GapStatus.OPEN,
    )

    decision = answer_to_decision(question, answer, gap, "session-002", "decision-002")

    # Reason should be constructed since free_text is empty
    assert decision.reason == f"User selected '{answer.value}' for: {question.question}"
    assert "yes_async" in decision.reason
    assert "Do you prefer async operations?" in decision.reason


def test_answer_to_decision_classification_included_in_value() -> None:
    """Decision.value contains classification list with string values."""
    question = Question(
        id="q15-question",
        gap_id="tool-policy-validation",
        question="Tool usage policy?",
        type=QuestionType.FREE_TEXT,
    )

    answer = normalize_answer(question, "restricted-mode", "Only approved tools")

    gap = KnowledgeGap(
        id="gap-003",
        topic="Tool Policy",
        description="Define tool usage policy",
        gap_type=GapType.MISSING_TOOL_POLICY,
        evidence=[],
        status=GapStatus.OPEN,
    )

    decision = answer_to_decision(question, answer, gap, "session-003", "decision-003")

    # Value should have classification as list of strings (not enum objects)
    classifications_in_value = decision.value["classification"]
    assert isinstance(classifications_in_value, list)
    for c in classifications_in_value:
        assert isinstance(c, str)
        # Should be valid classification values
        assert c in [e.value for e in AnswerClassification]


def test_answer_to_decision_metadata() -> None:
    """Decision has proper confidence, scope, and metadata fields."""
    question = Question(
        id="q16-question",
        gap_id="test-gap",
        question="Test question?",
        type=QuestionType.FREE_TEXT,
    )

    answer = normalize_answer(question, "test-value", "")

    gap = KnowledgeGap(
        id="gap-004",
        topic="Test Topic",
        description="Test description",
        gap_type=GapType.MISSING_FACT,
        evidence=["path1.md", "path2.md"],
        status=GapStatus.OPEN,
    )

    decision = answer_to_decision(question, answer, gap, "session-004", "decision-004")

    # Verify other fields
    assert decision.decision_scope == DecisionScope.PROJECT_WIDE
    assert decision.confidence == answer.confidence
    assert decision.id == "decision-004"
    assert decision.created_at
    assert decision.updated_at
    assert "agents" in decision.effects
    assert "skills" in decision.effects
    assert "validations" in decision.effects

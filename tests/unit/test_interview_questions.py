"""Unit tests for the interview questions module.

Tests cover gap-to-question generation, gap ranking, question batching,
follow-up detection, and adaptive follow-up construction.
"""

import pytest

from quattroagents.domain import (
    Answer,
    GapStatus,
    GapType,
    KnowledgeGap,
    Priority,
    Question,
    QuestionType,
)
from quattroagents.interview.questions import (
    build_follow_up_question,
    needs_follow_up,
    plan_question_batch,
    question_for_gap,
    rank_gaps,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def gap_ambiguous_architecture() -> KnowledgeGap:
    """A gap for ambiguous architecture."""
    return KnowledgeGap(
        id="gap-1",
        topic="architecture",
        description="Is the microservice split correct?",
        gap_type=GapType.AMBIGUOUS_ARCHITECTURE,
        evidence=["docs/architecture.md"],
        impact={"agents": "high", "skills": "medium"},
        confidence=0.6,
        priority=Priority.HIGH,
    )


@pytest.fixture
def gap_conflicting_evidence() -> KnowledgeGap:
    """A gap with conflicting evidence."""
    return KnowledgeGap(
        id="gap-2",
        topic="configuration",
        description="Which config takes precedence?",
        gap_type=GapType.CONFLICTING_EVIDENCE,
        evidence=["config.yaml", "env.json"],
        impact={"permissions": "high"},
        confidence=0.4,
        priority=Priority.MEDIUM,
    )


@pytest.fixture
def gap_missing_ownership() -> KnowledgeGap:
    """A gap for missing ownership."""
    return KnowledgeGap(
        id="gap-3",
        topic="legacy",
        description="Is this legacy code restricted?",
        gap_type=GapType.MISSING_OWNERSHIP,
        evidence=["src/legacy"],
        impact={},
        confidence=0.7,
        priority=Priority.LOW,
    )


@pytest.fixture
def gap_missing_validation_rule() -> KnowledgeGap:
    """A gap for missing validation rule."""
    return KnowledgeGap(
        id="gap-4",
        topic="testing",
        description="Should tests be mandatory?",
        gap_type=GapType.MISSING_VALIDATION_RULE,
        evidence=["tests/"],
        impact={"skills": "high"},
        confidence=0.8,
        priority=Priority.HIGH,
    )


@pytest.fixture
def gap_missing_priority() -> KnowledgeGap:
    """A gap for missing priority."""
    return KnowledgeGap(
        id="gap-5",
        topic="workflow",
        description="What priority for critical bugs?",
        gap_type=GapType.MISSING_PRIORITY,
        evidence=[],
        impact={"agents": "medium", "skills": "low"},
        confidence=0.5,
        priority=Priority.MEDIUM,
    )


@pytest.fixture
def gap_missing_tool_policy() -> KnowledgeGap:
    """A gap for missing tool policy."""
    return KnowledgeGap(
        id="gap-6",
        topic="tools",
        description="How to handle tool X if unavailable?",
        gap_type=GapType.MISSING_TOOL_POLICY,
        evidence=["tools/inventory.txt"],
        impact={"permissions": "high"},
        confidence=0.3,
        priority=Priority.HIGH,
    )


@pytest.fixture
def gap_stale_decision() -> KnowledgeGap:
    """A gap for stale decision."""
    return KnowledgeGap(
        id="gap-7",
        topic="architecture",
        description="Is the old API decision still valid?",
        gap_type=GapType.STALE_DECISION,
        evidence=["docs/decisions/api.md"],
        impact={"agents": "high"},
        confidence=0.5,
        priority=Priority.MEDIUM,
    )


@pytest.fixture
def gap_missing_fact() -> KnowledgeGap:
    """A gap for missing fact."""
    return KnowledgeGap(
        id="gap-8",
        topic="deployment",
        description="What is the deployment target?",
        gap_type=GapType.MISSING_FACT,
        evidence=["docs/deployment.md"],
        impact={"agents": "high", "skills": "high"},
        confidence=0.2,
        priority=Priority.HIGH,
    )


@pytest.fixture
def gap_missing_preference() -> KnowledgeGap:
    """A gap for missing preference."""
    return KnowledgeGap(
        id="gap-9",
        topic="coding",
        description="Preferred language for scripts?",
        gap_type=GapType.MISSING_PREFERENCE,
        evidence=[],
        impact={},
        confidence=0.5,
        priority=Priority.LOW,
    )


@pytest.fixture
def gap_missing_constraint() -> KnowledgeGap:
    """A gap for missing constraint."""
    return KnowledgeGap(
        id="gap-10",
        topic="performance",
        description="What is the latency constraint?",
        gap_type=GapType.MISSING_CONSTRAINT,
        evidence=["docs/sla.md"],
        impact={"agents": "high", "skills": "medium", "swarm": "low"},
        confidence=0.6,
        priority=Priority.MEDIUM,
    )


@pytest.fixture
def gap_missing_workflow() -> KnowledgeGap:
    """A gap for missing workflow."""
    return KnowledgeGap(
        id="gap-11",
        topic="process",
        description="What is the release workflow?",
        gap_type=GapType.MISSING_WORKFLOW,
        evidence=["docs/release.md"],
        impact={"agents": "high"},
        confidence=0.4,
        priority=Priority.MEDIUM,
    )


# ============================================================================
# Tests for question_for_gap
# ============================================================================


class TestQuestionForGap:
    """Test gap-to-question transformation for each gap type."""

    def test_ambiguous_architecture_creates_free_text_question(
        self, gap_ambiguous_architecture: KnowledgeGap
    ) -> None:
        """AMBIGUOUS_ARCHITECTURE should produce FREE_TEXT question."""
        q = question_for_gap(gap_ambiguous_architecture)

        assert q.type == QuestionType.FREE_TEXT
        assert q.options == []
        assert q.allow_free_text is True
        assert q.depth == 0
        assert q.follow_up_of is None

    def test_conflicting_evidence_creates_free_text_question(
        self, gap_conflicting_evidence: KnowledgeGap
    ) -> None:
        """CONFLICTING_EVIDENCE should produce FREE_TEXT question."""
        q = question_for_gap(gap_conflicting_evidence)

        assert q.type == QuestionType.FREE_TEXT
        assert q.options == []
        assert q.allow_free_text is True
        assert q.depth == 0
        assert q.follow_up_of is None

    def test_missing_ownership_creates_boolean_question(
        self, gap_missing_ownership: KnowledgeGap
    ) -> None:
        """MISSING_OWNERSHIP should produce BOOLEAN question with 2 options."""
        q = question_for_gap(gap_missing_ownership)

        assert q.type == QuestionType.BOOLEAN
        assert len(q.options) == 2
        assert q.options[0].id == "yes"
        assert q.options[1].id == "no"
        assert q.allow_free_text is False
        assert q.depth == 0
        assert q.follow_up_of is None

    def test_missing_validation_rule_creates_boolean_question(
        self, gap_missing_validation_rule: KnowledgeGap
    ) -> None:
        """MISSING_VALIDATION_RULE should produce BOOLEAN question with 2 options."""
        q = question_for_gap(gap_missing_validation_rule)

        assert q.type == QuestionType.BOOLEAN
        assert len(q.options) == 2
        assert q.options[0].id == "required"
        assert q.options[1].id == "not_required"
        assert q.allow_free_text is True
        assert q.depth == 0
        assert q.follow_up_of is None

    def test_missing_priority_creates_single_choice_question(
        self, gap_missing_priority: KnowledgeGap
    ) -> None:
        """MISSING_PRIORITY should produce SINGLE_CHOICE question."""
        q = question_for_gap(gap_missing_priority)

        assert q.type == QuestionType.SINGLE_CHOICE
        assert q.options == []
        assert q.allow_free_text is True
        assert q.depth == 0
        assert q.follow_up_of is None

    def test_missing_tool_policy_creates_single_choice_question(
        self, gap_missing_tool_policy: KnowledgeGap
    ) -> None:
        """MISSING_TOOL_POLICY should produce SINGLE_CHOICE question with 2 fixed options."""
        q = question_for_gap(gap_missing_tool_policy)

        assert q.type == QuestionType.SINGLE_CHOICE
        assert len(q.options) == 2
        assert q.options[0].id == "assume-available-later"
        assert q.options[1].id == "omit"
        assert q.allow_free_text is False
        assert q.depth == 0
        assert q.follow_up_of is None

    def test_stale_decision_creates_boolean_question(
        self, gap_stale_decision: KnowledgeGap
    ) -> None:
        """STALE_DECISION should produce BOOLEAN question with 2 options."""
        q = question_for_gap(gap_stale_decision)

        assert q.type == QuestionType.BOOLEAN
        assert len(q.options) == 2
        assert q.options[0].id == "still-valid"
        assert q.options[1].id == "obsolete"
        assert q.allow_free_text is True
        assert q.depth == 0
        assert q.follow_up_of is None

    def test_missing_fact_creates_free_text_question(self, gap_missing_fact: KnowledgeGap) -> None:
        """MISSING_FACT should produce FREE_TEXT question."""
        q = question_for_gap(gap_missing_fact)

        assert q.type == QuestionType.FREE_TEXT
        assert q.options == []
        assert q.allow_free_text is True
        assert q.depth == 0
        assert q.follow_up_of is None

    def test_missing_preference_creates_free_text_question(
        self, gap_missing_preference: KnowledgeGap
    ) -> None:
        """MISSING_PREFERENCE should produce FREE_TEXT question."""
        q = question_for_gap(gap_missing_preference)

        assert q.type == QuestionType.FREE_TEXT
        assert q.options == []
        assert q.allow_free_text is True
        assert q.depth == 0
        assert q.follow_up_of is None

    def test_missing_constraint_creates_free_text_question(
        self, gap_missing_constraint: KnowledgeGap
    ) -> None:
        """MISSING_CONSTRAINT should produce FREE_TEXT question."""
        q = question_for_gap(gap_missing_constraint)

        assert q.type == QuestionType.FREE_TEXT
        assert q.options == []
        assert q.allow_free_text is True
        assert q.depth == 0
        assert q.follow_up_of is None

    def test_missing_workflow_creates_free_text_question(
        self, gap_missing_workflow: KnowledgeGap
    ) -> None:
        """MISSING_WORKFLOW should produce FREE_TEXT question."""
        q = question_for_gap(gap_missing_workflow)

        assert q.type == QuestionType.FREE_TEXT
        assert q.options == []
        assert q.allow_free_text is True
        assert q.depth == 0
        assert q.follow_up_of is None

    def test_question_id_is_derived_from_gap_id(self, gap_missing_fact: KnowledgeGap) -> None:
        """Question id should be derived from gap id."""
        q = question_for_gap(gap_missing_fact)

        assert q.id == f"question-{gap_missing_fact.id}"
        assert q.gap_id == gap_missing_fact.id

    def test_question_inherits_gap_description(self, gap_missing_fact: KnowledgeGap) -> None:
        """Question text should be the gap description."""
        q = question_for_gap(gap_missing_fact)

        assert q.question == gap_missing_fact.description

    def test_question_reason_from_high_and_medium_impact(
        self, gap_missing_constraint: KnowledgeGap
    ) -> None:
        """Reason should list only high and medium impact areas."""
        q = question_for_gap(gap_missing_constraint)

        assert "agents" in q.reason
        assert "skills" in q.reason
        assert "swarm" not in q.reason  # low impact, excluded

    def test_question_reason_generic_for_empty_impact(
        self, gap_missing_preference: KnowledgeGap
    ) -> None:
        """Reason should be generic if no impact."""
        q = question_for_gap(gap_missing_preference)

        assert q.reason == "This gap affects decision-making."

    def test_question_evidence_inherited_from_gap(self, gap_missing_fact: KnowledgeGap) -> None:
        """Question evidence should match gap evidence."""
        q = question_for_gap(gap_missing_fact)

        assert q.evidence == gap_missing_fact.evidence

    def test_question_impact_list_from_gap_impact(
        self, gap_missing_constraint: KnowledgeGap
    ) -> None:
        """Question impact should be list of high/medium impact keys."""
        q = question_for_gap(gap_missing_constraint)

        assert set(q.impact) == {"agents", "skills"}


# ============================================================================
# Tests for rank_gaps
# ============================================================================


class TestRankGaps:
    """Test gap ranking by priority, uncertainty, and impact."""

    def test_high_priority_ranks_above_low_priority(self) -> None:
        """HIGH priority gap should rank above LOW priority gap (same other factors)."""
        gap_high = KnowledgeGap(
            id="gap-high",
            topic="test",
            description="test",
            gap_type=GapType.MISSING_FACT,
            confidence=0.5,
            priority=Priority.HIGH,
            impact={"agents": "medium"},
        )
        gap_low = KnowledgeGap(
            id="gap-low",
            topic="test",
            description="test",
            gap_type=GapType.MISSING_FACT,
            confidence=0.5,
            priority=Priority.LOW,
            impact={"agents": "medium"},
        )

        ranked = rank_gaps([gap_low, gap_high])

        assert ranked[0].id == "gap-high"
        assert ranked[1].id == "gap-low"

    def test_ties_broken_by_gap_id_descending(self) -> None:
        """Ties should be broken by gap id (descending due to reverse=True)."""
        gap_a = KnowledgeGap(
            id="gap-aaa",
            topic="test",
            description="test",
            gap_type=GapType.MISSING_FACT,
            confidence=0.5,
            priority=Priority.MEDIUM,
            impact={"agents": "high"},
        )
        gap_b = KnowledgeGap(
            id="gap-zzz",
            topic="test",
            description="test",
            gap_type=GapType.MISSING_FACT,
            confidence=0.5,
            priority=Priority.MEDIUM,
            impact={"agents": "high"},
        )

        ranked = rank_gaps([gap_a, gap_b])

        assert ranked[0].id == "gap-zzz"
        assert ranked[1].id == "gap-aaa"

    def test_score_accounts_for_uncertainty(self) -> None:
        """Lower confidence (higher uncertainty) should increase score."""
        gap_high_confidence = KnowledgeGap(
            id="gap-sure",
            topic="test",
            description="test",
            gap_type=GapType.MISSING_FACT,
            confidence=0.9,
            priority=Priority.MEDIUM,
            impact={"agents": "high"},
        )
        gap_low_confidence = KnowledgeGap(
            id="gap-unsure",
            topic="test",
            description="test",
            gap_type=GapType.MISSING_FACT,
            confidence=0.1,
            priority=Priority.MEDIUM,
            impact={"agents": "high"},
        )

        ranked = rank_gaps([gap_high_confidence, gap_low_confidence])

        assert ranked[0].id == "gap-unsure"
        assert ranked[1].id == "gap-sure"

    def test_score_accounts_for_impact(self) -> None:
        """Higher impact should increase score."""
        gap_high_impact = KnowledgeGap(
            id="gap-impact-high",
            topic="test",
            description="test",
            gap_type=GapType.MISSING_FACT,
            confidence=0.5,
            priority=Priority.MEDIUM,
            impact={"agents": "high", "skills": "high"},
        )
        gap_low_impact = KnowledgeGap(
            id="gap-impact-low",
            topic="test",
            description="test",
            gap_type=GapType.MISSING_FACT,
            confidence=0.5,
            priority=Priority.MEDIUM,
            impact={"agents": "low"},
        )

        ranked = rank_gaps([gap_low_impact, gap_high_impact])

        assert ranked[0].id == "gap-impact-high"
        assert ranked[1].id == "gap-impact-low"

    def test_empty_list_returns_empty(self) -> None:
        """Ranking an empty list should return empty."""
        ranked = rank_gaps([])

        assert ranked == []

    def test_single_gap_returns_single_gap(self) -> None:
        """Ranking a single gap should return it."""
        gap = KnowledgeGap(
            id="gap-only",
            topic="test",
            description="test",
            gap_type=GapType.MISSING_FACT,
        )

        ranked = rank_gaps([gap])

        assert len(ranked) == 1
        assert ranked[0].id == "gap-only"


# ============================================================================
# Tests for plan_question_batch
# ============================================================================


class TestPlanQuestionBatch:
    """Test question batch planning."""

    def test_respects_max_batch_limit(self) -> None:
        """Should return at most max_batch questions."""
        gaps = [
            KnowledgeGap(
                id=f"gap-{i}",
                topic="test",
                description=f"test {i}",
                gap_type=GapType.MISSING_FACT,
                status=GapStatus.OPEN,
            )
            for i in range(5)
        ]

        batch = plan_question_batch(gaps, max_batch=2, already_asked_question_ids=set())

        assert len(batch) == 2

    def test_excludes_non_open_gaps(self) -> None:
        """Should exclude gaps with status != OPEN."""
        gaps = [
            KnowledgeGap(
                id="gap-open",
                topic="test",
                description="test",
                gap_type=GapType.MISSING_FACT,
                status=GapStatus.OPEN,
            ),
            KnowledgeGap(
                id="gap-resolved",
                topic="test",
                description="test",
                gap_type=GapType.MISSING_FACT,
                status=GapStatus.RESOLVED,
            ),
            KnowledgeGap(
                id="gap-dismissed",
                topic="test",
                description="test",
                gap_type=GapType.MISSING_FACT,
                status=GapStatus.DISMISSED,
            ),
        ]

        batch = plan_question_batch(gaps, max_batch=10, already_asked_question_ids=set())

        assert len(batch) == 1
        assert batch[0].gap_id == "gap-open"

    def test_excludes_already_asked_questions(self) -> None:
        """Should exclude questions whose id is in already_asked_question_ids."""
        gaps = [
            KnowledgeGap(
                id="gap-1",
                topic="test",
                description="test 1",
                gap_type=GapType.MISSING_FACT,
                status=GapStatus.OPEN,
            ),
            KnowledgeGap(
                id="gap-2",
                topic="test",
                description="test 2",
                gap_type=GapType.MISSING_FACT,
                status=GapStatus.OPEN,
            ),
        ]
        already_asked = {"question-gap-1"}

        batch = plan_question_batch(gaps, max_batch=10, already_asked_question_ids=already_asked)

        assert len(batch) == 1
        assert batch[0].gap_id == "gap-2"

    def test_raises_value_error_for_max_batch_less_than_1(self) -> None:
        """Should raise ValueError when max_batch < 1."""
        gap = KnowledgeGap(
            id="gap-1",
            topic="test",
            description="test",
            gap_type=GapType.MISSING_FACT,
            status=GapStatus.OPEN,
        )

        with pytest.raises(ValueError, match="max_batch must be at least 1"):
            plan_question_batch([gap], max_batch=0, already_asked_question_ids=set())

    def test_raises_value_error_for_negative_max_batch(self) -> None:
        """Should raise ValueError for negative max_batch."""
        gap = KnowledgeGap(
            id="gap-1",
            topic="test",
            description="test",
            gap_type=GapType.MISSING_FACT,
            status=GapStatus.OPEN,
        )

        with pytest.raises(ValueError, match="max_batch must be at least 1"):
            plan_question_batch([gap], max_batch=-1, already_asked_question_ids=set())

    def test_respects_ranking_order(self) -> None:
        """Should return questions in ranked gap order."""
        gaps = [
            KnowledgeGap(
                id="gap-low",
                topic="test",
                description="test",
                gap_type=GapType.MISSING_FACT,
                status=GapStatus.OPEN,
                priority=Priority.LOW,
                confidence=0.9,
                impact={"agents": "low"},
            ),
            KnowledgeGap(
                id="gap-high",
                topic="test",
                description="test",
                gap_type=GapType.MISSING_FACT,
                status=GapStatus.OPEN,
                priority=Priority.HIGH,
                confidence=0.5,
                impact={"agents": "high"},
            ),
        ]

        batch = plan_question_batch(gaps, max_batch=10, already_asked_question_ids=set())

        assert len(batch) == 2
        assert batch[0].gap_id == "gap-high"
        assert batch[1].gap_id == "gap-low"

    def test_empty_gaps_returns_empty(self) -> None:
        """Empty gaps list should return empty batch."""
        batch = plan_question_batch([], max_batch=5, already_asked_question_ids=set())

        assert batch == []

    def test_all_gaps_non_open_returns_empty(self) -> None:
        """All non-OPEN gaps should return empty batch."""
        gaps = [
            KnowledgeGap(
                id="gap-1",
                topic="test",
                description="test",
                gap_type=GapType.MISSING_FACT,
                status=GapStatus.RESOLVED,
            ),
        ]

        batch = plan_question_batch(gaps, max_batch=5, already_asked_question_ids=set())

        assert batch == []


# ============================================================================
# Tests for needs_follow_up
# ============================================================================


class TestNeedsFollowUp:
    """Test follow-up detection logic."""

    def test_returns_true_when_repository_contradicts(self) -> None:
        """Should return True when repository_contradicts is True."""
        question = Question(
            id="q-1",
            gap_id="gap-1",
            question="test",
            type=QuestionType.BOOLEAN,
        )
        answer = Answer(
            question_id="q-1",
            value="yes",
            free_text="detailed answer",
        )

        result = needs_follow_up(question, answer, repository_contradicts=True)

        assert result is True

    def test_returns_true_for_empty_answer_both_empty(self) -> None:
        """Should return True when both value and free_text are empty."""
        question = Question(
            id="q-1",
            gap_id="gap-1",
            question="test",
            type=QuestionType.FREE_TEXT,
        )
        answer = Answer(
            question_id="q-1",
            value="",
            free_text="",
        )

        result = needs_follow_up(question, answer, repository_contradicts=False)

        assert result is True

    def test_returns_true_for_empty_answer_value_and_whitespace_free_text(self) -> None:
        """Should return True when value is empty and free_text is only whitespace."""
        question = Question(
            id="q-1",
            gap_id="gap-1",
            question="test",
            type=QuestionType.BOOLEAN,
        )
        answer = Answer(
            question_id="q-1",
            value="",
            free_text="   \t\n",
        )

        result = needs_follow_up(question, answer, repository_contradicts=False)

        assert result is True

    def test_returns_true_for_free_text_question_with_short_answer(self) -> None:
        """Should return True for FREE_TEXT question with answer < 8 chars."""
        question = Question(
            id="q-1",
            gap_id="gap-1",
            question="test",
            type=QuestionType.FREE_TEXT,
        )
        answer = Answer(
            question_id="q-1",
            value="",
            free_text="short",  # 5 chars
        )

        result = needs_follow_up(question, answer, repository_contradicts=False)

        assert result is True

    def test_returns_true_for_free_text_question_with_short_answer_whitespace_stripped(
        self,
    ) -> None:
        """Should check free_text length after stripping whitespace."""
        question = Question(
            id="q-1",
            gap_id="gap-1",
            question="test",
            type=QuestionType.FREE_TEXT,
        )
        answer = Answer(
            question_id="q-1",
            value="",
            free_text="  shrt  ",  # 4 chars after strip
        )

        result = needs_follow_up(question, answer, repository_contradicts=False)

        assert result is True

    def test_returns_false_for_free_text_question_with_adequate_answer(self) -> None:
        """Should return False for FREE_TEXT question with answer >= 8 chars."""
        question = Question(
            id="q-1",
            gap_id="gap-1",
            question="test",
            type=QuestionType.FREE_TEXT,
        )
        answer = Answer(
            question_id="q-1",
            value="",
            free_text="adequate answer",  # 15 chars
        )

        result = needs_follow_up(question, answer, repository_contradicts=False)

        assert result is False

    def test_returns_false_for_boolean_question_with_any_value(self) -> None:
        """Should return False for BOOLEAN question with a value (length not checked)."""
        question = Question(
            id="q-1",
            gap_id="gap-1",
            question="test",
            type=QuestionType.BOOLEAN,
        )
        answer = Answer(
            question_id="q-1",
            value="yes",
            free_text="",
        )

        result = needs_follow_up(question, answer, repository_contradicts=False)

        assert result is False

    def test_returns_false_for_normal_answer_with_no_contradiction(self) -> None:
        """Should return False for normal, detailed answer with no contradiction."""
        question = Question(
            id="q-1",
            gap_id="gap-1",
            question="test",
            type=QuestionType.FREE_TEXT,
        )
        answer = Answer(
            question_id="q-1",
            value="",
            free_text="This is a comprehensive answer with good detail.",
        )

        result = needs_follow_up(question, answer, repository_contradicts=False)

        assert result is False


# ============================================================================
# Tests for build_follow_up_question
# ============================================================================


class TestBuildFollowUpQuestion:
    """Test adaptive follow-up question construction."""

    def test_returns_none_when_depth_limit_exceeded(self) -> None:
        """Should return None when original.depth + 1 > max_depth."""
        original = Question(
            id="q-1",
            gap_id="gap-1",
            question="original question",
            type=QuestionType.FREE_TEXT,
            depth=2,
        )
        answer = Answer(
            question_id="q-1",
            value="some answer",
        )

        result = build_follow_up_question(original, answer, max_depth=2)

        assert result is None

    def test_returns_question_when_within_depth_limit(self) -> None:
        """Should return a Question when within depth limit."""
        original = Question(
            id="q-1",
            gap_id="gap-1",
            question="original question",
            type=QuestionType.FREE_TEXT,
            depth=0,
        )
        answer = Answer(
            question_id="q-1",
            value="some answer",
        )

        result = build_follow_up_question(original, answer, max_depth=2)

        assert result is not None

    def test_follow_up_has_increased_depth(self) -> None:
        """Follow-up should have depth = original.depth + 1."""
        original = Question(
            id="q-1",
            gap_id="gap-1",
            question="original question",
            type=QuestionType.FREE_TEXT,
            depth=1,
        )
        answer = Answer(
            question_id="q-1",
            value="some answer",
        )

        result = build_follow_up_question(original, answer, max_depth=3)

        assert result is not None
        assert result.depth == 2

    def test_follow_up_references_original_question(self) -> None:
        """Follow-up should set follow_up_of to original.id."""
        original = Question(
            id="q-1",
            gap_id="gap-1",
            question="original question",
            type=QuestionType.FREE_TEXT,
            depth=0,
        )
        answer = Answer(
            question_id="q-1",
            value="some answer",
        )

        result = build_follow_up_question(original, answer, max_depth=2)

        assert result is not None
        assert result.follow_up_of == "q-1"

    def test_follow_up_is_free_text_type(self) -> None:
        """Follow-up should always be FREE_TEXT type."""
        original = Question(
            id="q-1",
            gap_id="gap-1",
            question="original question",
            type=QuestionType.BOOLEAN,
            depth=0,
        )
        answer = Answer(
            question_id="q-1",
            value="yes",
        )

        result = build_follow_up_question(original, answer, max_depth=2)

        assert result is not None
        assert result.type == QuestionType.FREE_TEXT

    def test_follow_up_has_empty_options(self) -> None:
        """Follow-up should have empty options list."""
        original = Question(
            id="q-1",
            gap_id="gap-1",
            question="original question",
            type=QuestionType.FREE_TEXT,
            depth=0,
        )
        answer = Answer(
            question_id="q-1",
            value="some answer",
        )

        result = build_follow_up_question(original, answer, max_depth=2)

        assert result is not None
        assert result.options == []

    def test_follow_up_allows_free_text(self) -> None:
        """Follow-up should allow free text."""
        original = Question(
            id="q-1",
            gap_id="gap-1",
            question="original question",
            type=QuestionType.FREE_TEXT,
            depth=0,
        )
        answer = Answer(
            question_id="q-1",
            value="some answer",
        )

        result = build_follow_up_question(original, answer, max_depth=2)

        assert result is not None
        assert result.allow_free_text is True

    def test_follow_up_id_format(self) -> None:
        """Follow-up id should be: original_id-followup-depth+1."""
        original = Question(
            id="q-1",
            gap_id="gap-1",
            question="original question",
            type=QuestionType.FREE_TEXT,
            depth=0,
        )
        answer = Answer(
            question_id="q-1",
            value="some answer",
        )

        result = build_follow_up_question(original, answer, max_depth=2)

        assert result is not None
        assert result.id == "q-1-followup-1"

    def test_follow_up_id_increments_depth(self) -> None:
        """Follow-up id should increment depth correctly."""
        original = Question(
            id="q-1",
            gap_id="gap-1",
            question="original question",
            type=QuestionType.FREE_TEXT,
            depth=2,
        )
        answer = Answer(
            question_id="q-1",
            value="some answer",
        )

        result = build_follow_up_question(original, answer, max_depth=5)

        assert result is not None
        assert result.id == "q-1-followup-3"

    def test_follow_up_preserves_gap_id(self) -> None:
        """Follow-up should have the same gap_id as original."""
        original = Question(
            id="q-1",
            gap_id="gap-123",
            question="original question",
            type=QuestionType.FREE_TEXT,
            depth=0,
        )
        answer = Answer(
            question_id="q-1",
            value="some answer",
        )

        result = build_follow_up_question(original, answer, max_depth=2)

        assert result is not None
        assert result.gap_id == "gap-123"

    def test_follow_up_text_references_original_question(self) -> None:
        """Follow-up question text should reference the original question."""
        original = Question(
            id="q-1",
            gap_id="gap-1",
            question="What is the policy?",
            type=QuestionType.FREE_TEXT,
            depth=0,
        )
        answer = Answer(
            question_id="q-1",
            value="partial response",
        )

        result = build_follow_up_question(original, answer, max_depth=2)

        assert result is not None
        assert "What is the policy?" in result.question
        assert "partial response" in result.question

    def test_follow_up_text_uses_free_text_if_value_empty(self) -> None:
        """Follow-up should use free_text if value is empty."""
        original = Question(
            id="q-1",
            gap_id="gap-1",
            question="What is the policy?",
            type=QuestionType.FREE_TEXT,
            depth=0,
        )
        answer = Answer(
            question_id="q-1",
            value="",
            free_text="just the free text",
        )

        result = build_follow_up_question(original, answer, max_depth=2)

        assert result is not None
        assert "just the free text" in result.question

    def test_follow_up_inherits_evidence(self) -> None:
        """Follow-up should inherit evidence from original."""
        original = Question(
            id="q-1",
            gap_id="gap-1",
            question="original question",
            type=QuestionType.FREE_TEXT,
            depth=0,
            evidence=["file1.txt", "file2.txt"],
        )
        answer = Answer(
            question_id="q-1",
            value="some answer",
        )

        result = build_follow_up_question(original, answer, max_depth=2)

        assert result is not None
        assert result.evidence == ["file1.txt", "file2.txt"]

    def test_follow_up_inherits_impact(self) -> None:
        """Follow-up should inherit impact from original."""
        original = Question(
            id="q-1",
            gap_id="gap-1",
            question="original question",
            type=QuestionType.FREE_TEXT,
            depth=0,
            impact=["agents", "skills"],
        )
        answer = Answer(
            question_id="q-1",
            value="some answer",
        )

        result = build_follow_up_question(original, answer, max_depth=2)

        assert result is not None
        assert result.impact == ["agents", "skills"]

    def test_follow_up_at_max_depth_boundary(self) -> None:
        """Should return question when depth + 1 == max_depth."""
        original = Question(
            id="q-1",
            gap_id="gap-1",
            question="original question",
            type=QuestionType.FREE_TEXT,
            depth=1,
        )
        answer = Answer(
            question_id="q-1",
            value="some answer",
        )

        result = build_follow_up_question(original, answer, max_depth=2)

        assert result is not None
        assert result.depth == 2

    def test_follow_up_exceeds_max_depth_boundary(self) -> None:
        """Should return None when depth + 1 > max_depth (boundary case)."""
        original = Question(
            id="q-1",
            gap_id="gap-1",
            question="original question",
            type=QuestionType.FREE_TEXT,
            depth=2,
        )
        answer = Answer(
            question_id="q-1",
            value="some answer",
        )

        result = build_follow_up_question(original, answer, max_depth=2)

        assert result is None

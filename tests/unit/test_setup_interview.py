import pytest

from quattroagents.core.setup_interview import (
    build_setup_interview_brief,
    carry_forward_setup_interview,
    confirm_setup_interview,
    default_setup_interview,
    render_setup_interview_brief_markdown,
)


def _analysis() -> dict[str, object]:
    return {"languages": ["python", "rust"], "ci": ["github-actions"]}


def test_brief_includes_base_questions_and_one_per_detected_language() -> None:
    brief = build_setup_interview_brief(_analysis())

    ids = [item["id"] for item in brief["questions"]]
    assert ids[:3] == ["SETUP-1", "SETUP-2", "SETUP-3"]
    assert "SETUP-LANG-python" in ids
    assert "SETUP-LANG-rust" in ids
    assert "SETUP-HISTORY" not in ids


def test_brief_adds_history_question_only_when_history_present() -> None:
    brief = build_setup_interview_brief(
        _analysis(), history=[{"recorded_at": "2026-01-01T00:00:00Z"}]
    )

    ids = [item["id"] for item in brief["questions"]]
    assert "SETUP-HISTORY" in ids
    assert brief["history_considered"] == ["2026-01-01T00:00:00Z"]


def test_confirm_setup_interview_requires_base_questions() -> None:
    brief = build_setup_interview_brief(_analysis())

    with pytest.raises(ValueError, match="missing confirmed answer: SETUP-1"):
        confirm_setup_interview(brief, {"SETUP-2": "x", "SETUP-3": "y"})


def test_confirm_setup_interview_keeps_only_non_empty_optional_answers() -> None:
    brief = build_setup_interview_brief(_analysis())
    record = confirm_setup_interview(
        brief,
        {
            "SETUP-1": "purpose",
            "SETUP-2": "scope",
            "SETUP-3": "tools",
            "SETUP-LANG-python": "  ",
            "SETUP-LANG-rust": "cargo test",
        },
    )

    assert record["status"] == "confirmed"
    assert record["source"] == "interactive"
    assert "SETUP-LANG-python" not in record["answers"]
    assert record["answers"]["SETUP-LANG-rust"] == "cargo test"


def test_default_setup_interview_is_a_non_blocking_baseline() -> None:
    brief = build_setup_interview_brief(_analysis())
    record = default_setup_interview(brief)

    assert record["status"] == "default"
    assert record["answers"] == {}
    assert record["source"] == "baseline"


def test_carry_forward_marks_status_and_source() -> None:
    previous = {
        "schema_version": 1,
        "status": "confirmed",
        "answers": {"SETUP-1": "x"},
        "analysis": {},
    }

    carried = carry_forward_setup_interview(previous)

    assert carried["status"] == "carried_forward"
    assert carried["source"] == "history"
    assert carried["answers"] == {"SETUP-1": "x"}


def test_render_setup_interview_brief_markdown_lists_optional_questions() -> None:
    brief = build_setup_interview_brief(_analysis())
    rendered = render_setup_interview_brief_markdown(brief)

    assert "SETUP-1:" in rendered
    assert "SETUP-LANG-python (optional):" in rendered

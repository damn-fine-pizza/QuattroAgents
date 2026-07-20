from quattroagents.core.agent_synthesis import DEFAULT_MANIFEST, synthesize


def _baseline_interview() -> dict[str, object]:
    return {
        "schema_version": 1,
        "status": "default",
        "answers": {},
        "analysis": {},
        "source": "baseline",
    }


def test_synthesize_with_no_answers_matches_default_manifest_roles_and_skills() -> None:
    manifest = synthesize({"languages": ["python"]}, _baseline_interview(), [])

    assert [role["name"] for role in manifest["roles"]] == [
        role["name"] for role in DEFAULT_MANIFEST["roles"]
    ]
    assert [role["instructions"] for role in manifest["roles"]] == [
        role["instructions"] for role in DEFAULT_MANIFEST["roles"]
    ]
    assert manifest["skills"] == DEFAULT_MANIFEST["skills"]
    assert manifest["rationale"]["languages_considered"] == ["python"]
    assert manifest["rationale"]["interview_answers_used"] == []


def test_synthesize_adds_adhoc_tooling_skill_from_setup_3_answer() -> None:
    interview = {
        "schema_version": 1,
        "status": "confirmed",
        "answers": {"SETUP-3": "Use rtk and codebase-memory-mcp for all lookups."},
        "analysis": {},
        "source": "interactive",
    }

    manifest = synthesize({"languages": []}, interview, [])

    tooling = next(skill for skill in manifest["skills"] if skill["name"] == "qagents-tooling")
    assert tooling["source"] == "adhoc"
    assert "rtk and codebase-memory-mcp" in tooling["body"]
    assert "SETUP-3" in manifest["rationale"]["interview_answers_used"]


def test_synthesize_adds_language_convention_skill_when_answered() -> None:
    interview = {
        "schema_version": 1,
        "status": "confirmed",
        "answers": {"SETUP-LANG-python": "Use pytest and ruff."},
        "analysis": {},
        "source": "interactive",
    }

    manifest = synthesize({"languages": ["python"]}, interview, [])

    convention = next(
        skill for skill in manifest["skills"] if skill["name"] == "qagents-python-conventions"
    )
    assert convention["source"] == "adhoc"
    assert "Use pytest and ruff." in convention["body"]
    assert "SETUP-LANG-python" in manifest["rationale"]["interview_answers_used"]


def test_synthesize_tailors_role_instructions_from_purpose_and_scope_answers() -> None:
    interview = {
        "schema_version": 1,
        "status": "confirmed",
        "answers": {
            "SETUP-1": "Ship a reliable CLI.",
            "SETUP-2": "Prefer small bounded changes.",
        },
        "analysis": {},
        "source": "interactive",
    }

    manifest = synthesize({"languages": []}, interview, [])

    for role in manifest["roles"]:
        assert "Project purpose: Ship a reliable CLI." in role["instructions"]
        assert "Scope guidance: Prefer small bounded changes." in role["instructions"]
        assert role["source"] == "adhoc"
    assert set(manifest["rationale"]["interview_answers_used"]) >= {"SETUP-1", "SETUP-2"}


def test_synthesize_records_history_reused() -> None:
    history = [{"_filename": "2026-01-01T00-00-00Z.json"}]

    manifest = synthesize({"languages": []}, _baseline_interview(), history)

    assert manifest["rationale"]["history_reused"] == ["2026-01-01T00-00-00Z.json"]

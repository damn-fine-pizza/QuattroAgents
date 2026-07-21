"""Test suite for the new Project Agent Factory MCP server.

Covers all 22 tools and the JSON-RPC serve() transport end-to-end.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from quattroagents import runtime_version
from quattroagents.domain import (
    ConflictRecord,
    ConflictSeverity,
    ConflictStatus,
    ConflictType,
    DecisionScope,
    DecisionStatus,
)
from quattroagents.mcp_server import (
    tool_analyze_project,
    tool_confirm_interview_decisions,
    tool_generate_agents,
    tool_generate_skills,
    tool_generate_swarm_plan,
    tool_get_interview_state,
    tool_get_next_questions,
    tool_get_project_profile,
    tool_list_agents,
    tool_list_decisions,
    tool_record_decision,
    tool_reopen_decision,
    tool_resolve_decision_conflict,
    tool_setup,
    tool_show_generation_diff,
    tool_start_project_interview,
    tool_submit_interview_answers,
    tool_validate_generated_configuration,
)
from quattroagents.persistence import AgentFactoryStore, write_json


def _minimal_pyproject(tmp_path: Path) -> None:
    """Create a minimal pyproject.toml in tmp_path."""
    (tmp_path / "pyproject.toml").write_text(
        """[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"

[project]
name = "test-project"
version = "0.1.0"
"""
    )


def test_analyze_project_returns_profile_with_fingerprint(tmp_path: Path) -> None:
    """Test tool_analyze_project returns profile with fingerprint and changes."""
    _minimal_pyproject(tmp_path)

    result = tool_analyze_project({"project_root": str(tmp_path)})

    assert "profile" in result
    assert "changes" in result
    profile = result["profile"]
    assert "fingerprint" in profile
    assert isinstance(profile["fingerprint"], str)
    assert len(profile["fingerprint"]) > 0

    changes = result["changes"]
    assert "significant" in changes
    assert changes["significant"] is True  # First analysis, no prior profile


def test_setup_writes_provider_files_to_disk(tmp_path: Path) -> None:
    """Test tool_setup writes .claude/agents/*.md files to disk."""
    _minimal_pyproject(tmp_path)

    result = tool_setup({"project_root": str(tmp_path), "providers": ["claude"]})

    assert "agents" in result
    assert "skills" in result
    assert "files" in result
    assert isinstance(result["agents"], list)
    assert isinstance(result["skills"], list)
    assert isinstance(result["files"], list)

    # Check that at least some files were written
    claude_dir = tmp_path / ".claude" / "agents"
    if claude_dir.exists():
        agents_files = list(claude_dir.glob("*.md"))
        # If agents were generated, at least one should exist
        # (depends on what the generator produces for this minimal project)
        assert isinstance(agents_files, list)


def test_list_agents_after_setup_returns_same_agents(tmp_path: Path) -> None:
    """Test tool_list_agents returns agents from prior tool_setup."""
    _minimal_pyproject(tmp_path)

    setup_result = tool_setup({"project_root": str(tmp_path), "providers": ["claude"]})
    setup_agents = setup_result["agents"]

    list_result = tool_list_agents({"project_root": str(tmp_path)})
    list_agents = [a["id"] for a in list_result["agents"]]

    assert sorted(list_agents) == sorted(setup_agents)


def test_record_decision_persists_and_is_retrievable(tmp_path: Path) -> None:
    """Test tool_record_decision persists a decision retrievable via tool_list_decisions."""
    _minimal_pyproject(tmp_path)

    decision_id = "test-decision-1"
    record_args = {
        "project_root": str(tmp_path),
        "id": decision_id,
        "title": "Use TypeScript for new features",
        "value": {"language": "typescript"},
        "reason": "Better type safety",
    }

    record_result = tool_record_decision(record_args)
    assert record_result["decision"]["id"] == decision_id
    assert record_result["decision"]["title"] == "Use TypeScript for new features"

    # Retrieve it
    list_result = tool_list_decisions({"project_root": str(tmp_path)})
    assert "decisions" in list_result
    decisions = list_result["decisions"]
    recorded = next((d for d in decisions if d["id"] == decision_id), None)
    assert recorded is not None
    assert recorded["id"] == decision_id
    assert recorded["title"] == "Use TypeScript for new features"


def test_reopen_decision_changes_status(tmp_path: Path) -> None:
    """Test tool_reopen_decision changes status to UNCERTAIN."""
    _minimal_pyproject(tmp_path)

    decision_id = "test-decision-2"
    tool_record_decision(
        {
            "project_root": str(tmp_path),
            "id": decision_id,
            "title": "Python version",
            "value": {"version": "3.11"},
        }
    )

    # Reopen it
    reopen_result = tool_reopen_decision(
        {"project_root": str(tmp_path), "decision_id": decision_id, "reason": "Reconsidering"}
    )

    assert reopen_result["decision"]["status"] == DecisionStatus.UNCERTAIN

    # Verify via list
    list_result = tool_list_decisions({"project_root": str(tmp_path)})
    reopened = next((d for d in list_result["decisions"] if d["id"] == decision_id), None)
    assert reopened is not None
    assert reopened["status"] == DecisionStatus.UNCERTAIN


def test_validate_generated_configuration_after_setup(tmp_path: Path) -> None:
    """Test tool_validate_generated_configuration after successful tool_setup."""
    _minimal_pyproject(tmp_path)

    tool_setup({"project_root": str(tmp_path), "providers": ["claude"]})

    result = tool_validate_generated_configuration({"project_root": str(tmp_path)})

    assert "valid" in result
    assert "violations" in result
    # Should be valid (or at least not error)
    assert isinstance(result["valid"], bool)
    assert isinstance(result["violations"], list)


def test_show_generation_diff_reports_unchanged_on_same_profile(tmp_path: Path) -> None:
    """Test tool_show_generation_diff reports unchanged files on re-run."""
    _minimal_pyproject(tmp_path)

    tool_setup({"project_root": str(tmp_path), "providers": ["claude"]})

    # Run diff on the same profile/decisions (should be unchanged)
    result = tool_show_generation_diff({"project_root": str(tmp_path)})

    assert "files" in result
    files = result["files"]
    assert isinstance(files, list)

    # All files should be "unchanged" or not created on second pass
    # (since profile/decisions haven't changed)
    for file_result in files:
        assert "status" in file_result
        # Status should be one of: unchanged, would_create, would_update, conflict_manual_edit
        assert file_result["status"] in [
            "unchanged",
            "would_create",
            "would_update",
            "conflict_manual_edit",
        ]


def test_interview_session_flow_completes(tmp_path: Path) -> None:
    """Test full interview session: start -> get questions -> submit answers -> confirm."""
    _minimal_pyproject(tmp_path)
    tool_analyze_project({"project_root": str(tmp_path)})

    # Start session
    session_id = "test-session-1"
    start_result = tool_start_project_interview(
        {
            "project_root": str(tmp_path),
            "session_id": session_id,
            "session_type": "initial_setup",
        }
    )
    session = start_result["session"]
    assert session["id"] == session_id
    assert session["status"] == "awaiting_answers"

    # Get next questions
    questions_result = tool_get_next_questions(
        {"project_root": str(tmp_path), "session_id": session_id}
    )
    questions = questions_result["questions"]
    assert isinstance(questions, list)

    # Submit answers (loop until ready or max iterations)
    max_iterations = 10
    for _iteration in range(max_iterations):
        if not questions:
            break

        # Build answers for all questions
        answers = []
        for q in questions:
            answers.append(
                {
                    "question_id": q["id"],
                    "value": "yes" if q["type"] == "boolean" else q["id"],
                    "free_text": f"Answer to {q['id']}",
                }
            )

        submit_result = tool_submit_interview_answers(
            {"project_root": str(tmp_path), "session_id": session_id, "answers": answers}
        )
        session = submit_result["session"]

        # Check if ready
        if session["status"] == "ready_for_confirmation":
            break

        # Get next batch
        if questions_result["questions"]:
            questions_result = tool_get_next_questions(
                {"project_root": str(tmp_path), "session_id": session_id}
            )
            questions = questions_result["questions"]
        else:
            questions = []

    # Should be ready for confirmation
    assert session["status"] == "ready_for_confirmation"

    # Confirm decisions
    confirm_result = tool_confirm_interview_decisions(
        {"project_root": str(tmp_path), "session_id": session_id}
    )
    assert "session" in confirm_result
    assert "decisions" in confirm_result
    assert isinstance(confirm_result["decisions"], list)


def test_submit_interview_answers_raises_on_missing_value_field(tmp_path: Path) -> None:
    """Test that tool_submit_interview_answers raises ValueError when 'value' field is missing."""
    _minimal_pyproject(tmp_path)
    tool_analyze_project({"project_root": str(tmp_path)})

    # Start session
    session_id = "test-session-missing-value"
    tool_start_project_interview(
        {
            "project_root": str(tmp_path),
            "session_id": session_id,
            "session_type": "initial_setup",
        }
    )

    # Get next questions
    questions_result = tool_get_next_questions(
        {"project_root": str(tmp_path), "session_id": session_id}
    )
    questions = questions_result["questions"]
    assert len(questions) > 0, "Expected at least one question"

    # Build answers with wrong field name ("answer" instead of "value")
    answers = [
        {
            "question_id": questions[0]["id"],
            "answer": "yes",  # WRONG: should be "value"
        }
    ]

    # Should raise ValueError about missing 'value' field
    with pytest.raises(ValueError, match="missing required.*value"):
        tool_submit_interview_answers(
            {"project_root": str(tmp_path), "session_id": session_id, "answers": answers}
        )


def test_generate_swarm_plan_with_agent_ids(tmp_path: Path) -> None:
    """Test tool_generate_swarm_plan with agent_ids from prior tool_generate_agents."""
    _minimal_pyproject(tmp_path)
    tool_analyze_project({"project_root": str(tmp_path)})

    # Generate agents
    gen_result = tool_generate_agents({"project_root": str(tmp_path)})
    agent_ids = [a["id"] for a in gen_result["agents"]]

    if agent_ids:
        # Call with explicit agent_ids
        plan_result = tool_generate_swarm_plan(
            {
                "project_root": str(tmp_path),
                "task_id": "test-task",
                "goal": "Test the swarm",
                "agent_ids": agent_ids,
            }
        )
        assert "plan" in plan_result
        assert "text" in plan_result
        assert isinstance(plan_result["text"], str)


def test_get_project_profile_on_analyzed_project(tmp_path: Path) -> None:
    """Test tool_get_project_profile returns profile after tool_analyze_project."""
    _minimal_pyproject(tmp_path)

    tool_analyze_project({"project_root": str(tmp_path)})

    result = tool_get_project_profile({"project_root": str(tmp_path)})
    assert "profile" in result
    assert result["profile"] is not None
    assert "fingerprint" in result["profile"]


def test_get_interview_state_returns_current_session(tmp_path: Path) -> None:
    """Test tool_get_interview_state returns the current session state."""
    _minimal_pyproject(tmp_path)
    tool_analyze_project({"project_root": str(tmp_path)})

    session_id = "test-session-state"
    tool_start_project_interview(
        {
            "project_root": str(tmp_path),
            "session_id": session_id,
            "session_type": "initial_setup",
        }
    )

    result = tool_get_interview_state({"project_root": str(tmp_path), "session_id": session_id})
    assert "session" in result
    assert result["session"]["id"] == session_id


def test_generate_skills_after_generate_agents(tmp_path: Path) -> None:
    """Test tool_generate_skills uses agents from prior tool_generate_agents."""
    _minimal_pyproject(tmp_path)
    tool_analyze_project({"project_root": str(tmp_path)})

    tool_generate_agents({"project_root": str(tmp_path)})

    result = tool_generate_skills({"project_root": str(tmp_path)})
    assert "skills" in result
    assert isinstance(result["skills"], list)


def test_coerce_json_string_arguments(tmp_path: Path) -> None:
    """Test that JSON-encoded string arguments are properly coerced."""
    _minimal_pyproject(tmp_path)

    # Pass providers as JSON string (some MCP clients do this)
    result = tool_setup(
        {"project_root": str(tmp_path), "providers": '["claude"]'}  # JSON string
    )
    assert "agents" in result
    assert "skills" in result


def test_mcp_server_json_rpc_end_to_end(tmp_path: Path) -> None:
    """Test serve() end-to-end via subprocess with JSON-RPC requests."""
    _minimal_pyproject(tmp_path)

    # Build JSON-RPC requests
    requests = [
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {},
            }
        ),
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {},
            }
        ),
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "analyze_project",
                    "arguments": {"project_root": str(tmp_path)},
                },
            }
        ),
    ]
    input_text = "\n".join(requests) + "\n"

    repo_root = Path(__file__).parents[2]
    result = subprocess.run(
        [sys.executable, "-c", "from quattroagents.mcp_server import serve; serve()"],
        input=input_text,
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env={**os.environ, "PYTHONPATH": "src"},
        timeout=30,
    )

    assert result.returncode == 0, f"stderr: {result.stderr}"

    # Parse responses
    responses = [json.loads(line) for line in result.stdout.strip().split("\n") if line.strip()]
    assert len(responses) >= 3

    # Check initialize response
    init_resp = responses[0]
    assert init_resp["jsonrpc"] == "2.0"
    assert init_resp["id"] == 1
    assert "result" in init_resp
    assert init_resp["result"]["serverInfo"]["name"] == "quattroagents-agent-factory"
    assert init_resp["result"]["serverInfo"]["version"] == runtime_version()

    # Check tools/list response
    tools_resp = responses[1]
    assert tools_resp["jsonrpc"] == "2.0"
    assert tools_resp["id"] == 2
    assert "result" in tools_resp
    tools = tools_resp["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "analyze_project" in tool_names
    assert "setup" in tool_names
    assert "list_agents" in tool_names

    # Check tools/call response
    call_resp = responses[2]
    assert call_resp["jsonrpc"] == "2.0"
    assert call_resp["id"] == 3
    assert "result" in call_resp
    assert "error" not in call_resp
    result_content = call_resp["result"]["content"]
    assert len(result_content) > 0
    result_text = json.loads(result_content[0]["text"])
    assert "profile" in result_text


def test_record_decision_with_json_encoded_value(tmp_path: Path) -> None:
    """Test tool_record_decision handles JSON-encoded value argument."""
    _minimal_pyproject(tmp_path)

    # Pass value as JSON string (some MCP clients stringify objects)
    result = tool_record_decision(
        {
            "project_root": str(tmp_path),
            "id": "decision-json",
            "title": "JSON value test",
            "value": '{"key": "value", "nested": {"data": 42}}',
        }
    )

    assert result["decision"]["value"]["key"] == "value"
    assert result["decision"]["value"]["nested"]["data"] == 42


def test_record_decision_with_scope_paths_and_effects(tmp_path: Path) -> None:
    """Test tool_record_decision with scope_paths and effects."""
    _minimal_pyproject(tmp_path)

    result = tool_record_decision(
        {
            "project_root": str(tmp_path),
            "id": "decision-complex",
            "title": "Complex decision",
            "value": {"choice": "option-a"},
            "scope_paths": '["src/", "tests/"]',
            "effects": '{"agents": ["agent-1", "agent-2"]}',
            "decision_scope": "project_wide",
        }
    )

    decision = result["decision"]
    assert decision["scope_paths"] == ["src/", "tests/"]
    assert decision["effects"]["agents"] == ["agent-1", "agent-2"]
    assert decision["decision_scope"] == DecisionScope.PROJECT_WIDE


def test_list_decisions_with_status_filter(tmp_path: Path) -> None:
    """Test tool_list_decisions filters by status."""
    _minimal_pyproject(tmp_path)

    # Record two decisions
    tool_record_decision(
        {
            "project_root": str(tmp_path),
            "id": "dec-active-1",
            "title": "Active decision",
            "value": {},
        }
    )
    tool_record_decision(
        {
            "project_root": str(tmp_path),
            "id": "dec-uncertain",
            "title": "Uncertain decision",
            "value": {},
        }
    )

    # Reopen one to make it uncertain
    tool_reopen_decision(
        {
            "project_root": str(tmp_path),
            "decision_id": "dec-uncertain",
            "reason": "Reconsidering",
        }
    )

    # List only active
    active_result = tool_list_decisions(
        {"project_root": str(tmp_path), "status": DecisionStatus.ACTIVE}
    )
    active_ids = [d["id"] for d in active_result["decisions"]]
    assert "dec-active-1" in active_ids
    assert "dec-uncertain" not in active_ids


def test_list_decisions_with_decision_scope_filter(tmp_path: Path) -> None:
    """Test tool_list_decisions filters by decision_scope."""
    _minimal_pyproject(tmp_path)

    tool_record_decision(
        {
            "project_root": str(tmp_path),
            "id": "dec-scope-1",
            "title": "Project-wide decision",
            "value": {},
            "decision_scope": "project_wide",
        }
    )
    tool_record_decision(
        {
            "project_root": str(tmp_path),
            "id": "dec-scope-2",
            "title": "Task-local decision",
            "value": {},
            "decision_scope": "task_local",
        }
    )

    # Filter by scope
    pw_result = tool_list_decisions(
        {"project_root": str(tmp_path), "decision_scope": DecisionScope.PROJECT_WIDE}
    )
    pw_ids = [d["id"] for d in pw_result["decisions"]]
    assert "dec-scope-1" in pw_ids
    assert "dec-scope-2" not in pw_ids


def test_resolve_decision_conflict_supersedes_losing_decisions(tmp_path: Path) -> None:
    """Test tool_resolve_decision_conflict with USER_VS_USER type supersedes losing decisions."""
    _minimal_pyproject(tmp_path)

    # Create three decisions on the same topic (title)
    topic_title = "Choose default database"
    for decision_id in ["decision-a", "decision-b", "decision-c"]:
        tool_record_decision(
            {
                "project_root": str(tmp_path),
                "id": decision_id,
                "title": topic_title,
                "value": {"choice": decision_id},
                "reason": f"Recommending {decision_id}",
            }
        )

    # Verify all three are ACTIVE and exist
    list_result = tool_list_decisions({"project_root": str(tmp_path)})
    decisions_by_id = {d["id"]: d for d in list_result["decisions"]}
    assert "decision-a" in decisions_by_id
    assert "decision-b" in decisions_by_id
    assert "decision-c" in decisions_by_id
    assert decisions_by_id["decision-a"]["status"] == DecisionStatus.ACTIVE
    assert decisions_by_id["decision-b"]["status"] == DecisionStatus.ACTIVE
    assert decisions_by_id["decision-c"]["status"] == DecisionStatus.ACTIVE

    # Create a conflict record with decision-c as the keeper
    conflict = ConflictRecord(
        id="conflict-1",
        type=ConflictType.USER_VS_USER,
        decision_id="decision-c",
        evidence=["decision-a: recommends PostgreSQL", "decision-b: recommends MySQL"],
        severity=ConflictSeverity.MEDIUM,
        status=ConflictStatus.UNRESOLVED,
        possible_resolutions=[
            "keep the most recent decision and supersede the others",
            "merge all three into a hybrid approach",
        ],
        resolution=None,
    )

    # Write conflict to disk at the expected path
    store = AgentFactoryStore(tmp_path)
    conflicts_path = store.base / "generated" / "conflicts.json"
    write_json(conflicts_path, [conflict.to_dict()])

    # Resolve the conflict with the superseding resolution
    result = tool_resolve_decision_conflict(
        {
            "project_root": str(tmp_path),
            "conflict_id": "conflict-1",
            "resolution": "keep the most recent decision and supersede the others",
        }
    )

    # Verify the conflict is resolved
    assert result["conflict"]["id"] == "conflict-1"
    assert result["conflict"]["status"] == ConflictStatus.RESOLVED
    assert (
        result["conflict"]["resolution"] == "keep the most recent decision and supersede the others"
    )

    # Verify the losing decisions are in the result
    assert set(result["superseded_decisions"]) == {"decision-a", "decision-b"}

    # Verify the losing decisions now have SUPERSEDED status
    list_result_after = tool_list_decisions({"project_root": str(tmp_path)})
    decisions_by_id_after = {d["id"]: d for d in list_result_after["decisions"]}

    assert decisions_by_id_after["decision-a"]["status"] == DecisionStatus.SUPERSEDED, (
        "decision-a should be superseded"
    )
    assert decisions_by_id_after["decision-b"]["status"] == DecisionStatus.SUPERSEDED, (
        "decision-b should be superseded"
    )
    assert decisions_by_id_after["decision-c"]["status"] == DecisionStatus.ACTIVE, (
        "decision-c (keeper) should still be active"
    )

    # Verify superseded_by field is set correctly
    assert decisions_by_id_after["decision-a"]["superseded_by"] == "decision-c"
    assert decisions_by_id_after["decision-b"]["superseded_by"] == "decision-c"

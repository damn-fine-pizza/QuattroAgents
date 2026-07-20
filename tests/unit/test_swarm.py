import json

import pytest

from quattroagents.core.swarm import (
    build_interview_brief,
    build_swarm_plan,
    conduct_interview,
    render_confirmed_interview_markdown,
    render_interview_brief_markdown,
    render_swarm_plan_markdown,
)


def task() -> dict[str, object]:
    return {
        "id": "TASK-001",
        "milestone": "0.2.0",
        "payload": {
            "objective": "Add a bounded swarm planner",
            "requirements": [
                {"id": "REQ-1", "text": "Plan independent work"},
                {"id": "REQ-2", "text": "Review output"},
            ],
            "acceptance_commands": ["pytest", "ruff check ."],
            "interview": {
                "schema_version": 1,
                "status": "confirmed",
                "answers": {
                    "INTENT-1": "Deliver a bounded swarm plan.",
                    "INTENT-2": "Only local planning is in scope.",
                    "INTENT-3": "Unit and integration tests pass.",
                    "INTENT-4": "Do not change the protected kernel.",
                    "INTENT-5": "Review runs after independent documentation and test work.",
                },
                "analysis": {"languages": ["python"]},
            },
            "swarm_work_items": [
                {
                    "id": "docs",
                    "objective": "Document the planner",
                    "requirements": ["REQ-1"],
                    "allowed_files": ["README.md"],
                    "context_refs": ["docs/communication-protocol.md"],
                    "depends_on": [],
                },
                {
                    "id": "tests",
                    "objective": "Test the planner",
                    "requirements": ["REQ-2"],
                    "allowed_files": ["tests/test_swarm.py"],
                    "context_refs": ["src/quattroagents/core/swarm.py"],
                    "depends_on": [],
                },
            ],
        },
    }


def test_swarm_plan_groups_independent_non_overlapping_workers() -> None:
    plan = build_swarm_plan(task(), 2)

    assert plan["mode"] == "plan_only"
    assert plan["scheduling"] == {
        "maximum_parallel_workers": 2,
    }
    assert plan["waves"][0]["parallel"] is True
    assert [worker["id"] for worker in plan["waves"][0]["workers"]] == ["docs", "tests"]
    assert plan["waves"][0]["workers"][0]["context_summary"]["context_refs"] == [
        "docs/communication-protocol.md"
    ]
    assert plan["interview"]["analysis"] == {"languages": ["python"]}
    assert plan["waves"][0]["workers"][0]["context_summary"]["user_intent"]["INTENT-1"] == (
        "Deliver a bounded swarm plan."
    )
    packet = plan["waves"][0]["workers"][0]
    assert set(packet) >= {
        "id",
        "role",
        "objective",
        "requirements",
        "allowed_files",
        "forbidden_changes",
        "context_refs",
        "acceptance_commands",
        "required_evidence",
        "depends_on",
        "risk",
    }
    assert packet["forbidden_changes"] == [
        "Do not launch agents or subagents.",
        "Do not modify files outside allowed_files.",
    ]
    assert packet["required_evidence"] == [
        "Acceptance command results.",
        "Changed-file list limited to allowed_files.",
    ]
    markdown = render_swarm_plan_markdown(plan).lower()
    assert "no agent or subagent is launched" in markdown
    assert "maximum parallel workers: 2" in markdown
    assert "codex" not in json.dumps(plan).lower()
    assert "codex" not in markdown


def test_swarm_plan_serializes_overlapping_files_and_rejects_cycles() -> None:
    overlapping = task()
    payload = overlapping["payload"]
    assert isinstance(payload, dict)
    items = payload["swarm_work_items"]
    assert isinstance(items, list)
    second = items[1]
    assert isinstance(second, dict)
    second["allowed_files"] = ["README.md"]

    plan = build_swarm_plan(overlapping, 2)

    assert len(plan["waves"]) == 2
    first = items[0]
    assert isinstance(first, dict)
    first["allowed_files"] = ["src"]
    second["allowed_files"] = ["src/quattroagents/core/swarm.py"]
    assert len(build_swarm_plan(overlapping, 2)["waves"]) == 2
    cyclic = task()
    cyclic_payload = cyclic["payload"]
    assert isinstance(cyclic_payload, dict)
    cyclic_items = cyclic_payload["swarm_work_items"]
    assert isinstance(cyclic_items, list)
    first = cyclic_items[0]
    second = cyclic_items[1]
    assert isinstance(first, dict) and isinstance(second, dict)
    first["depends_on"] = ["tests"]
    second["depends_on"] = ["docs"]
    with pytest.raises(ValueError, match="cycle"):
        build_swarm_plan(cyclic, 2)

    unknown_requirement = task()
    unknown_payload = unknown_requirement["payload"]
    assert isinstance(unknown_payload, dict)
    unknown_items = unknown_payload["swarm_work_items"]
    assert isinstance(unknown_items, list)
    unknown_first = unknown_items[0]
    assert isinstance(unknown_first, dict)
    unknown_first["requirements"] = ["REQ-404"]
    with pytest.raises(ValueError, match="unknown swarm requirement"):
        build_swarm_plan(unknown_requirement, 2)


def test_swarm_plan_uses_injected_scheduling_limit() -> None:
    configured = task()
    payload = configured["payload"]
    assert isinstance(payload, dict)
    payload["swarm_work_items"] = [
        {
            "id": identifier,
            "objective": f"Do {identifier}",
            "requirements": ["REQ-1"],
            "allowed_files": [f"{identifier}.md"],
            "context_refs": ["src/quattroagents/core/swarm.py"],
            "depends_on": [],
        }
        for identifier in ("one", "two", "three", "four")
    ]

    plan = build_swarm_plan(configured, 3)

    assert plan["scheduling"]["maximum_parallel_workers"] == 3
    assert [[worker["id"] for worker in wave["workers"]] for wave in plan["waves"]] == [
        ["four", "one", "three"],
        ["two"],
    ]
    with pytest.raises(ValueError, match="positive integer"):
        build_swarm_plan(configured, 0)


def test_brownfield_interview_requires_human_intent_before_planning() -> None:
    brief = build_interview_brief(
        {"languages": ["python"], "ci": [".github/workflows/ci.yml"], "codex": True, "claude": True}
    )

    assert brief["stage"] == "intent_before_planning"
    assert [item["id"] for item in brief["questions"]] == [
        "INTENT-1",
        "INTENT-2",
        "INTENT-3",
        "INTENT-4",
        "INTENT-5",
    ]
    assert "before creating worker packets" in render_interview_brief_markdown(brief).lower()


def test_confirmed_interview_is_required_and_rendered_for_task_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    brief = build_interview_brief(
        {"languages": ["python"], "ci": [], "codex": True, "claude": False}
    )
    responses = iter(
        [
            "Deliver a report.",
            "Only documentation.",
            "Tests pass.",
            "No protected files.",
            "No parallel work.",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda: next(responses))

    record = conduct_interview(brief)

    assert record["status"] == "confirmed"
    assert '"interview"' in render_confirmed_interview_markdown(record)
    missing = task()
    payload = missing["payload"]
    assert isinstance(payload, dict)
    payload.pop("interview")
    with pytest.raises(ValueError, match="confirmed user interview"):
        build_swarm_plan(missing, 1)

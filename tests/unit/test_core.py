from pathlib import Path

from quattroagents.core.configuration import merge_json, safe_path
from quattroagents.core.gates import allow_integration, allow_worker
from quattroagents.core.models import Risk, TaskContract, Tier
from quattroagents.core.routing import route


def contract() -> TaskContract:
    return TaskContract(
        "TASK-001",
        "test",
        Risk.LOW,
        [{"id": "REQ-1", "text": "works"}],
        ["a.py"],
        acceptance_commands=["pytest"],
    )


def test_small_routing_and_gate() -> None:
    assert route(contract()) is Tier.SMALL
    assert allow_worker(contract(), Tier.SMALL, ["a.py"])[0]


def test_protected_rejected_for_small() -> None:
    assert not allow_worker(contract(), Tier.SMALL, ["src/quattroagents/core/routing.py"])[0]


def test_protected_integration_requires_explicit_human_approval() -> None:
    protected = ["src/quattroagents/control_plane/database.py"]
    assert allow_integration(["docs/guide.md"], False) == (True, "allowed")
    assert allow_integration(protected, False) == (
        False,
        "protected kernel integration requires explicit human approval",
    )
    assert allow_integration(protected, True) == (True, "allowed")


def test_task_contract_preserves_optional_milestone() -> None:
    assert (
        TaskContract(
            "TASK-002",
            "test",
            Risk.LOW,
            [{"id": "REQ-1", "text": "works"}],
            milestone="0.2.0",
        ).to_dict()["milestone"]
        == "0.2.0"
    )


def test_merge_and_path_validation(tmp_path: Path) -> None:
    assert merge_json({"a": {"x": 1}}, {"a": {"y": 2}}) == {"a": {"x": 1, "y": 2}}
    assert safe_path(tmp_path, "a").parent == tmp_path.resolve()
    try:
        safe_path(tmp_path, "../escape")
    except ValueError:
        pass
    else:
        raise AssertionError("must reject traversal")

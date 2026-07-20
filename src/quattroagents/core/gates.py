from __future__ import annotations

from pathlib import Path

from .models import Risk, TaskContract, Tier

PROTECTED = [
    "src/quattroagents/core/routing.py",
    "src/quattroagents/core/gates.py",
    "src/quattroagents/core/configuration.py",
    "src/quattroagents/control_plane/database.py",
    "src/quattroagents/control_plane/tasks.py",
    "src/quattroagents/control_plane/leases.py",
    "src/quattroagents/validation/",
    ".quattroagents/model-routing.json",
    ".quattroagents/quality-gates.json",
    ".quattroagents/fleet.json",
]


def requires_human_approval(contract: TaskContract, changed: list[str]) -> bool:
    return contract.risk is Risk.HIGH or any(
        any(p.startswith(prefix) for prefix in PROTECTED) for p in changed
    )


def allow_worker(contract: TaskContract, tier: Tier, changed: list[str]) -> tuple[bool, str]:
    if tier is Tier.SMALL and requires_human_approval(contract, changed):
        return (
            False,
            "protected kernel requires medium+ implementation, independent review, and human approval",
        )
    if tier is Tier.SMALL and not contract.ready_for_small():
        return False, "small worker requires a complete task contract"
    return True, "allowed"


def allow_integration(changed: list[str], human_approved: bool) -> tuple[bool, str]:
    """Require an explicit human approval before integrating protected changes."""
    protected = any(any(path.startswith(prefix) for prefix in PROTECTED) for path in changed)
    if protected and not human_approved:
        return False, "protected kernel integration requires explicit human approval"
    return True, "allowed"


def path_allowed(root: Path, path: str) -> bool:
    candidate = (root / path).resolve()
    return candidate == root.resolve() or root.resolve() in candidate.parents

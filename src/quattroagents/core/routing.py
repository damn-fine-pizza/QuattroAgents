from __future__ import annotations

from .models import Risk, TaskContract, Tier

FLEET = [
    ("orchestrator", Tier.MEDIUM),
    ("repository-scout", Tier.SMALL),
    ("bounded-worker", Tier.SMALL),
    ("test-worker", Tier.SMALL),
    ("fast-reviewer", Tier.SMALL),
    ("semantic-reviewer", Tier.MEDIUM),
    ("architecture-adjudicator", Tier.LARGE),
]


def fleet(profile: str) -> list[dict[str, object]]:
    return [
        {"name": name, "tier": tier.value, "enabled": tier is not Tier.LONG_HORIZON}
        for name, tier in FLEET
    ]


def route(contract: TaskContract) -> Tier:
    if contract.risk is Risk.HIGH:
        return Tier.LARGE
    if contract.risk is Risk.MEDIUM or not contract.ready_for_small():
        return Tier.MEDIUM
    return Tier.SMALL


def routing(profile: str) -> dict[str, object]:
    parallel = {"economy": [1, 2], "balanced": [2, 4], "quality": [1, 2]}.get(profile, [1, 2])
    return {
        "schema_version": 1,
        "tiers": {tier.value: {"manual_only": tier is Tier.LONG_HORIZON} for tier in Tier},
        "parallelism": parallel,
        "retry_limit": 1,
    }

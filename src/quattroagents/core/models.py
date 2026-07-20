from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Tier(StrEnum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    LONG_HORIZON = "long_horizon"


class Risk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class TaskContract:
    task_id: str
    objective: str
    risk: Risk
    requirements: list[dict[str, str]]
    allowed_files: list[str] = field(default_factory=list)
    forbidden_changes: list[str] = field(default_factory=list)
    context_refs: list[str] = field(default_factory=list)
    reference_patterns: list[str] = field(default_factory=list)
    acceptance_commands: list[str] = field(default_factory=list)
    required_evidence: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    escalate_when: list[str] = field(default_factory=list)
    schema_version: int = 1

    def ready_for_small(self) -> bool:
        return bool(
            self.objective and self.requirements and self.allowed_files and self.acceptance_commands
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResultEnvelope:
    task_id: str
    status: str
    producer: dict[str, str]
    summary: str
    requirements: dict[str, str]
    artifacts: list[str] = field(default_factory=list)
    evidence: dict[str, str] = field(default_factory=dict)
    facts: list[str] = field(default_factory=list)
    inferences: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    confidence: float = 0.0
    escalation: dict[str, Any] = field(default_factory=lambda: {"required": False, "reason": None})
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

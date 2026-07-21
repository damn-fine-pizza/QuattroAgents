"""Local, file-based persistence for the Project Agent Factory.

Everything lives under `<project_root>/.agent-factory/` as human-inspectable
JSON (not YAML: this project deliberately keeps zero runtime dependencies,
and JSON is exactly as inspectable/editable by hand). Layout:

    .agent-factory/
    ├── project-profile.json          latest ProjectProfile snapshot
    ├── history/
    │   └── <UTC-ISO8601>-analysis.json   timestamped ProjectProfile snapshots, for change detection
    ├── decisions/
    │   └── <decision-id>.json        one file per Decision, supersede chain via supersedes/superseded_by
    ├── sessions/
    │   └── <session-id>.json         one file per InterviewSession (embeds its gaps/questions/answers)
    ├── generated/
    │   └── manifest.json             last synthesized {agents, skills, swarm} internal manifest
    └── overrides/
        └── <sanitized-relative-path>.json   last-generated-content hash per rendered output file,
                                              used to detect manual edits before the next regeneration

Ported, generic helpers below (`safe_path`, `write_json`, `read_json`) follow the same pattern
already proven in the pre-rewrite `core/configuration.py` module.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .domain import (
    Decision,
    DecisionScope,
    DecisionStatus,
    InterviewSession,
    ProjectProfile,
    SessionType,
)

STORE_DIR_NAME = ".agent-factory"


def store_dir(root: Path) -> Path:
    return root / STORE_DIR_NAME


def safe_path(root: Path, candidate: Path) -> Path:
    """Resolve candidate and raise ValueError if it escapes root (symlink-safe)."""
    resolved_root = root.resolve()
    resolved = candidate.resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError(f"path escapes project root: {candidate}")
    return resolved


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sanitize_relative_path(relative_path: str) -> str:
    return relative_path.replace("/", "__")


# --------------------------------------------------------------------------
# Override-aware generated-file writing
# --------------------------------------------------------------------------


@dataclass
class WriteResult:
    relative_path: str
    status: str  # "written" | "unchanged" | "conflict"
    previous_content: str | None = None
    attempted_content: str | None = None


class GeneratedFileGuard:
    """Writes generated files without silently clobbering manual edits.

    Strategy: "generated base + manual overrides" (see docs). Before writing,
    compares the on-disk file's hash against the hash recorded at the time it
    was last (re)generated. If they match, the file is safe to overwrite. If
    they differ, a human edited it since — write is refused and a conflict is
    reported instead of merging or overwriting silently.
    """

    def __init__(self, root: Path):
        self.root = root
        self.overrides_dir = store_dir(root) / "overrides"

    def _record_path(self, relative_path: str) -> Path:
        return self.overrides_dir / f"{_sanitize_relative_path(relative_path)}.json"

    def write(self, relative_path: str, content: str) -> WriteResult:
        target = safe_path(self.root, self.root / relative_path)
        record_path = self._record_path(relative_path)
        record = read_json(record_path, None)
        new_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        if target.exists():
            on_disk = target.read_text(encoding="utf-8")
            on_disk_hash = hashlib.sha256(on_disk.encode("utf-8")).hexdigest()
        else:
            on_disk = None
            on_disk_hash = None

        if (
            record is not None
            and on_disk_hash is not None
            and on_disk_hash != record["last_generated_hash"]
        ):
            if on_disk_hash == new_hash:
                return WriteResult(relative_path=relative_path, status="unchanged")
            return WriteResult(
                relative_path=relative_path,
                status="conflict",
                previous_content=on_disk,
                attempted_content=content,
            )

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        write_json(
            record_path,
            {"path": relative_path, "last_generated_hash": new_hash, "generated_at": _utc_now()},
        )
        return WriteResult(relative_path=relative_path, status="written")


# --------------------------------------------------------------------------
# Store
# --------------------------------------------------------------------------


class AgentFactoryStore:
    def __init__(self, root: Path):
        self.root = root
        self.base = store_dir(root)

    # -- project profile -----------------------------------------------

    def save_profile(self, profile: ProjectProfile) -> None:
        write_json(self.base / "project-profile.json", profile.to_dict())
        self._snapshot_profile_history(profile)

    def load_profile(self) -> ProjectProfile | None:
        data = read_json(self.base / "project-profile.json", None)
        return ProjectProfile.from_dict(data) if data is not None else None

    def _snapshot_profile_history(self, profile: ProjectProfile) -> Path:
        stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S-%f")
        path = self.base / "history" / f"{stamp}Z-analysis.json"
        write_json(path, profile.to_dict())
        return path

    def profile_history(self, limit: int = 5) -> list[ProjectProfile]:
        directory = self.base / "history"
        if not directory.exists():
            return []
        paths = sorted(directory.glob("*-analysis.json"), reverse=True)
        return [
            ProjectProfile.from_dict(json.loads(p.read_text(encoding="utf-8")))
            for p in paths[:limit]
        ]

    # -- decisions --------------------------------------------------------

    def save_decision(self, decision: Decision) -> None:
        decision.updated_at = decision.updated_at or _utc_now()
        write_json(self.base / "decisions" / f"{decision.id}.json", decision.to_dict())

    def load_decision(self, decision_id: str) -> Decision | None:
        data = read_json(self.base / "decisions" / f"{decision_id}.json", None)
        return Decision.from_dict(data) if data is not None else None

    def list_decisions(
        self,
        *,
        status: DecisionStatus | None = None,
        decision_scope: DecisionScope | None = None,
    ) -> list[Decision]:
        directory = self.base / "decisions"
        if not directory.exists():
            return []
        decisions = [
            Decision.from_dict(json.loads(p.read_text(encoding="utf-8")))
            for p in sorted(directory.glob("*.json"))
        ]
        if status is not None:
            decisions = [d for d in decisions if d.status == status]
        if decision_scope is not None:
            decisions = [d for d in decisions if d.decision_scope == decision_scope]
        return decisions

    def supersede_decision(self, old_id: str, new_decision: Decision) -> None:
        old = self.load_decision(old_id)
        if old is None:
            raise KeyError(f"unknown decision: {old_id}")
        now = _utc_now()
        old.status = DecisionStatus.SUPERSEDED
        old.superseded_by = new_decision.id
        old.updated_at = now
        new_decision.supersedes = old_id
        new_decision.updated_at = new_decision.updated_at or now
        self.save_decision(old)
        self.save_decision(new_decision)

    def supersede_by_existing(
        self, losing_ids: list[str], keeper_id: str, reason: str
    ) -> list[Decision]:
        """Mark each losing decision SUPERSEDED by an already-existing keeper decision.

        Unlike `supersede_decision` (which links a brand-new replacement
        decision to the one it replaces), this is for conflict resolution:
        several existing decisions lose to another existing one, with no new
        decision created. `Decision.supersedes` only holds a single id, so it
        is intentionally left untouched on the keeper — only each loser's
        `status`/`superseded_by` is set.
        """
        now = _utc_now()
        losers: list[Decision] = []
        for loser_id in losing_ids:
            if loser_id == keeper_id:
                continue
            loser = self.load_decision(loser_id)
            if loser is None:
                continue
            loser.status = DecisionStatus.SUPERSEDED
            loser.superseded_by = keeper_id
            loser.reason = reason
            loser.updated_at = now
            self.save_decision(loser)
            losers.append(loser)
        return losers

    def reopen_decision(self, decision_id: str, reason: str) -> Decision:
        decision = self.load_decision(decision_id)
        if decision is None:
            raise KeyError(f"unknown decision: {decision_id}")
        decision.status = DecisionStatus.UNCERTAIN
        decision.reason = reason
        decision.updated_at = _utc_now()
        self.save_decision(decision)
        return decision

    # -- interview sessions -------------------------------------------

    def save_session(self, session: InterviewSession) -> None:
        write_json(self.base / "sessions" / f"{session.id}.json", session.to_dict())

    def load_session(self, session_id: str) -> InterviewSession | None:
        data = read_json(self.base / "sessions" / f"{session_id}.json", None)
        return InterviewSession.from_dict(data) if data is not None else None

    def list_sessions(
        self, *, session_type: SessionType | None = None, limit: int = 10
    ) -> list[InterviewSession]:
        directory = self.base / "sessions"
        if not directory.exists():
            return []
        paths = sorted(directory.glob("*.json"), reverse=True)
        sessions = [
            InterviewSession.from_dict(json.loads(p.read_text(encoding="utf-8"))) for p in paths
        ]
        if session_type is not None:
            sessions = [s for s in sessions if s.type == session_type]
        return sessions[:limit]

    def latest_session(self, *, session_type: SessionType | None = None) -> InterviewSession | None:
        sessions = self.list_sessions(session_type=session_type, limit=1)
        return sessions[0] if sessions else None

    # -- generated manifest ---------------------------------------------

    def save_generated_manifest(self, manifest: dict[str, Any]) -> None:
        write_json(self.base / "generated" / "manifest.json", manifest)

    def load_generated_manifest(self) -> dict[str, Any] | None:
        data: dict[str, Any] | None = read_json(self.base / "generated" / "manifest.json", None)
        return data

    # -- generated files (override-aware) --------------------------------

    def file_guard(self) -> GeneratedFileGuard:
        return GeneratedFileGuard(self.root)

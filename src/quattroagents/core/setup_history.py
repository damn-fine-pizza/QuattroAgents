from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .configuration import state_dir

_SUBDIR = "setup"


def _history_dir(root: Path) -> Path:
    return state_dir(root) / "decisions" / _SUBDIR


class SetupHistoryStore:
    """Append-only, file-based history of `setup` analysis/interview/manifest records."""

    def append(
        self,
        root: Path,
        analysis: dict[str, Any],
        interview: dict[str, Any],
        manifest: dict[str, Any],
    ) -> dict[str, Any]:
        directory = _history_dir(root)
        directory.mkdir(parents=True, exist_ok=True)
        previous = self.latest(root)
        record = {
            "schema_version": 1,
            "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "analysis": analysis,
            "interview": interview,
            "manifest": manifest,
            "previous_record": (
                f"{_SUBDIR}/{previous['_filename']}" if previous is not None else None
            ),
        }
        stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S-%f")
        filename = f"{stamp}Z.json"
        path = directory / filename
        counter = 1
        while path.exists():
            filename = f"{stamp}-{counter:04d}Z.json"
            path = directory / filename
            counter += 1
        path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {**record, "_filename": filename}

    def recent(self, root: Path, limit: int = 5) -> list[dict[str, Any]]:
        directory = _history_dir(root)
        if not directory.exists():
            return []
        paths = sorted(directory.glob("*.json"), reverse=True)
        records = []
        for path in paths[:limit]:
            record = json.loads(path.read_text(encoding="utf-8"))
            records.append({**record, "_filename": path.name})
        return records

    def latest(self, root: Path) -> dict[str, Any] | None:
        records = self.recent(root, limit=1)
        return records[0] if records else None

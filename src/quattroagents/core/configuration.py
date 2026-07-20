from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

STATE = ".quattroagents"
STATE_FILES: dict[str, Any] = {
    "project-profile.json": {"schema_version": 1, "profile": "economy", "providers": []},
    "capability-map.json": {"schema_version": 1, "capabilities": {}},
    "fleet.json": {"schema_version": 1, "agents": []},
    "model-routing.json": {"schema_version": 1, "tiers": {}},
    "quality-gates.json": {"schema_version": 1, "protected_paths": []},
    "context-manifest.json": {"schema_version": 1, "entries": []},
}


def state_dir(root: Path) -> Path:
    return root / STATE


def safe_path(root: Path, candidate: str | Path) -> Path:
    resolved_root = root.resolve()
    resolved = (root / candidate).resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError("path escapes project root")
    return resolved


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def backup(root: Path, path: Path) -> Path | None:
    if not path.exists():
        return None
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = state_dir(root) / "backups" / stamp / path.relative_to(root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, destination)
    return destination


def merge_json(existing: Any, generated: Any) -> Any:
    if isinstance(existing, dict) and isinstance(generated, dict):
        result = dict(existing)
        for key, value in generated.items():
            result[key] = merge_json(result[key], value) if key in result else value
        return result
    return generated


def initialise(root: Path, profile: str, providers: list[str]) -> None:
    state = state_dir(root)
    for name in (
        "tasks",
        "results",
        "evidence",
        "artifacts",
        "decisions",
        "metrics",
        "runtime",
        "backups",
    ):
        (state / name).mkdir(parents=True, exist_ok=True)
    for name, value in STATE_FILES.items():
        path = state / name
        data = merge_json(read_json(path, {}), value)
        if name == "project-profile.json":
            data.update({"profile": profile, "providers": providers})
        write_json(path, data)

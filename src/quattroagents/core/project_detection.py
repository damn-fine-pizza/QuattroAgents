from __future__ import annotations

from pathlib import Path


def detect(root: Path) -> dict[str, object]:
    markers = {
        "python": ["pyproject.toml", "setup.py", "requirements.txt"],
        "node": ["package.json"],
        "rust": ["Cargo.toml"],
        "go": ["go.mod"],
        "cpp": ["CMakeLists.txt", "meson.build"],
    }
    languages = [name for name, files in markers.items() if any((root / f).exists() for f in files)]
    return {
        "root": str(root),
        "languages": languages,
        "git": (root / ".git").exists(),
        "ci": [str(p.relative_to(root)) for p in root.glob(".github/workflows/*")],
        "codex": (root / ".codex").exists(),
        "claude": (root / ".claude").exists(),
    }

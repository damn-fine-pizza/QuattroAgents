"""QuattroAgents: a Project Agent Factory for tailored Claude/Codex agents and skills."""

import subprocess
from pathlib import Path

__version__ = "0.7.2"


def runtime_identity() -> tuple[str | None, bool]:
    """Return the source revision and whether the checkout has local changes."""
    root = Path(__file__).resolve().parents[2]
    try:
        revision = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short=12", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "-C", str(root), "status", "--porcelain"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
    except (OSError, subprocess.CalledProcessError):
        return None, False
    return revision or None, dirty


def runtime_version() -> str:
    """Return a SemVer-compatible package version with local source identity."""
    revision, dirty = runtime_identity()
    if revision is None:
        return __version__
    return f"{__version__}+g{revision}" + (".dirty" if dirty else "")

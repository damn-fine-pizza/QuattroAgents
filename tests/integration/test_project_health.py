import os
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "project-health.sh"


def _write_fake_python(root: Path) -> Path:
    python = root / ".venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_text(
        "#!/usr/bin/env sh\n"
        "printf '%s\\n' \"$*\" >> \"$HEALTH_LOG\"\n"
        "case \"$*\" in\n"
        "  *doctor*) exit \"${DOCTOR_EXIT:-0}\" ;;\n"
        "  *validate*) exit \"${VALIDATE_EXIT:-0}\" ;;\n"
        "esac\n"
    )
    python.chmod(0o755)
    return python


def _run(root: Path, log: Path, **environment: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(SCRIPT), str(root)],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "HEALTH_LOG": str(log), **environment},
    )


def test_project_health_runs_doctor_then_validate_for_the_requested_root(tmp_path: Path) -> None:
    _write_fake_python(tmp_path)
    log = tmp_path / "health.log"

    result = _run(tmp_path, log)

    assert result.returncode == 0
    assert log.read_text().splitlines() == [
        f"-m quattroagents doctor --project {tmp_path} --format json",
        f"-m quattroagents validate --project {tmp_path} --format json",
    ]


def test_project_health_stops_when_doctor_fails(tmp_path: Path) -> None:
    _write_fake_python(tmp_path)
    log = tmp_path / "health.log"

    result = _run(tmp_path, log, DOCTOR_EXIT="23")

    assert result.returncode == 23
    assert log.read_text().splitlines() == [
        f"-m quattroagents doctor --project {tmp_path} --format json"
    ]


def test_project_health_returns_validate_failure(tmp_path: Path) -> None:
    _write_fake_python(tmp_path)
    log = tmp_path / "health.log"

    result = _run(tmp_path, log, VALIDATE_EXIT="24")

    assert result.returncode == 24
    assert log.read_text().splitlines() == [
        f"-m quattroagents doctor --project {tmp_path} --format json",
        f"-m quattroagents validate --project {tmp_path} --format json",
    ]

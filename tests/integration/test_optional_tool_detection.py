import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]


@pytest.mark.parametrize(
    ("script_name", "command_name", "missing_message"),
    [
        ("detect-rtk.sh", "rtk", "RTK not installed; optional integration skipped."),
        (
            "detect-codebase-memory-mcp.sh",
            "codebase-memory-mcp",
            "Codebase Memory MCP not installed; optional integration skipped.",
        ),
    ],
)
def test_optional_tool_detection_is_rerunnable(
    tmp_path: Path,
    script_name: str,
    command_name: str,
    missing_message: str,
) -> None:
    script = ROOT / "scripts" / script_name
    absent = subprocess.run(
        ["/bin/sh", str(script)],
        capture_output=True,
        check=True,
        env={"PATH": "/missing"},
        text=True,
    )
    assert absent.stdout.strip() == missing_message

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_command = fake_bin / command_name
    fake_command.write_text("#!/usr/bin/env sh\necho optional-tool 9.9.9\n")
    fake_command.chmod(0o755)
    present = subprocess.run(
        ["/bin/sh", str(script)],
        capture_output=True,
        check=True,
        env={**os.environ, "PATH": f"{fake_bin}:/usr/bin:/bin"},
        text=True,
    )
    assert present.stdout.strip() == "optional-tool 9.9.9"

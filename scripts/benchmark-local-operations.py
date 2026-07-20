#!/usr/bin/env python3
"""Record raw, offline observations for two local command conditions.

This harness deliberately does not calculate a speedup or any other inferred
benefit.  A non-zero command result is recorded like every other observation,
then the remaining observations continue to run.
"""

from __future__ import annotations

import argparse
import json
import platform
import shlex
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path


def parse_command(value: str) -> list[str]:
    """Parse one local command without invoking a shell."""
    command = shlex.split(value)
    if not command:
        raise argparse.ArgumentTypeError("command must contain at least one word")
    return command


def source_commit(project_root: Path) -> str:
    """Return the checked-out revision, or a stable local fallback."""
    result = subprocess.run(
        ["git", "-C", str(project_root), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
    )
    if result.returncode == 0:
        return result.stdout.decode("utf-8", errors="replace").strip()
    return "unknown"


def runtime_identity() -> dict[str, str]:
    """Describe the Python runtime that executes the local harness."""
    return {
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
    }


def run_observation(
    condition: str,
    command: Sequence[str],
    iteration: int,
    project_root: Path,
    commit: str,
    runtime: dict[str, str],
) -> dict[str, object]:
    """Execute a local command once and retain its raw outcome."""
    started = time.perf_counter_ns()
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            cwd=project_root,
        )
        exit_status = completed.returncode
        stdout_bytes = len(completed.stdout)
        stderr_bytes = len(completed.stderr)
    except OSError as error:
        exit_status = None
        stdout_bytes = 0
        stderr_bytes = len(str(error).encode("utf-8"))
    elapsed_duration_ns = time.perf_counter_ns() - started
    return {
        "command": list(command),
        "command_word_count": len(command),
        "condition": condition,
        "elapsed_duration_ns": elapsed_duration_ns,
        "elapsed_duration_seconds": elapsed_duration_ns / 1_000_000_000,
        "exit_status": exit_status,
        "iteration": iteration,
        "runtime_identity": runtime,
        "source_commit": commit,
        "stderr_bytes": stderr_bytes,
        "stdout_bytes": stdout_bytes,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline-command",
        required=True,
        type=parse_command,
        help="Quoted local baseline command; it is parsed with shlex and never run in a shell.",
    )
    parser.add_argument(
        "--assisted-command",
        required=True,
        type=parse_command,
        help="Quoted local assisted command; it is parsed with shlex and never run in a shell.",
    )
    parser.add_argument(
        "--iterations", type=int, default=3, help="Paired repetitions (default: 3)."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Directory used as each command's working directory.",
    )
    arguments = parser.parse_args(argv)
    if arguments.iterations < 1:
        parser.error("--iterations must be at least 1")
    arguments.project_root = arguments.project_root.resolve()
    return arguments


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_args(argv)
    commit = source_commit(arguments.project_root)
    runtime = runtime_identity()
    results: list[dict[str, object]] = []
    for iteration in range(1, arguments.iterations + 1):
        results.append(
            run_observation(
                "baseline",
                arguments.baseline_command,
                iteration,
                arguments.project_root,
                commit,
                runtime,
            )
        )
        results.append(
            run_observation(
                "assisted",
                arguments.assisted_command,
                iteration,
                arguments.project_root,
                commit,
                runtime,
            )
        )
    print(
        json.dumps(
            {
                "schema_version": 1,
                "project_root": str(arguments.project_root),
                "results": results,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

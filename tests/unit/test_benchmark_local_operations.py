import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "benchmark-local-operations.py"


def run_benchmark(
    project_root: Path, baseline: str, assisted: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--project-root",
            str(project_root),
            "--baseline-command",
            baseline,
            "--assisted-command",
            assisted,
            "--iterations",
            "2",
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def test_benchmark_records_raw_paired_results_and_preserves_failures(tmp_path: Path) -> None:
    baseline = f"{sys.executable} -c \"import sys; print('baseline'); sys.exit(7)\""
    assisted = f"{sys.executable} -c \"import sys; print('ok'); print('warning', file=sys.stderr)\""

    completed = run_benchmark(tmp_path, baseline, assisted)

    assert completed.returncode == 0
    report = json.loads(completed.stdout)
    assert report["schema_version"] == 1
    assert report["project_root"] == str(tmp_path)
    assert [(item["condition"], item["iteration"]) for item in report["results"]] == [
        ("baseline", 1),
        ("assisted", 1),
        ("baseline", 2),
        ("assisted", 2),
    ]

    baseline_results = report["results"][::2]
    assert [item["exit_status"] for item in baseline_results] == [7, 7]
    assert all(item["stdout_bytes"] == len(b"baseline\n") for item in baseline_results)
    assert all(item["stderr_bytes"] == 0 for item in baseline_results)

    assisted_result = report["results"][1]
    assert assisted_result["command"] == [
        sys.executable,
        "-c",
        "import sys; print('ok'); print('warning', file=sys.stderr)",
    ]
    assert assisted_result["command_word_count"] == 3
    assert assisted_result["stdout_bytes"] == len(b"ok\n")
    assert assisted_result["stderr_bytes"] == len(b"warning\n")
    assert assisted_result["exit_status"] == 0
    assert assisted_result["elapsed_duration_ns"] >= 0
    assert assisted_result["elapsed_duration_seconds"] >= 0
    assert assisted_result["source_commit"] == "unknown"
    assert set(assisted_result["runtime_identity"]) == {
        "implementation",
        "platform",
        "python_executable",
        "python_version",
    }


def test_benchmark_rejects_zero_iterations() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--baseline-command",
            "echo baseline",
            "--assisted-command",
            "echo assisted",
            "--iterations",
            "0",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert "--iterations must be at least 1" in completed.stderr


def test_benchmark_uses_the_project_source_commit() -> None:
    expected_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        cwd=PROJECT_ROOT,
        text=True,
    ).stdout.strip()

    completed = run_benchmark(
        PROJECT_ROOT,
        f"{sys.executable} -c \"print('baseline')\"",
        f"{sys.executable} -c \"print('assisted')\"",
    )

    assert completed.returncode == 0
    assert {item["source_commit"] for item in json.loads(completed.stdout)["results"]} == {
        expected_commit
    }

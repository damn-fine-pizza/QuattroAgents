import subprocess
import sys
from pathlib import Path


def test_metrics_markdown_report_from_cli() -> None:
    root = Path(__file__).parents[2]
    result = subprocess.run(
        [sys.executable, "-m", "quattroagents", "metrics", "report", "--format", "markdown"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout == (
        "# QuattroAgents metrics\n\n"
        "## Summary\n\n"
        "No execution samples recorded yet (0). All numeric values are zero; "
        "no savings or outcomes are inferred.\n\n"
        "| Metric | Value |\n"
        "| --- | ---: |\n"
        "| Samples | 0 |\n"
        "| Accepted tasks | 0 |\n"
        "| Retries | 0 |\n"
        "| Escalations | 0 |\n"
        "| Duration | 0 s |\n"
        "| Parallelism | 0 |\n"
        "| Repeated reads | 0 |\n"
        "| accepted_tasks_per_quota_unit | 0 |\n"
        "\n"
    )

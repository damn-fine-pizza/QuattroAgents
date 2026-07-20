from pathlib import Path

from quattroagents.cli import doctor, metrics_snapshot, render_metrics_markdown


def test_doctor_reports_optional_tool_availability(monkeypatch) -> None:
    def which(command: str) -> str | None:
        return "/opt/tools/" + command if command in {"rtk", "codebase-memory-mcp"} else None

    monkeypatch.setattr("quattroagents.cli.shutil.which", which)

    report = doctor(Path("/project"))

    assert report["rtk"] is True
    assert report["codebase_memory_mcp"] is True


def test_doctor_reports_runtime_revision(monkeypatch) -> None:
    monkeypatch.setattr("quattroagents.cli.runtime_identity", lambda: ("0123456789ab", True))
    monkeypatch.setattr("quattroagents.cli.runtime_version", lambda: "0.2.0+g0123456789ab.dirty")

    report = doctor(Path("/project"))

    assert report["version"] == "0.2.0+g0123456789ab.dirty"
    assert report["package_version"] == "0.2.0"
    assert report["revision"] == "0123456789ab"
    assert report["dirty"] is True


def test_metrics_json_snapshot_remains_compatible() -> None:
    assert metrics_snapshot() == {
        "samples": 0,
        "primary_metric": "accepted_tasks_per_quota_unit",
    }


def test_markdown_metrics_report_is_deterministic_and_explicit_about_no_data() -> None:
    assert render_metrics_markdown(metrics_snapshot()) == (
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
    )

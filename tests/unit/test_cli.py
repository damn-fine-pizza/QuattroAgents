from quattroagents.cli import metrics_snapshot, render_metrics_markdown


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

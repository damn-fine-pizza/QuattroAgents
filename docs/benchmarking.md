# Benchmarking

Compare A: one medium agent; B: medium orchestrator plus small worker; C: B plus context manifest; D: C plus MCP; and later E: adaptive parallelism. Report accepted tasks per quota unit only from real data, with duration, retries, escalation, summaries and repeated reads.

Run `.venv/bin/python -m quattroagents metrics report --format markdown` to produce the deterministic human-readable report. It lists samples, accepted tasks, retries, escalations, duration, parallelism, repeated reads, and `accepted_tasks_per_quota_unit`. Until a benchmark records real execution samples, each numeric metric is reported as zero and the report states that no outcomes or savings are inferred.

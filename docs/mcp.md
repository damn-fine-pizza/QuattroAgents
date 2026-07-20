# MCP

`qagents mcp serve --project .` starts the local stdio server. It implements initialization, lists the twelve control-plane tools (`task_create`, `task_claim`, `task_update`, `task_query`, `run_create`, `run_snapshot`, `run_query`, `run_verify`, `lease_acquire`, `lease_release`, `artifact_register`, `decision_propose`) and project resources, and persists tasks/leases in `.quattroagents/control-plane.sqlite3`. `qagents mcp doctor` verifies generated state and advertised interfaces.

For direct Codex and Claude registration without a QuattroAgents checkout, see the [MCP installation guide](quattroagents-mcp.md).

# MCP

`qagents mcp serve --project .` starts the local stdio server. It implements initialization, lists the eight control-plane tools and project resources, and persists tasks/leases in `.quattroagents/control-plane.sqlite3`. `qagents mcp doctor` verifies generated state and advertised interfaces.

For direct Codex and Claude registration without a QuattroAgents checkout, see the [MCP installation guide](quattroagents-mcp.md).

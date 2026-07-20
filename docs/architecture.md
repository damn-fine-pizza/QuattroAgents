# Architecture

The core holds canonical JSON state and provider-neutral policies. Adapters render Codex and Claude Code configuration from that state. The control plane uses SQLite with WAL for task claims and path leases; its stdio MCP server is local to the project root. L0 carries IDs/verdicts, L1 a concise structured summary, and L2 filesystem artifact references.

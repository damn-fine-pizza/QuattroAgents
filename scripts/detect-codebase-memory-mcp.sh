#!/usr/bin/env sh
set -eu

if command -v codebase-memory-mcp >/dev/null 2>&1; then
  codebase-memory-mcp --version
else
  echo "Codebase Memory MCP not installed; optional integration skipped."
fi

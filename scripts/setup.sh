#!/usr/bin/env sh
set -eu

PROJECT_ROOT=${1:-$(pwd)}
cd "$PROJECT_ROOT"
if command -v python3 >/dev/null 2>&1; then PYTHON=python3; else PYTHON=python; fi
"$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' || { echo "Python 3.11+ is required" >&2; exit 2; }
if [ ! -x .venv/bin/python ]; then "$PYTHON" -m venv .venv; fi
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -e ".[dev]"
"$VENV_PYTHON" -m quattroagents setup --project "$PROJECT_ROOT" --providers codex,claude --profile economy --install-mcp recommended --yes
"$PROJECT_ROOT/scripts/detect-rtk.sh"
"$PROJECT_ROOT/scripts/detect-codebase-memory-mcp.sh"
echo "Use scripts/rtk.sh to run RTK with the project's .venv developer tools."
"$VENV_PYTHON" -m quattroagents doctor --project "$PROJECT_ROOT" --json
"$VENV_PYTHON" -m quattroagents validate --project "$PROJECT_ROOT" --json

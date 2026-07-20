#!/usr/bin/env sh
set -eu

PROJECT_ROOT=${1:-$(pwd)}
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"

"$VENV_PYTHON" -m quattroagents doctor --project "$PROJECT_ROOT" --format json
"$VENV_PYTHON" -m quattroagents validate --project "$PROJECT_ROOT" --format json

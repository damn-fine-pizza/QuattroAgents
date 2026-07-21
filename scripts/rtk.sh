#!/usr/bin/env sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

if ! command -v rtk >/dev/null 2>&1; then
  echo "RTK is not installed; run scripts/detect-rtk.sh for details." >&2
  exit 127
fi

exec env PATH="$PROJECT_ROOT/.venv/bin:$PATH" rtk "$@"

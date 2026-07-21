#!/usr/bin/env sh
set -eu

if command -v rtk >/dev/null 2>&1; then
  rtk --version
else
  echo "RTK not installed; optional integration skipped."
fi

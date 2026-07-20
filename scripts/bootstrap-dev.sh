#!/usr/bin/env sh
exec "$(dirname "$0")/setup.sh" "${1:-$(pwd)}"

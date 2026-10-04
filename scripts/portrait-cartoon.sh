#!/usr/bin/env bash
# Run portrait_cartoon.py with uv, ignoring any stale VIRTUAL_ENV in the shell.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec env -u VIRTUAL_ENV uv run "${SCRIPT_DIR}/portrait_cartoon.py" "$@"

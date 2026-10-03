#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -x "${PROJECT_ROOT}/.venv/bin/uvicorn" ]]; then
  UVICORN="${PROJECT_ROOT}/.venv/bin/uvicorn"
elif command -v uvicorn >/dev/null 2>&1; then
  UVICORN="uvicorn"
else
  echo "uvicorn not found. Install backend deps with:" >&2
  echo "  pip install -r backend/requirements.txt" >&2
  exit 1
fi

cd "${SCRIPT_DIR}"
echo "Starting API at http://127.0.0.1:8000 (logs below)"
exec "${UVICORN}" app.main:app \
  --reload \
  --host 127.0.0.1 \
  --port 8000 \
  --log-level info \
  --access-log

#!/usr/bin/env bash
# Replay the square_draw sample in Rerun with a 3D SO-101 URDF model (no Hugging Face account).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
  PYTHON="${PROJECT_ROOT}/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
else
  echo "python3 not found" >&2
  exit 1
fi

exec "${PYTHON}" "${PROJECT_ROOT}/scripts/viz_square_urdf.py" \
  --dataset-root "${SCRIPT_DIR}/square_draw" \
  --assets-dir "${SCRIPT_DIR}/assets/so101"

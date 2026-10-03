#!/usr/bin/env bash
# Visualize the full pipeline output with SO-101 URDF arm + joint plots in Rerun.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DATASET_ROOT="${PROJECT_ROOT}/backend/resources/complete-output-example"
ASSETS_DIR="${PROJECT_ROOT}/samples/assets/so101"
REPO_ID="${LEROBOT_REPO_ID:-robo-replicator/complete-output-example}"
EPISODE_INDEX="${LEROBOT_EPISODE_INDEX:-0}"

if [[ ! -f "${DATASET_ROOT}/meta/info.json" ]]; then
  echo "Dataset not found at ${DATASET_ROOT}." >&2
  echo "Extract a *-draw.zip output into that folder first." >&2
  exit 1
fi

if [[ -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
  PYTHON="${PROJECT_ROOT}/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
else
  echo "python3 not found" >&2
  exit 1
fi

exec "${PYTHON}" "${SCRIPT_DIR}/viz_square_urdf.py" \
  --repo-id "${REPO_ID}" \
  --dataset-root "${DATASET_ROOT}" \
  --assets-dir "${ASSETS_DIR}" \
  --episode-index "${EPISODE_INDEX}"

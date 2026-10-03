#!/usr/bin/env bash
# Visualize the local square_draw sample dataset (no Hugging Face account needed).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DATASET_ROOT="${SCRIPT_DIR}/square_draw"

if [[ -x "${PROJECT_ROOT}/.venv/bin/lerobot-dataset-viz" ]]; then
  LEROBOT_DATASET_VIZ="${PROJECT_ROOT}/.venv/bin/lerobot-dataset-viz"
elif command -v lerobot-dataset-viz >/dev/null 2>&1; then
  LEROBOT_DATASET_VIZ="lerobot-dataset-viz"
else
  echo "lerobot-dataset-viz not found. Install with:" >&2
  echo "  python3 -m venv .venv && .venv/bin/pip install 'lerobot[dataset_viz]'" >&2
  exit 1
fi

exec "${LEROBOT_DATASET_VIZ}" \
  --repo-id robo-replicator/square_draw \
  --root "${DATASET_ROOT}" \
  --episode-index 0 \
  --mode local

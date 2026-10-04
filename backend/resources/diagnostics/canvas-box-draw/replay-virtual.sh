#!/usr/bin/env bash
# Visualize this drawing in Rerun (joint trajectories, no hardware required).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATASET_ROOT="${SCRIPT_DIR}"
REPO_ID="robo-replicator/canvas-box"
EPISODE_INDEX="${LEROBOT_EPISODE_INDEX:-0}"

if [[ ! -f "${DATASET_ROOT}/meta/info.json" ]]; then
  echo "Dataset not found at ${DATASET_ROOT} (missing meta/info.json)." >&2
  exit 1
fi

if [[ -x "${SCRIPT_DIR}/../.venv/bin/lerobot-dataset-viz" ]]; then
  LEROBOT_DATASET_VIZ="${SCRIPT_DIR}/../.venv/bin/lerobot-dataset-viz"
elif command -v lerobot-dataset-viz >/dev/null 2>&1; then
  LEROBOT_DATASET_VIZ="lerobot-dataset-viz"
else
  echo "lerobot-dataset-viz not found. Install with:" >&2
  echo "  pip install 'lerobot[dataset_viz]'" >&2
  exit 1
fi

exec "${LEROBOT_DATASET_VIZ}" \
  --repo-id "${REPO_ID}" \
  --root "${DATASET_ROOT}" \
  --episode-index "${EPISODE_INDEX}" \
  --mode local

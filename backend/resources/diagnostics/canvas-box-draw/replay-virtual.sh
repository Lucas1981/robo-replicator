#!/usr/bin/env bash
# Visualize this drawing in Rerun with a 3D SO-101 arm model (no hardware required).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATASET_ROOT="${SCRIPT_DIR}"
REPO_ID="robo-replicator/canvas-box"
EPISODE_INDEX="${LEROBOT_EPISODE_INDEX:-0}"

if [[ ! -f "${DATASET_ROOT}/meta/info.json" ]]; then
  echo "Dataset not found at ${DATASET_ROOT} (missing meta/info.json)." >&2
  exit 1
fi

if [[ ! -f "${SCRIPT_DIR}/viz_urdf.py" ]]; then
  echo "Missing viz_urdf.py next to this script." >&2
  exit 1
fi

_find_python() {
  local dir="${SCRIPT_DIR}"
  while [[ "${dir}" != "/" ]]; do
    if [[ -x "${dir}/.venv/bin/python" ]]; then
      echo "${dir}/.venv/bin/python"
      return 0
    fi
    dir="$(dirname "${dir}")"
  done
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi
  return 1
}

if ! PYTHON="$(_find_python)"; then
  echo "python3 not found." >&2
  exit 1
fi

if ! "${PYTHON}" -c "import rerun, lerobot" 2>/dev/null; then
  echo "Missing Python packages for 3D replay. Install with:" >&2
  echo "  pip install 'lerobot[dataset]' rerun-sdk" >&2
  exit 1
fi

exec "${PYTHON}" "${SCRIPT_DIR}/viz_urdf.py" \
  --repo-id "${REPO_ID}" \
  --dataset-root "${DATASET_ROOT}" \
  --episode-index "${EPISODE_INDEX}"

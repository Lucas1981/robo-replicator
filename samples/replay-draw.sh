#!/usr/bin/env bash
# Replay a generated LeRobotDataset on a physical SO-101 follower arm.
#
# Usage:
#   SO101_PORT=/dev/tty.usbmodemXXXX SO101_ID=YOUR_ARM_ID ./samples/replay-draw.sh /path/to/draw_dataset
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DATASET_ROOT="${1:-}"

ROBOT_PORT="${SO101_PORT:-${2:-}}"
ROBOT_ID="${SO101_ID:-${3:-}}"

if [[ -x "${PROJECT_ROOT}/.venv/bin/lerobot-replay" ]]; then
  LEROBOT_REPLAY="${PROJECT_ROOT}/.venv/bin/lerobot-replay"
elif command -v lerobot-replay >/dev/null 2>&1; then
  LEROBOT_REPLAY="lerobot-replay"
else
  echo "lerobot-replay not found. Install with:" >&2
  echo "  python3 -m venv .venv && .venv/bin/pip install 'lerobot[core_scripts]'" >&2
  exit 1
fi

if [[ -z "${DATASET_ROOT}" || -z "${ROBOT_PORT}" || -z "${ROBOT_ID}" ]]; then
  echo "Usage:" >&2
  echo "  SO101_PORT=/dev/tty.usbmodemXXXX SO101_ID=YOUR_ARM_ID ${0} /path/to/dataset_dir" >&2
  echo "  ${0} /path/to/dataset_dir /dev/tty.usbmodemXXXX YOUR_ARM_ID" >&2
  echo >&2
  echo "Unzip a downloaded *-draw.zip, then pass the extracted folder." >&2
  exit 1
fi

if [[ ! -f "${DATASET_ROOT}/meta/info.json" ]]; then
  echo "Dataset not found at ${DATASET_ROOT} (missing meta/info.json)." >&2
  exit 1
fi

REPO_ID="$(python3 - <<PY
import json
info = json.load(open("${DATASET_ROOT}/meta/info.json"))
print(info.get("repo_id", "robo-replicator/draw"))
PY
)"

exec "${LEROBOT_REPLAY}" \
  --robot.type=so101_follower \
  --robot.port="${ROBOT_PORT}" \
  --robot.id="${ROBOT_ID}" \
  --dataset.repo_id="${REPO_ID}" \
  --dataset.root="${DATASET_ROOT}" \
  --dataset.episode=0

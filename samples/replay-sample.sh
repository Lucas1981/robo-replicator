#!/usr/bin/env bash
# Replay the square_draw sample on a physical SO-101 follower arm.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DATASET_ROOT="${SCRIPT_DIR}/square_draw"

ROBOT_PORT="${SO101_PORT:-${1:-}}"
ROBOT_ID="${SO101_ID:-${2:-}}"

if [[ -x "${PROJECT_ROOT}/.venv/bin/lerobot-replay" ]]; then
  LEROBOT_REPLAY="${PROJECT_ROOT}/.venv/bin/lerobot-replay"
elif command -v lerobot-replay >/dev/null 2>&1; then
  LEROBOT_REPLAY="lerobot-replay"
else
  echo "lerobot-replay not found. Install with:" >&2
  echo "  python3 -m venv .venv && .venv/bin/pip install 'lerobot[core_scripts]'" >&2
  exit 1
fi

if [[ -z "${ROBOT_PORT}" || -z "${ROBOT_ID}" ]]; then
  echo "Usage:" >&2
  echo "  SO101_PORT=/dev/tty.usbmodemXXXX SO101_ID=YOUR_ARM_ID ${0}" >&2
  echo "  ${0} /dev/tty.usbmodemXXXX YOUR_ARM_ID" >&2
  echo >&2
  echo "Find the USB port with: lerobot-find-port" >&2
  exit 1
fi

exec "${LEROBOT_REPLAY}" \
  --robot.type=so101_follower \
  --robot.port="${ROBOT_PORT}" \
  --robot.id="${ROBOT_ID}" \
  --dataset.repo_id=robo-replicator/square_draw \
  --dataset.root="${DATASET_ROOT}" \
  --dataset.episode=0

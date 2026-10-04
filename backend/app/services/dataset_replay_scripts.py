from pathlib import Path

REPO_ID_PLACEHOLDER = "__REPO_ID__"

REPLAY_VIRTUAL_SH = f"""\
#!/usr/bin/env bash
# Visualize this drawing in Rerun (joint trajectories, no hardware required).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
DATASET_ROOT="${{SCRIPT_DIR}}"
REPO_ID="{REPO_ID_PLACEHOLDER}"
EPISODE_INDEX="${{LEROBOT_EPISODE_INDEX:-0}}"

if [[ ! -f "${{DATASET_ROOT}}/meta/info.json" ]]; then
  echo "Dataset not found at ${{DATASET_ROOT}} (missing meta/info.json)." >&2
  exit 1
fi

if [[ -x "${{SCRIPT_DIR}}/../.venv/bin/lerobot-dataset-viz" ]]; then
  LEROBOT_DATASET_VIZ="${{SCRIPT_DIR}}/../.venv/bin/lerobot-dataset-viz"
elif command -v lerobot-dataset-viz >/dev/null 2>&1; then
  LEROBOT_DATASET_VIZ="lerobot-dataset-viz"
else
  echo "lerobot-dataset-viz not found. Install with:" >&2
  echo "  pip install 'lerobot[dataset_viz]'" >&2
  exit 1
fi

exec "${{LEROBOT_DATASET_VIZ}}" \\
  --repo-id "${{REPO_ID}}" \\
  --root "${{DATASET_ROOT}}" \\
  --episode-index "${{EPISODE_INDEX}}" \\
  --mode local
"""

REPLAY_FOLLOWER_SH = f"""\
#!/usr/bin/env bash
# Replay this drawing on a physical SO-101 follower arm.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
DATASET_ROOT="${{SCRIPT_DIR}}"
REPO_ID="{REPO_ID_PLACEHOLDER}"
EPISODE_INDEX="${{LEROBOT_EPISODE_INDEX:-0}}"

ROBOT_PORT="${{SO101_PORT:-}}"
ROBOT_ID="${{SO101_ID:-}}"

if [[ ! -f "${{DATASET_ROOT}}/meta/info.json" ]]; then
  echo "Dataset not found at ${{DATASET_ROOT}} (missing meta/info.json)." >&2
  exit 1
fi

if [[ -x "${{SCRIPT_DIR}}/../.venv/bin/lerobot-replay" ]]; then
  LEROBOT_REPLAY="${{SCRIPT_DIR}}/../.venv/bin/lerobot-replay"
elif command -v lerobot-replay >/dev/null 2>&1; then
  LEROBOT_REPLAY="lerobot-replay"
else
  echo "lerobot-replay not found. Install with:" >&2
  echo "  pip install 'lerobot[core_scripts]'" >&2
  exit 1
fi

if [[ -z "${{ROBOT_PORT}}" || -z "${{ROBOT_ID}}" ]]; then
  echo "Usage:" >&2
  echo "  SO101_PORT=/dev/tty.usbmodemXXXX SO101_ID=YOUR_ARM_ID ${{0}}" >&2
  echo >&2
  echo "Find the USB port with: lerobot-find-port" >&2
  exit 1
fi

exec "${{LEROBOT_REPLAY}}" \\
  --robot.type=so101_follower \\
  --robot.port="${{ROBOT_PORT}}" \\
  --robot.id="${{ROBOT_ID}}" \\
  --dataset.repo_id="${{REPO_ID}}" \\
  --dataset.root="${{DATASET_ROOT}}" \\
  --dataset.episode="${{EPISODE_INDEX}}"
"""


def write_replay_scripts(dataset_root: Path, repo_id: str) -> None:
    scripts = {
        "replay-virtual.sh": REPLAY_VIRTUAL_SH.replace(REPO_ID_PLACEHOLDER, repo_id),
        "replay-follower.sh": REPLAY_FOLLOWER_SH.replace(REPO_ID_PLACEHOLDER, repo_id),
    }
    for filename, content in scripts.items():
        path = dataset_root / filename
        path.write_text(content, encoding="utf-8", newline="\n")
        path.chmod(0o755)

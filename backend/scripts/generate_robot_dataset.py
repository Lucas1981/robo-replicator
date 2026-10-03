#!/usr/bin/env python3
"""Convert an SVG path file into a LeRobotDataset for SO-101 replay.

Usage:
    python backend/scripts/generate_robot_dataset.py backend/resources/paths-sample.svg
    python backend/scripts/generate_robot_dataset.py drawing-paths.svg --output samples/my_draw
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.robot_config import FPS  # noqa: E402
from app.services.robot_dataset import RobotDatasetError, write_dataset_directory  # noqa: E402
from app.services.robot_trajectory import build_trajectory, estimate_duration_seconds  # noqa: E402
from app.services.svg_parser import parse_svg_paths  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("svg", type=Path, help="Input SVG with drawable paths")
    parser.add_argument(
        "--output",
        type=Path,
        help="Output directory for the LeRobotDataset (default: <svg-stem>_draw/)",
    )
    parser.add_argument(
        "--task",
        default=None,
        help="Task label stored in the dataset (default: derived from filename)",
    )
    args = parser.parse_args()

    svg_path = args.svg.resolve()
    if not svg_path.is_file():
        raise SystemExit(f"SVG not found: {svg_path}")

    output_dir = (args.output or svg_path.with_name(f"{svg_path.stem}_draw")).resolve()
    task = args.task or f"Draw paths from {svg_path.name}"
    svg_bytes = svg_path.read_bytes()

    try:
        parsed = parse_svg_paths(svg_bytes)
        trajectory = build_trajectory(parsed)
        write_dataset_directory(svg_bytes, output_dir, svg_path.name, task)
    except (RobotDatasetError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc

    duration = estimate_duration_seconds(len(trajectory), FPS)
    print(f"Wrote dataset to {output_dir}")
    print(f"  paths: {len(parsed.paths)}  frames: {len(trajectory)}  duration: {duration:.1f}s @ {FPS} fps")
    print()
    print("Replay with:")
    print("  lerobot-replay \\")
    print("    --robot.type=so101_follower \\")
    print("    --robot.port=/dev/tty.usbmodemXXXX \\")
    print("    --robot.id=YOUR_ARM_ID \\")
    print(f"    --dataset.repo_id=robo-replicator/{svg_path.stem.removesuffix('-paths')} \\")
    print(f"    --dataset.root={output_dir} \\")
    print("    --dataset.episode=0")


if __name__ == "__main__":
    main()

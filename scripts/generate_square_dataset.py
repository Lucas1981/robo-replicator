#!/usr/bin/env python3
"""Generate a LeRobotDataset episode that draws a square on a canvas.

The output is compatible with ``lerobot-replay`` on an SO-101 follower arm.
Joint angles are a starting point — tune HOME_POSE and SQUARE_EXTENT for your
physical setup (pen mount, paper position, calibration).

Usage:
    python scripts/generate_square_dataset.py
    python scripts/generate_square_dataset.py --output samples/square_draw
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import torch
from lerobot.datasets.lerobot_dataset import LeRobotDataset

FPS = 30
TASK = "Draw a square on the canvas"

# Nominal pose over the center of the drawing surface (degrees).
HOME_POSE = {
    "shoulder_pan": 0.0,
    "shoulder_lift": 15.0,
    "elbow_flex": 50.0,
    "wrist_flex": -50.0,
    "wrist_roll": 0.0,
}

# Half-width of the square in shoulder_pan / shoulder_lift degrees.
SQUARE_HALF_EXTENT_PAN = 12.0
SQUARE_HALF_EXTENT_LIFT = 10.0

# Gripper range is 0–100 on SO-101 (open → closed).
PEN_UP = 10.0
PEN_DOWN = 85.0

FRAMES_TRAVEL = 15
FRAMES_PEN_SETTLE = 5
FRAMES_DRAW = 30

JOINT_NAMES = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
]

DATASET_FEATURES = {
    "action": {
        "dtype": "float32",
        "shape": (6,),
        "names": [f"{name}.pos" for name in JOINT_NAMES],
    },
    "observation.state": {
        "dtype": "float32",
        "shape": (6,),
        "names": [f"{name}.pos" for name in JOINT_NAMES],
    },
}


@dataclass(frozen=True)
class Pose2D:
    pan: float
    lift: float


def canvas_to_joints(point: Pose2D, pen_down: bool) -> list[float]:
    """Map normalized canvas coordinates to SO-101 joint targets."""
    return [
        HOME_POSE["shoulder_pan"] + point.pan * SQUARE_HALF_EXTENT_PAN,
        HOME_POSE["shoulder_lift"] + point.lift * SQUARE_HALF_EXTENT_LIFT,
        HOME_POSE["elbow_flex"],
        HOME_POSE["wrist_flex"],
        HOME_POSE["wrist_roll"],
        PEN_DOWN if pen_down else PEN_UP,
    ]


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def interpolate_poses(
    start: Pose2D, end: Pose2D, pen_down: bool, num_frames: int
) -> list[list[float]]:
    if num_frames < 1:
        raise ValueError("num_frames must be at least 1")
    if num_frames == 1:
        return [canvas_to_joints(end, pen_down)]

    frames: list[list[float]] = []
    for i in range(num_frames):
        t = i / (num_frames - 1)
        point = Pose2D(
            pan=lerp(start.pan, end.pan, t),
            lift=lerp(start.lift, end.lift, t),
        )
        frames.append(canvas_to_joints(point, pen_down))
    return frames


def square_corners() -> list[Pose2D]:
    """Unit square corners: bottom-left → bottom-right → top-right → top-left."""
    return [
        Pose2D(-1.0, -1.0),
        Pose2D(1.0, -1.0),
        Pose2D(1.0, 1.0),
        Pose2D(-1.0, 1.0),
    ]


def build_square_trajectory() -> list[list[float]]:
    """Pen-up travel to the first corner, then four pen-down straight edges."""
    corners = square_corners()
    edges = list(zip(corners, corners[1:] + corners[:1]))
    trajectory: list[list[float]] = []

    # Approach the first corner with the pen up.
    trajectory.extend(interpolate_poses(corners[-1], corners[0], pen_down=False, num_frames=FRAMES_TRAVEL))

    for start, end in edges:
        trajectory.extend([canvas_to_joints(start, pen_down=True)] * FRAMES_PEN_SETTLE)
        trajectory.extend(interpolate_poses(start, end, pen_down=True, num_frames=FRAMES_DRAW))
        trajectory.extend([canvas_to_joints(end, pen_down=False)] * FRAMES_PEN_SETTLE)

    trajectory.extend([canvas_to_joints(corners[0], pen_down=False)] * FRAMES_TRAVEL)
    return trajectory


def generate_dataset(output_dir: Path, repo_id: str = "robo-replicator/square_draw") -> Path:
    if output_dir.exists():
        import shutil

        shutil.rmtree(output_dir)

    dataset = LeRobotDataset.create(
        repo_id=repo_id,
        fps=FPS,
        features=DATASET_FEATURES,
        root=output_dir,
        robot_type="so101_follower",
        use_videos=False,
    )

    for joints in build_square_trajectory():
        frame = {
            "action": torch.tensor(joints, dtype=torch.float32),
            "observation.state": torch.tensor(joints, dtype=torch.float32),
            "task": TASK,
        }
        dataset.add_frame(frame)

    dataset.save_episode()
    dataset.finalize()
    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "samples" / "square_draw",
        help="Directory for the generated LeRobotDataset",
    )
    args = parser.parse_args()

    output = generate_dataset(args.output.resolve())
    num_frames = len(build_square_trajectory())
    duration = num_frames / FPS
    print(f"Wrote dataset to {output}")
    print(f"  frames: {num_frames}  duration: {duration:.1f}s @ {FPS} fps")
    print()
    print("Replay with:")
    print("  lerobot-replay \\")
    print("    --robot.type=so101_follower \\")
    print("    --robot.port=/dev/tty.usbmodemXXXX \\")
    print("    --robot.id=YOUR_ARM_ID \\")
    print(f"    --dataset.repo_id=robo-replicator/square_draw \\")
    print(f"    --dataset.root={output} \\")
    print("    --dataset.episode=0")


if __name__ == "__main__":
    main()

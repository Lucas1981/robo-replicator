#!/usr/bin/env python3
"""Replay a LeRobotDataset in Rerun with a 3D SO-101 URDF model and joint plots."""

from __future__ import annotations

import argparse
import math
import urllib.request
from pathlib import Path

import rerun as rr
import rerun.blueprint as rrb
from lerobot.datasets.lerobot_dataset import LeRobotDataset

SO101_BASE_URL = (
    "https://raw.githubusercontent.com/TheRobotStudio/SO-ARM100/main/Simulation/SO101"
)
URDF_FILENAME = "so101_new_calib.urdf"


def ensure_so101_assets(cache_dir: Path) -> Path:
    """Download the SO-101 URDF and mesh assets if not already cached."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    urdf_path = cache_dir / URDF_FILENAME
    assets_dir = cache_dir / "assets"

    if not urdf_path.exists():
        print(f"Downloading {URDF_FILENAME}...")
        urdf_path.write_bytes(urllib.request.urlopen(f"{SO101_BASE_URL}/{URDF_FILENAME}").read())

    if not assets_dir.exists() or not any(assets_dir.iterdir()):
        import json

        assets_dir.mkdir(parents=True, exist_ok=True)
        listing = json.loads(
            urllib.request.urlopen(
                "https://api.github.com/repos/TheRobotStudio/SO-ARM100/"
                "contents/Simulation/SO101/assets?ref=main"
            ).read()
        )
        print(f"Downloading {len(listing)} mesh files (~18 MB, one-time)...")
        for entry in listing:
            if entry["type"] != "file":
                continue
            dest = assets_dir / entry["name"]
            if not dest.exists():
                dest.write_bytes(urllib.request.urlopen(entry["download_url"]).read())

    return urdf_path


def gripper_to_radians(value: float, joint: rr.urdf.UrdfJoint) -> float:
    """Map LeRobot gripper range (0-100) to the URDF revolute joint."""
    t = max(0.0, min(100.0, value)) / 100.0
    return joint.limit_lower + t * (joint.limit_upper - joint.limit_lower)


def joint_value_radians(feature_name: str, value: float, urdf_joint: rr.urdf.UrdfJoint) -> float:
    if feature_name.startswith("gripper"):
        return gripper_to_radians(value, urdf_joint)
    return math.radians(value)


def visualize(
    dataset_root: Path,
    assets_dir: Path,
    repo_id: str,
    episode_index: int = 0,
    spawn_viewer: bool = True,
    save_path: Path | None = None,
) -> None:
    urdf_path = ensure_so101_assets(assets_dir)
    dataset = LeRobotDataset(repo_id, root=dataset_root, episodes=[episode_index])
    actions = dataset.select_columns("action")
    action_names = dataset.features["action"]["names"]

    urdf_tree = rr.urdf.UrdfTree.from_file_path(urdf_path)
    urdf_joints = {joint.name: joint for joint in urdf_tree.joints() if joint.joint_type == "revolute"}

    rr.init(f"{repo_id}/urdf_episode_{episode_index}", spawn=spawn_viewer and save_path is None)
    urdf_tree.log_urdf_to_recording()

    robot_name = urdf_tree.name.replace(" ", "_")
    arm_view = rrb.Spatial3DView(
        name="SO-101",
        origin=f"/{robot_name}",
        overrides={
            f"{robot_name}/collision_geometries": rrb.EntityBehavior(visible=False),
        },
    )
    joints_view = rrb.TimeSeriesView(origin="action", name="Joint commands")
    blueprint = rrb.Blueprint(
        rrb.Tabs(
            arm_view,
            joints_view,
            active_tab="SO-101",
        )
    )
    rr.send_blueprint(blueprint)

    for frame_idx in range(dataset.num_frames):
        rr.set_time("frame_index", sequence=frame_idx)
        rr.set_time("timestamp", timestamp=frame_idx / dataset.fps)

        action = actions[frame_idx]["action"]
        rr.log("action", rr.Scalars(action.numpy()))

        for i, feature_name in enumerate(action_names):
            joint_key = feature_name.removesuffix(".pos")
            urdf_joint = urdf_joints.get(joint_key)
            if urdf_joint is None:
                continue
            angle = joint_value_radians(joint_key, float(action[i]), urdf_joint)
            rr.log("joint_transforms", urdf_joint.compute_transform(angle, clamp=True))

    if save_path is not None:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        rr.save(save_path)
        print(f"Saved Rerun recording to {save_path}")


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-id",
        default="local/dataset",
        help="LeRobotDataset repo id label (any value works for a local --dataset-root)",
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=script_dir,
        help="Root directory of the LeRobotDataset (default: directory containing this script)",
    )
    parser.add_argument(
        "--assets-dir",
        type=Path,
        default=script_dir / ".cache" / "so101",
        help="Cache directory for the SO-101 URDF and mesh files",
    )
    parser.add_argument("--episode-index", type=int, default=0)
    parser.add_argument(
        "--save",
        type=Path,
        default=None,
        help="Write a .rrd file instead of opening the viewer",
    )
    args = parser.parse_args()

    visualize(
        dataset_root=args.dataset_root.resolve(),
        assets_dir=args.assets_dir.resolve(),
        repo_id=args.repo_id,
        episode_index=args.episode_index,
        save_path=args.save,
    )


if __name__ == "__main__":
    main()

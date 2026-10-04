"""LeRobot/placo kinematics helpers for SO-101 planar drawing."""

from __future__ import annotations

import json
import logging
import urllib.request
from functools import lru_cache
from pathlib import Path

import numpy as np

from app.config import RESOURCES_DIR
from app.services.robot_config import (
    ARM_JOINT_NAMES,
    HOME_POSE,
    IK_ORIENTATION_WEIGHT,
    REACH_POSE,
)

logger = logging.getLogger(__name__)

SO101_BASE_URL = (
    "https://raw.githubusercontent.com/TheRobotStudio/SO-ARM100/main/Simulation/SO101"
)
URDF_FILENAME = "so101_new_calib.urdf"
URDF_CACHE_DIR = RESOURCES_DIR / "so101"
TARGET_FRAME = "gripper_frame_link"


def ensure_so101_urdf() -> Path:
    URDF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    urdf_path = URDF_CACHE_DIR / URDF_FILENAME
    assets_dir = URDF_CACHE_DIR / "assets"

    if not urdf_path.exists():
        logger.info("Downloading %s for planar IK...", URDF_FILENAME)
        urdf_path.write_bytes(urllib.request.urlopen(f"{SO101_BASE_URL}/{URDF_FILENAME}").read())

    if not assets_dir.exists() or not any(assets_dir.iterdir()):
        listing = json.loads(
            urllib.request.urlopen(
                "https://api.github.com/repos/TheRobotStudio/SO-ARM100/"
                "contents/Simulation/SO101/assets?ref=main"
            ).read()
        )
        assets_dir.mkdir(parents=True, exist_ok=True)
        for entry in listing:
            if entry["type"] != "file":
                continue
            dest = assets_dir / entry["name"]
            if not dest.exists():
                dest.write_bytes(urllib.request.urlopen(entry["download_url"]).read())

    return urdf_path


@lru_cache(maxsize=1)
def get_robot_kinematics():
    from lerobot.model.kinematics import RobotKinematics

    urdf_path = ensure_so101_urdf()
    return RobotKinematics(
        str(urdf_path),
        TARGET_FRAME,
        joint_names=ARM_JOINT_NAMES,
    )


def home_joint_guess() -> np.ndarray:
    return np.array([HOME_POSE[name] for name in ARM_JOINT_NAMES], dtype=float)


def reach_joint_guess() -> np.ndarray:
    """Extended reach seed for IK (avoids folded local minima near the base)."""
    return np.array([REACH_POSE[name] for name in ARM_JOINT_NAMES], dtype=float)


def gripper_down_rotation() -> np.ndarray:
    """Gripper frame with +Z pointing straight down (pen mounted in the jaws).

    The SO-101 gripper mesh opens along Z; for drawing, Z should align with
    world -Z so the tool faces the horizontal canvas vertically.
    """
    y_axis = np.array([0.0, 1.0, 0.0])
    z_axis = np.array([0.0, 0.0, -1.0])
    x_axis = np.cross(y_axis, z_axis)
    return np.column_stack([x_axis, y_axis, z_axis])


def build_ee_target(xyz_m: np.ndarray, rotation: np.ndarray) -> np.ndarray:
    """Build a 4x4 end-effector target like LeRobot's InverseKinematicsEEToJoints."""
    target = np.eye(4, dtype=float)
    target[:3, :3] = rotation
    target[:3, 3] = xyz_m
    return target


def solve_arm_ik(
    xyz_m: np.ndarray,
    q_seed: np.ndarray,
    *,
    pen_down_rotation: np.ndarray,
    orientation_weight: float = IK_ORIENTATION_WEIGHT,
) -> np.ndarray:
    """Map a planar XYZ target to arm joint angles via LeRobot RobotKinematics.

    Two-phase solve (position, then gripper-down orientation) matches how the
    SO-101 5-DOF arm is used in practice and avoids folded configurations.
    """
    kinematics = get_robot_kinematics()
    position_target = build_ee_target(xyz_m, kinematics.forward_kinematics(q_seed)[:3, :3])
    q_position = kinematics.inverse_kinematics(
        q_seed,
        position_target,
        orientation_weight=0.0,
    )
    orientation_target = build_ee_target(xyz_m, pen_down_rotation)
    return kinematics.inverse_kinematics(
        q_position,
        orientation_target,
        orientation_weight=orientation_weight,
    )


def position_error_m(xyz_m: np.ndarray, q: np.ndarray) -> float:
    kinematics = get_robot_kinematics()
    actual = kinematics.forward_kinematics(q)[:3, 3]
    return float(np.linalg.norm(actual - xyz_m))

"""Planar inverse kinematics for drawing on a horizontal canvas in front of the SO-101."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from app.services.robot_config import (
    CANVAS_BASE_CLEARANCE_MM,
    CANVAS_HEIGHT_MM,
    CANVAS_MARGIN,
    CANVAS_NEAR_OFFSET_FRACTION,
    CANVAS_PLANE_Z_MM,
    CANVAS_V_NEAR_FRACTION,
    CANVAS_WIDTH_MM,
    IK_ORIENTATION_WEIGHT,
)
from app.services.robot_kinematics import (
    gripper_down_rotation,
    position_error_m,
    reach_joint_guess,
    solve_arm_ik,
)

logger = logging.getLogger(__name__)

CORNER_UV = (
    (0.05, 0.05),
    (0.95, 0.05),
    (0.95, 0.95),
    (0.05, 0.95),
)
# Default travel origin on the near edge (extended over the canvas, away from the base).
READY_UV = (0.05, 0.05)


@dataclass(frozen=True)
class PlanarCanvasModel:
    near_offset_m: float
    depth_m: float
    width_m: float
    plane_z_m: float
    orientation_weight: float
    v_near_fraction: float

    @classmethod
    def from_config(cls, depth_mm: float | None = None) -> PlanarCanvasModel:
        inset = CANVAS_MARGIN
        return cls(
            near_offset_m=(CANVAS_NEAR_OFFSET_FRACTION * CANVAS_HEIGHT_MM + CANVAS_BASE_CLEARANCE_MM)
            / 1000.0,
            depth_m=((depth_mm if depth_mm is not None else CANVAS_HEIGHT_MM) * (1.0 - 2.0 * inset))
            / 1000.0,
            width_m=(CANVAS_WIDTH_MM * (1.0 - 2.0 * inset)) / 1000.0,
            plane_z_m=CANVAS_PLANE_Z_MM / 1000.0,
            orientation_weight=IK_ORIENTATION_WEIGHT,
            v_near_fraction=CANVAS_V_NEAR_FRACTION,
        )

    def as_dict(self) -> dict[str, float]:
        return {
            "near_offset_mm": self.near_offset_m * 1000.0,
            "depth_mm": self.depth_m * 1000.0,
            "width_mm": self.width_m * 1000.0,
            "plane_z_mm": self.plane_z_m * 1000.0,
            "orientation_weight": self.orientation_weight,
            "near_offset_fraction": CANVAS_NEAR_OFFSET_FRACTION,
            "base_clearance_mm": CANVAS_BASE_CLEARANCE_MM,
            "v_near_fraction": self.v_near_fraction,
            "canvas_margin": CANVAS_MARGIN,
        }

    def uv_to_xyz(self, u: float, v: float) -> np.ndarray:
        return xyz_from_uv(self, u, v)


@dataclass
class PlanarIkSolver:
    model: PlanarCanvasModel
    pen_down_rotation: np.ndarray
    corner_joints: list[np.ndarray]

    def uv_to_xyz(self, u: float, v: float) -> np.ndarray:
        return self.model.uv_to_xyz(u, v)

    def joints_for_uv(self, u: float, v: float, q_seed: np.ndarray) -> list[float]:
        xyz = self.uv_to_xyz(u, v)
        q = self._solve_xyz(xyz, q_seed)
        return q.astype(float).tolist()

    def joints_for_xyz(self, xyz: np.ndarray, q_seed: np.ndarray) -> list[float]:
        q = self._solve_xyz(xyz, q_seed)
        return q.astype(float).tolist()

    def corner_poses_dict(self) -> dict[str, list[float]]:
        labels = ("top_left", "top_right", "bottom_right", "bottom_left")
        return {
            label: joints.tolist()
            for label, joints in zip(labels, self.corner_joints, strict=True)
        }

    def _solve_xyz(self, xyz: np.ndarray, q_seed: np.ndarray) -> np.ndarray:
        return solve_arm_ik(
            xyz,
            q_seed,
            pen_down_rotation=self.pen_down_rotation,
            orientation_weight=self.model.orientation_weight,
        )


def build_planar_ik_solver() -> PlanarIkSolver:
    model = PlanarCanvasModel.from_config()
    pen_down_rotation = gripper_down_rotation()
    model, corner_joints = _calibrate_canvas(model, pen_down_rotation)
    return PlanarIkSolver(
        model=model,
        pen_down_rotation=pen_down_rotation,
        corner_joints=corner_joints,
    )


def _solve_corners(
    model: PlanarCanvasModel,
    pen_down_rotation: np.ndarray,
) -> tuple[list[np.ndarray], float]:
    corner_joints: list[np.ndarray] = []
    q = reach_joint_guess()
    max_error_m = 0.0

    for u, v in CORNER_UV:
        xyz = model.uv_to_xyz(u, v)
        q = solve_arm_ik(
            xyz,
            q,
            pen_down_rotation=pen_down_rotation,
            orientation_weight=model.orientation_weight,
        )
        max_error_m = max(max_error_m, position_error_m(xyz, q))
        corner_joints.append(q.copy())

    return corner_joints, max_error_m


def _calibrate_canvas(
    model: PlanarCanvasModel,
    pen_down_rotation: np.ndarray,
) -> tuple[PlanarCanvasModel, list[np.ndarray]]:
    """Pick canvas depth for reachable corner IK with gripper facing down."""
    requested_depth_m = model.depth_m
    min_depth_m = max(requested_depth_m * 0.12, 0.025)

    best_model = model
    best_corners, best_error_m = _solve_corners(model, pen_down_rotation)

    depth_m = requested_depth_m
    while depth_m * 0.88 >= min_depth_m:
        depth_m *= 0.88
        trial = PlanarCanvasModel(
            near_offset_m=model.near_offset_m,
            depth_m=depth_m,
            width_m=model.width_m,
            plane_z_m=model.plane_z_m,
            orientation_weight=model.orientation_weight,
            v_near_fraction=model.v_near_fraction,
        )
        corner_joints, max_error_m = _solve_corners(trial, pen_down_rotation)
        if max_error_m < best_error_m:
            best_model = trial
            best_corners = corner_joints
            best_error_m = max_error_m

    if best_model.depth_m < requested_depth_m - 1e-6:
        logger.info(
            "Calibrated canvas depth to %.1f mm (requested %.1f mm) for gripper-down planar IK.",
            best_model.depth_m * 1000.0,
            requested_depth_m * 1000.0,
        )

    if best_error_m > 0.035:
        logger.warning(
            "Canvas corner IK error remains %.1f mm after depth calibration; "
            "tune ROBOT_CANVAS_PLANE_Z_MM, ROBOT_CANVAS_NEAR_OFFSET_FRACTION, "
            "or ROBOT_CANVAS_BASE_CLEARANCE_MM.",
            best_error_m * 1000.0,
        )

    return best_model, best_corners


def xyz_from_uv(model: PlanarCanvasModel, u: float, v: float) -> np.ndarray:
    u_n, v_n = _normalized_uv(u, v, model.v_near_fraction)
    return np.array(
        [
            model.near_offset_m + v_n * model.depth_m,
            (u_n - 0.5) * model.width_m,
            model.plane_z_m,
        ],
        dtype=float,
    )


def _normalized_uv(u: float, v: float, v_near_fraction: float) -> tuple[float, float]:
    inset = CANVAS_MARGIN
    span = 1.0 - 2.0 * inset
    if span <= 0.0:
        raise ValueError("CANVAS_MARGIN must be less than 0.5.")
    u_n = float(np.clip((u - inset) / span, 0.0, 1.0))
    v_n = float(np.clip((v - inset) / span, 0.0, 1.0))
    if v_near_fraction > 0.0:
        v_n = v_near_fraction + (1.0 - v_near_fraction) * v_n
    return u_n, v_n

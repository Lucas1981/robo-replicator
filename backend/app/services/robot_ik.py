"""Backward-compatible entry points for canvas → joint mapping."""

from __future__ import annotations

from app.services.robot_planar_ik import PlanarIkSolver, build_planar_ik_solver


def load_planar_ik_solver() -> PlanarIkSolver:
    return build_planar_ik_solver()

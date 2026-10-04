import json
import math
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from app.services.robot_config import (
    CANVAS_ASPECT,
    CANVAS_HEIGHT_MM,
    CANVAS_MARGIN,
    CANVAS_ORIENTATION,
    CANVAS_WIDTH_MM,
    DRAW_SPEED_MM_S,
    FPS,
    FRAMES_PATH_SETTLE,
    MIN_DRAW_FRAMES,
    MIN_TRAVEL_FRAMES,
    TRAVEL_LIFT_MM,
    TRAVEL_SPEED_MM_S,
)
from app.services.robot_planar_ik import (
    READY_UV,
    PlanarCanvasModel,
    PlanarIkSolver,
    build_planar_ik_solver,
)
from app.services.svg_parser import ParsedSvg


@dataclass(frozen=True)
class CanvasUV:
    """Normalized canvas position: u=left→right, v=near→far on a horizontal pad."""

    u: float
    v: float


@dataclass(frozen=True)
class CanvasMapping:
    """SVG viewBox → horizontal portrait A4 canvas (UV) transform."""

    svg_width: float
    svg_height: float
    canvas_width_mm: float
    canvas_height_mm: float
    canvas_aspect: float
    canvas_orientation: str
    scale: float
    content_width: float
    content_height: float
    u_pad: float
    v_pad: float
    source_svg_width: float | None = None
    source_svg_height: float | None = None
    crop_x: float = 0.0
    crop_y: float = 0.0


@dataclass(frozen=True)
class TrajectoryResult:
    frames: list[list[float]]
    mapping: CanvasMapping
    planar_model: PlanarCanvasModel
    corner_joints: dict[str, list[float]]


def build_trajectory(parsed: ParsedSvg) -> TrajectoryResult:
    solver = build_planar_ik_solver()
    mapping = compute_canvas_mapping(parsed.width, parsed.height)
    mapping = replace(
        mapping,
        source_svg_width=parsed.source_width,
        source_svg_height=parsed.source_height,
        crop_x=parsed.crop_x,
        crop_y=parsed.crop_y,
    )
    canvas_paths = map_svg_paths_to_canvas(parsed.paths, mapping)
    trajectory: list[list[float]] = []
    q_seed = solver.corner_joints[0].copy()
    current = CanvasUV(u=READY_UV[0], v=READY_UV[1])

    for path in canvas_paths:
        if len(path) < 2:
            continue

        start = path[0]
        travel_frames, q_seed = _travel(solver, q_seed, current, start)
        trajectory.extend(travel_frames)
        settle = solver.joints_for_uv(start.u, start.v, q_seed)
        trajectory.extend([settle] * FRAMES_PATH_SETTLE)
        q_seed = _numpy_joints(settle)

        for segment_start, segment_end in zip(path, path[1:]):
            segment_frames, q_seed = _draw_segment(solver, q_seed, segment_start, segment_end)
            trajectory.extend(segment_frames)

        settle = solver.joints_for_uv(path[-1].u, path[-1].v, q_seed)
        trajectory.extend([settle] * FRAMES_PATH_SETTLE)
        q_seed = _numpy_joints(settle)
        current = path[-1]

    if not trajectory:
        raise ValueError("SVG paths produced an empty robot trajectory.")

    return TrajectoryResult(
        frames=trajectory,
        mapping=mapping,
        planar_model=solver.model,
        corner_joints=solver.corner_poses_dict(),
    )


def compute_canvas_mapping(svg_width: float, svg_height: float) -> CanvasMapping:
    if svg_width <= 0 or svg_height <= 0:
        raise ValueError("SVG width and height must be positive.")

    inset = CANVAS_MARGIN
    drawable_u_span = 1.0 - 2.0 * inset
    drawable_v_span = 1.0 - 2.0 * inset
    scale = min(drawable_u_span / svg_width, drawable_v_span / svg_height)
    content_width = svg_width * scale
    content_height = svg_height * scale
    u_pad = inset + (drawable_u_span - content_width) / 2.0
    v_pad = inset + (drawable_v_span - content_height) / 2.0

    return CanvasMapping(
        svg_width=svg_width,
        svg_height=svg_height,
        canvas_width_mm=CANVAS_WIDTH_MM,
        canvas_height_mm=CANVAS_HEIGHT_MM,
        canvas_aspect=CANVAS_ASPECT,
        canvas_orientation=CANVAS_ORIENTATION,
        scale=scale,
        content_width=content_width,
        content_height=content_height,
        u_pad=u_pad,
        v_pad=v_pad,
    )


def map_svg_paths_to_canvas(
    paths: list[list[tuple[float, float]]],
    mapping: CanvasMapping,
) -> list[list[CanvasUV]]:
    return [[svg_point_to_canvas(x, y, mapping) for x, y in path] for path in paths]


def svg_point_to_canvas(x: float, y: float, mapping: CanvasMapping) -> CanvasUV:
    u = mapping.u_pad + x * mapping.scale
    v = mapping.v_pad + y * mapping.scale
    return CanvasUV(u=u, v=v)


def write_draw_source_meta(
    dataset_root: Path,
    mapping: CanvasMapping,
    planar_model: PlanarCanvasModel,
    corner_joints: dict[str, list[float]],
    *,
    source_filename: str,
) -> Path:
    meta_dir = dataset_root / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_filename": source_filename,
        "svg_width": mapping.svg_width,
        "svg_height": mapping.svg_height,
        "source_svg_width": mapping.source_svg_width,
        "source_svg_height": mapping.source_svg_height,
        "crop_x": mapping.crop_x,
        "crop_y": mapping.crop_y,
        "canvas_width_mm": mapping.canvas_width_mm,
        "canvas_height_mm": mapping.canvas_height_mm,
        "canvas_aspect": mapping.canvas_aspect,
        "canvas_orientation": mapping.canvas_orientation,
        "transform": {
            "scale": mapping.scale,
            "content_width": mapping.content_width,
            "content_height": mapping.content_height,
            "u_pad": mapping.u_pad,
            "v_pad": mapping.v_pad,
        },
        "planar_canvas": planar_model.as_dict(),
        "corner_poses": corner_joints,
        "motion": {
            "fps": FPS,
            "draw_speed_mm_s": DRAW_SPEED_MM_S,
            "travel_speed_mm_s": TRAVEL_SPEED_MM_S,
            "travel_lift_mm": TRAVEL_LIFT_MM,
        },
    }
    path = meta_dir / "draw_source.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _canvas_distance_mm(start: CanvasUV, end: CanvasUV, model: PlanarCanvasModel) -> float:
    start_xyz = _uv_to_xyz_mm(start, model)
    end_xyz = _uv_to_xyz_mm(end, model)
    return float(np_hypot3(end_xyz, start_xyz))


def _uv_to_xyz_mm(uv: CanvasUV, model: PlanarCanvasModel) -> tuple[float, float, float]:
    xyz = model.uv_to_xyz(uv.u, uv.v)
    return xyz[0] * 1000.0, xyz[1] * 1000.0, xyz[2] * 1000.0


def np_hypot3(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def _frames_for_distance_mm(
    distance_mm: float,
    speed_mm_s: float,
    *,
    min_frames: int,
) -> int:
    if distance_mm <= 0.0:
        return min_frames
    duration_s = distance_mm / speed_mm_s
    return max(min_frames, round(duration_s * FPS))


def _travel(
    solver: PlanarIkSolver,
    q_seed: np.ndarray,
    start: CanvasUV,
    end: CanvasUV,
) -> tuple[list[list[float]], np.ndarray]:
    distance_mm = _canvas_distance_mm(start, end, solver.model)
    num_frames = _frames_for_distance_mm(
        distance_mm, TRAVEL_SPEED_MM_S, min_frames=MIN_TRAVEL_FRAMES
    )
    return _interpolate_segment(
        solver,
        q_seed,
        start,
        end,
        num_frames,
        z_offset_m=TRAVEL_LIFT_MM / 1000.0,
    )


def _draw_segment(
    solver: PlanarIkSolver,
    q_seed: np.ndarray,
    start: CanvasUV,
    end: CanvasUV,
) -> tuple[list[list[float]], np.ndarray]:
    distance_mm = _canvas_distance_mm(start, end, solver.model)
    num_frames = _frames_for_distance_mm(
        distance_mm, DRAW_SPEED_MM_S, min_frames=MIN_DRAW_FRAMES
    )
    return _interpolate_segment(solver, q_seed, start, end, num_frames)


def _interpolate_segment(
    solver: PlanarIkSolver,
    q_seed: np.ndarray,
    start: CanvasUV,
    end: CanvasUV,
    num_frames: int,
    *,
    z_offset_m: float = 0.0,
) -> tuple[list[list[float]], np.ndarray]:
    if num_frames < 1:
        raise ValueError("num_frames must be at least 1")

    start_xyz = solver.uv_to_xyz(start.u, start.v)
    end_xyz = solver.uv_to_xyz(end.u, end.v)
    frames: list[list[float]] = []
    q = q_seed.copy()
    preserve_seed_at_start = z_offset_m <= 0.0

    for step in range(num_frames):
        t = step / (num_frames - 1) if num_frames > 1 else 1.0
        if step == 0 and num_frames > 1 and preserve_seed_at_start:
            frames.append(q.astype(float).tolist())
            continue
        xyz = start_xyz + t * (end_xyz - start_xyz)
        if z_offset_m > 0.0:
            xyz = xyz.copy()
            xyz[2] += z_offset_m
        joints = solver.joints_for_xyz(xyz, q)
        q = _numpy_joints(joints)
        frames.append(joints)

    return frames, q


def _numpy_joints(joints: list[float]) -> np.ndarray:
    return np.array(joints, dtype=float)


def estimate_duration_seconds(num_frames: int, fps: int) -> float:
    return num_frames / fps

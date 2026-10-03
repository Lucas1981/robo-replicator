import math
from dataclasses import dataclass

from app.services.robot_config import (
    CANVAS_HALF_EXTENT_LIFT,
    CANVAS_HALF_EXTENT_PAN,
    CANVAS_MARGIN,
    FRAMES_PEN_SETTLE,
    FRAMES_PER_UNIT,
    FRAMES_TRAVEL,
    HOME_POSE,
    MIN_DRAW_FRAMES,
    PEN_DOWN,
    PEN_UP,
)
from app.services.svg_parser import ParsedSvg


@dataclass(frozen=True)
class CanvasPoint:
    pan: float
    lift: float


def canvas_to_joints(point: CanvasPoint, pen_down: bool) -> list[float]:
    return [
        HOME_POSE["shoulder_pan"] + point.pan * CANVAS_HALF_EXTENT_PAN,
        HOME_POSE["shoulder_lift"] + point.lift * CANVAS_HALF_EXTENT_LIFT,
        HOME_POSE["elbow_flex"],
        HOME_POSE["wrist_flex"],
        HOME_POSE["wrist_roll"],
        PEN_DOWN if pen_down else PEN_UP,
    ]


def build_trajectory(parsed: ParsedSvg) -> list[list[float]]:
    normalized_paths = _normalize_paths(parsed.paths)
    trajectory: list[list[float]] = []
    current = CanvasPoint(0.0, 0.0)

    for path in normalized_paths:
        if len(path) < 2:
            continue

        start = path[0]
        trajectory.extend(_travel(current, start))
        trajectory.extend([canvas_to_joints(start, pen_down=True)] * FRAMES_PEN_SETTLE)

        for segment_start, segment_end in zip(path, path[1:]):
            trajectory.extend(_draw_segment(segment_start, segment_end))

        trajectory.extend([canvas_to_joints(path[-1], pen_down=False)] * FRAMES_PEN_SETTLE)
        current = path[-1]

    if not trajectory:
        raise ValueError("SVG paths produced an empty robot trajectory.")

    return trajectory


def _normalize_paths(paths: list[list[tuple[float, float]]]) -> list[list[CanvasPoint]]:
    all_points = [point for path in paths for point in path]
    xs = [point[0] for point in all_points]
    ys = [point[1] for point in all_points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span = max(max_x - min_x, max_y - min_y, 1.0)
    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0
    scale = (1.0 - CANVAS_MARGIN * 2.0) / (span / 2.0)

    normalized_paths: list[list[CanvasPoint]] = []
    for path in paths:
        normalized_path = [
            CanvasPoint(pan=(x - center_x) * scale, lift=-(y - center_y) * scale) for x, y in path
        ]
        normalized_paths.append(normalized_path)
    return normalized_paths


def _travel(start: CanvasPoint, end: CanvasPoint) -> list[list[float]]:
    return _interpolate_poses(start, end, pen_down=False, num_frames=FRAMES_TRAVEL)


def _draw_segment(start: CanvasPoint, end: CanvasPoint) -> list[list[float]]:
    distance = math.hypot(end.pan - start.pan, end.lift - start.lift)
    num_frames = max(MIN_DRAW_FRAMES, int(distance * FRAMES_PER_UNIT))
    return _interpolate_poses(start, end, pen_down=True, num_frames=num_frames)


def _interpolate_poses(
    start: CanvasPoint,
    end: CanvasPoint,
    *,
    pen_down: bool,
    num_frames: int,
) -> list[list[float]]:
    if num_frames < 1:
        raise ValueError("num_frames must be at least 1")
    if num_frames == 1:
        return [canvas_to_joints(end, pen_down)]

    frames: list[list[float]] = []
    for step in range(num_frames):
        t = step / (num_frames - 1)
        point = CanvasPoint(
            pan=_lerp(start.pan, end.pan, t),
            lift=_lerp(start.lift, end.lift, t),
        )
        frames.append(canvas_to_joints(point, pen_down))
    return frames


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def estimate_duration_seconds(num_frames: int, fps: int) -> float:
    return num_frames / fps

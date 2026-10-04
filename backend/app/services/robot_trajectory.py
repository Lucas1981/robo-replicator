import json
import math
from dataclasses import dataclass
from pathlib import Path

from app.services.robot_config import (
    CANVAS_ASPECT,
    CANVAS_HALF_EXTENT_LIFT,
    CANVAS_HALF_EXTENT_PAN,
    CANVAS_HEIGHT_MM,
    CANVAS_MARGIN,
    CANVAS_WIDTH_MM,
    DRAW_SPEED_MM_S,
    FPS,
    FRAMES_PEN_SETTLE,
    HOME_POSE,
    MIN_DRAW_FRAMES,
    MIN_TRAVEL_FRAMES,
    PEN_DOWN,
    PEN_UP,
    TRAVEL_SPEED_MM_S,
)
from app.services.svg_parser import ParsedSvg


@dataclass(frozen=True)
class CanvasPoint:
    pan: float
    lift: float


@dataclass(frozen=True)
class CanvasMapping:
    """SVG viewBox → portrait A4 robot canvas transform."""

    svg_width: float
    svg_height: float
    canvas_width_mm: float
    canvas_height_mm: float
    canvas_aspect: float
    scale: float
    pan_min: float
    pan_max: float
    lift_min: float
    lift_max: float
    pan_pad: float
    lift_pad: float


@dataclass(frozen=True)
class TrajectoryResult:
    frames: list[list[float]]
    mapping: CanvasMapping


def canvas_to_joints(point: CanvasPoint, pen_down: bool) -> list[float]:
    return [
        HOME_POSE["shoulder_pan"] + point.pan * CANVAS_HALF_EXTENT_PAN,
        HOME_POSE["shoulder_lift"] + point.lift * CANVAS_HALF_EXTENT_LIFT,
        HOME_POSE["elbow_flex"],
        HOME_POSE["wrist_flex"],
        HOME_POSE["wrist_roll"],
        PEN_DOWN if pen_down else PEN_UP,
    ]


def build_trajectory(parsed: ParsedSvg) -> TrajectoryResult:
    mapping = compute_canvas_mapping(parsed.width, parsed.height)
    canvas_paths = map_svg_paths_to_canvas(parsed.paths, mapping)
    trajectory: list[list[float]] = []
    current = CanvasPoint(0.0, 0.0)

    for path in canvas_paths:
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

    return TrajectoryResult(frames=trajectory, mapping=mapping)


def compute_canvas_mapping(svg_width: float, svg_height: float) -> CanvasMapping:
    if svg_width <= 0 or svg_height <= 0:
        raise ValueError("SVG width and height must be positive.")

    inset = CANVAS_MARGIN
    pan_min = -CANVAS_ASPECT * (1.0 - inset)
    pan_max = CANVAS_ASPECT * (1.0 - inset)
    lift_min = -(1.0 - inset)
    lift_max = 1.0 - inset

    pan_span = pan_max - pan_min
    lift_span = lift_max - lift_min
    scale = min(pan_span / svg_width, lift_span / svg_height)

    scaled_width = svg_width * scale
    scaled_height = svg_height * scale
    pan_pad = (pan_span - scaled_width) / 2.0
    lift_pad = (lift_span - scaled_height) / 2.0

    return CanvasMapping(
        svg_width=svg_width,
        svg_height=svg_height,
        canvas_width_mm=CANVAS_WIDTH_MM,
        canvas_height_mm=CANVAS_HEIGHT_MM,
        canvas_aspect=CANVAS_ASPECT,
        scale=scale,
        pan_min=pan_min,
        pan_max=pan_max,
        lift_min=lift_min,
        lift_max=lift_max,
        pan_pad=pan_pad,
        lift_pad=lift_pad,
    )


def map_svg_paths_to_canvas(
    paths: list[list[tuple[float, float]]],
    mapping: CanvasMapping,
) -> list[list[CanvasPoint]]:
    return [[svg_point_to_canvas(x, y, mapping) for x, y in path] for path in paths]


def svg_point_to_canvas(x: float, y: float, mapping: CanvasMapping) -> CanvasPoint:
    pan = mapping.pan_min + mapping.pan_pad + x * mapping.scale
    lift = mapping.lift_max - mapping.lift_pad - y * mapping.scale
    return CanvasPoint(pan=pan, lift=lift)


def write_draw_source_meta(
    dataset_root: Path,
    mapping: CanvasMapping,
    *,
    source_filename: str,
) -> Path:
    meta_dir = dataset_root / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_filename": source_filename,
        "svg_width": mapping.svg_width,
        "svg_height": mapping.svg_height,
        "canvas_width_mm": mapping.canvas_width_mm,
        "canvas_height_mm": mapping.canvas_height_mm,
        "canvas_aspect": mapping.canvas_aspect,
        "transform": {
            "scale": mapping.scale,
            "pan_min": mapping.pan_min,
            "pan_max": mapping.pan_max,
            "lift_min": mapping.lift_min,
            "lift_max": mapping.lift_max,
            "pan_pad": mapping.pan_pad,
            "lift_pad": mapping.lift_pad,
        },
        "motion": {
            "fps": FPS,
            "draw_speed_mm_s": DRAW_SPEED_MM_S,
            "travel_speed_mm_s": TRAVEL_SPEED_MM_S,
        },
    }
    path = meta_dir / "draw_source.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _canvas_mm_scale() -> tuple[float, float]:
    inset = CANVAS_MARGIN
    pan_span = 2.0 * CANVAS_ASPECT * (1.0 - inset)
    lift_span = 2.0 * (1.0 - inset)
    drawable_width_mm = CANVAS_WIDTH_MM * (1.0 - 2.0 * inset)
    drawable_height_mm = CANVAS_HEIGHT_MM * (1.0 - 2.0 * inset)
    return drawable_width_mm / pan_span, drawable_height_mm / lift_span


def _canvas_distance_mm(start: CanvasPoint, end: CanvasPoint) -> float:
    mm_per_pan, mm_per_lift = _canvas_mm_scale()
    dx_mm = (end.pan - start.pan) * mm_per_pan
    dy_mm = (end.lift - start.lift) * mm_per_lift
    return math.hypot(dx_mm, dy_mm)


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


def _travel(start: CanvasPoint, end: CanvasPoint) -> list[list[float]]:
    distance_mm = _canvas_distance_mm(start, end)
    num_frames = _frames_for_distance_mm(
        distance_mm, TRAVEL_SPEED_MM_S, min_frames=MIN_TRAVEL_FRAMES
    )
    return _interpolate_poses(start, end, pen_down=False, num_frames=num_frames)


def _draw_segment(start: CanvasPoint, end: CanvasPoint) -> list[list[float]]:
    distance_mm = _canvas_distance_mm(start, end)
    num_frames = _frames_for_distance_mm(
        distance_mm, DRAW_SPEED_MM_S, min_frames=MIN_DRAW_FRAMES
    )
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

#!/usr/bin/env python3
"""Build a LeRobot replay zip from the canvas-box diagnostic SVG.

The SVG draws a portrait A4 rectangle with both diagonals (6 lines total).
Use the output zip on a follower arm to verify SVG → canvas corner mapping.

Usage:
    python backend/resources/diagnostics/generate_canvas_box_dataset.py
    python backend/resources/diagnostics/generate_canvas_box_dataset.py \\
        --svg backend/resources/diagnostics/canvas-box.svg \\
        --output backend/resources/diagnostics/canvas-box-draw.zip
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.robot_config import FPS  # noqa: E402
from app.services.robot_dataset import (  # noqa: E402
    RobotDatasetError,
    _directory_to_zip,
    write_dataset_directory,
)
from app.services.robot_trajectory import build_trajectory, estimate_duration_seconds  # noqa: E402
from app.services.svg_parser import parse_svg_paths  # noqa: E402

DIAGNOSTICS_DIR = Path(__file__).resolve().parent
DEFAULT_SVG = DIAGNOSTICS_DIR / "canvas-box.svg"
DEFAULT_ZIP = DIAGNOSTICS_DIR / "canvas-box-draw.zip"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--svg",
        type=Path,
        default=DEFAULT_SVG,
        help=f"Input diagnostic SVG (default: {DEFAULT_SVG.name})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_ZIP,
        help=f"Output replay zip (default: {DEFAULT_ZIP.name})",
    )
    parser.add_argument(
        "--task",
        default="Diagnostic: draw canvas box with X",
        help="Task label stored in the dataset",
    )
    args = parser.parse_args()

    svg_path = args.svg.resolve()
    output_path = args.output.resolve()

    if not svg_path.is_file():
        raise SystemExit(f"SVG not found: {svg_path}")

    svg_bytes = svg_path.read_bytes()
    temp_dir = Path(tempfile.mkdtemp(prefix="canvas-box-draw-"))

    try:
        parsed = parse_svg_paths(svg_bytes)
        result = build_trajectory(parsed)
        write_dataset_directory(svg_bytes, temp_dir, svg_path.name, args.task)
        zip_bytes = _directory_to_zip(temp_dir)
    except (RobotDatasetError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(zip_bytes)

    mapping = result.mapping
    duration = estimate_duration_seconds(len(result.frames), FPS)
    print(f"Wrote {output_path} ({len(zip_bytes)} bytes)")
    print(f"  paths: {len(parsed.paths)}  frames: {len(result.frames)}  duration: {duration:.1f}s @ {FPS} fps")
    print(
        f"  svg: {mapping.svg_width:g}x{mapping.svg_height:g}  "
        f"scale: {mapping.scale:.6g}  canvas: {mapping.canvas_width_mm:g}x{mapping.canvas_height_mm:g} mm"
    )
    print()
    print("Replay on hardware:")
    print(f"  unzip -d /tmp/canvas-box-draw {output_path}")
    print("  cd /tmp/canvas-box-draw")
    print("  SO101_PORT=/dev/tty.usbmodemXXXX SO101_ID=YOUR_ARM_ID ./replay-follower.sh")


if __name__ == "__main__":
    main()

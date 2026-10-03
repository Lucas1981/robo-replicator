#!/usr/bin/env python3
"""Build draw-sample.zip from paths-sample.svg for DEBUG_SKIP_ROBOT_STEP."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import DEBUG_DRAW_SAMPLE_PATH, DEBUG_PATHS_SAMPLE_PATH  # noqa: E402
from app.services.robot_dataset import _directory_to_zip, write_dataset_directory  # noqa: E402


def main() -> None:
    svg_path = DEBUG_PATHS_SAMPLE_PATH
    if not svg_path.is_file():
        raise SystemExit(f"Paths sample not found: {svg_path}")

    svg_bytes = svg_path.read_bytes()
    temp_dir = Path(tempfile.mkdtemp(prefix="draw-sample-"))
    try:
        write_dataset_directory(
            svg_bytes,
            temp_dir,
            svg_path.name,
            task="Draw paths from outline sample",
        )
        zip_bytes = _directory_to_zip(temp_dir)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    DEBUG_DRAW_SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEBUG_DRAW_SAMPLE_PATH.write_bytes(zip_bytes)
    print(f"Wrote {DEBUG_DRAW_SAMPLE_PATH} ({len(zip_bytes)} bytes)")


if __name__ == "__main__":
    main()

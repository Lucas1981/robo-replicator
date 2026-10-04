#!/usr/bin/env python3
"""Replay a LeRobotDataset in Rerun with a 3D SO-101 URDF model and joint plots."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

BACKEND_SCRIPT = Path(__file__).resolve().parent.parent / "backend" / "scripts" / "dataset_urdf_viz.py"

if __name__ == "__main__":
    if not BACKEND_SCRIPT.is_file():
        raise SystemExit(f"Missing visualization script: {BACKEND_SCRIPT}")
    sys.argv[0] = str(BACKEND_SCRIPT)
    runpy.run_path(str(BACKEND_SCRIPT), run_name="__main__")

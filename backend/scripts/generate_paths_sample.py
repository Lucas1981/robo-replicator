#!/usr/bin/env python3
"""Generate backend/resources/paths-sample.svg from outline-sample.png."""

from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import DEBUG_OUTLINE_SAMPLE_PATH, RESOURCES_DIR  # noqa: E402
from app.services.vectorize import _bitmap_to_svg  # noqa: E402

OUTPUT = RESOURCES_DIR / "paths-sample.svg"


def main() -> None:
    if not DEBUG_OUTLINE_SAMPLE_PATH.is_file():
        raise SystemExit(f"Missing outline sample: {DEBUG_OUTLINE_SAMPLE_PATH}")

    outline_bytes = DEBUG_OUTLINE_SAMPLE_PATH.read_bytes()
    svg_bytes = _bitmap_to_svg(outline_bytes, DEBUG_OUTLINE_SAMPLE_PATH.name)
    OUTPUT.write_bytes(svg_bytes)
    print(f"Wrote {OUTPUT} ({len(svg_bytes)} bytes)")


if __name__ == "__main__":
    main()

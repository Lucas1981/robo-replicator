import asyncio
from pathlib import Path

from app.services.image_validation import ValidatedImage

STUB_DELAY_SECONDS = 0.8


def output_filename(source_filename: str) -> str:
    stem = Path(source_filename).stem or "output"
    return f"{stem}-outline.svg"


def build_stub_outline_svg(image: ValidatedImage) -> str:
    label = _escape_xml(Path(image.filename).stem)
    source = _escape_xml(image.content_type)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="400" height="400">
  <rect width="100%" height="100%" fill="#fff"/>
  <rect x="40" y="40" width="320" height="320" fill="none" stroke="#111" stroke-width="3"/>
  <rect x="120" y="120" width="160" height="160" fill="none" stroke="#111" stroke-width="2"/>
  <line x1="40" y1="200" x2="360" y2="200" stroke="#111" stroke-width="2"/>
  <line x1="200" y1="40" x2="200" y2="360" stroke="#111" stroke-width="2"/>
  <text x="200" y="24" text-anchor="middle" font-family="sans-serif" font-size="11" fill="#555">
    Stub outline from backend ({image.width}×{image.height})
  </text>
  <text x="200" y="380" text-anchor="middle" font-family="sans-serif" font-size="12" fill="#555">
    {label} ({source})
  </text>
</svg>"""


async def generate_outline(image: ValidatedImage) -> str:
    """Placeholder for future LLM / vector pipeline. Returns a stub SVG for now."""
    await asyncio.sleep(STUB_DELAY_SECONDS)
    return build_stub_outline_svg(image)


def _escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )

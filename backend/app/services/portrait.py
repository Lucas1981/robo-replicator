"""Bridge to scripts/portrait_cartoon.py (Vin), so the API and the CLI share one pipeline."""

import importlib.util
from pathlib import Path

from app.config import BACKEND_ROOT

PORTRAIT_SCRIPT = BACKEND_ROOT.parent / "scripts" / "portrait_cartoon.py"

_spec = importlib.util.spec_from_file_location("portrait_cartoon", PORTRAIT_SCRIPT)
portrait_cartoon = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(portrait_cartoon)

CartoonError = portrait_cartoon.CartoonError
CAMERA_DIR: Path = portrait_cartoon.CAMERA_DIR
save_photo = portrait_cartoon.save_photo
cartoonize = portrait_cartoon.cartoonize


def find_photo(name: str) -> Path:
    """Resolve a saved photo by its bare file name, refusing anything outside camera/."""
    path = (CAMERA_DIR / name).resolve()
    if path.parent != CAMERA_DIR.resolve() or path.suffix.lower() != ".jpg" or not path.is_file():
        raise CartoonError(f"Unknown photo: {name}")
    return path

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parent.parent
RESOURCES_DIR = BACKEND_ROOT / "resources"
DEFAULT_DEBUG_OUTLINE_SAMPLE = RESOURCES_DIR / "outline-sample.png"
DEFAULT_DEBUG_PATHS_SAMPLE = RESOURCES_DIR / "paths-sample.svg"
DEFAULT_DEBUG_DRAW_SAMPLE = RESOURCES_DIR / "draw-sample.zip"

load_dotenv(BACKEND_ROOT / ".env")


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name, str(default)).strip().lower()
    return value in {"1", "true", "yes", "on"}

CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
MIN_DIMENSION = int(os.getenv("MIN_IMAGE_DIMENSION", "64"))
MAX_DIMENSION = int(os.getenv("MAX_IMAGE_DIMENSION", "8192"))

# DALL-E 2 edits require square PNG under 4 MB.
DALLE2_MAX_BYTES = 4 * 1024 * 1024
DALLE2_EDIT_SIZE = int(os.getenv("DALLE2_EDIT_SIZE", "1024"))

OPENAI_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1").strip()

# When true, skip OpenAI and return DEBUG_OUTLINE_SAMPLE_PATH instead.
DEBUG_SKIP_LLM_STEP = _env_bool("DEBUG_SKIP_LLM_STEP", False)
DEBUG_OUTLINE_SAMPLE_PATH = Path(
    os.getenv("DEBUG_OUTLINE_SAMPLE_PATH", str(DEFAULT_DEBUG_OUTLINE_SAMPLE))
).resolve()

# When true, skip bitmap vectorization and return DEBUG_PATHS_SAMPLE_PATH instead.
DEBUG_SKIP_VECTORIZE_STEP = _env_bool("DEBUG_SKIP_VECTORIZE_STEP", False)
DEBUG_PATHS_SAMPLE_PATH = Path(
    os.getenv("DEBUG_PATHS_SAMPLE_PATH", str(DEFAULT_DEBUG_PATHS_SAMPLE))
).resolve()

DEBUG_SKIP_ROBOT_STEP = _env_bool("DEBUG_SKIP_ROBOT_STEP", False)
DEBUG_DRAW_SAMPLE_PATH = Path(
    os.getenv("DEBUG_DRAW_SAMPLE_PATH", str(DEFAULT_DEBUG_DRAW_SAMPLE))
).resolve()

OUTLINE_PROMPT = os.getenv(
    "OUTLINE_PROMPT",
    (
        "Convert this into a very simple black-and-white outline drawing of the same subject. "
        "Use clean, minimal black line art on a pure white background. "
        "No grayscale, no shading, no color, no fills, and no textures. "
        "Preserve the main contours and recognizable silhouette with as few strokes as possible. "
        "The result should look like a cartoon line drawing suitable for a pen plotter robot."
    ),
)

ACCEPTED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}


class MissingApiKeyError(RuntimeError):
    """Raised when OPENAI_API_KEY is not configured."""


def get_openai_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise MissingApiKeyError(
            "OPENAI_API_KEY is not set. Copy backend/.env.example to backend/.env "
            "and add your OpenAI API key."
        )
    return api_key

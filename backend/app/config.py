import os

CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
MIN_DIMENSION = int(os.getenv("MIN_IMAGE_DIMENSION", "64"))
MAX_DIMENSION = int(os.getenv("MAX_IMAGE_DIMENSION", "8192"))

ACCEPTED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}

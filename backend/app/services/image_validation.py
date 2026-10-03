from dataclasses import dataclass
from io import BytesIO

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.config import (
    ACCEPTED_CONTENT_TYPES,
    MAX_DIMENSION,
    MAX_UPLOAD_BYTES,
    MIN_DIMENSION,
)


@dataclass(frozen=True)
class ValidatedImage:
    filename: str
    content_type: str
    width: int
    height: int
    data: bytes


class ImageValidationError(ValueError):
    pass


async def validate_upload(file: UploadFile) -> ValidatedImage:
    if not file.filename:
        raise ImageValidationError("A file must be provided.")

    content_type = file.content_type or ""
    if content_type not in ACCEPTED_CONTENT_TYPES:
        raise ImageValidationError("Use a JPEG, PNG, WebP, or GIF image.")

    data = await file.read()
    if not data:
        raise ImageValidationError("The file is empty.")

    if len(data) > MAX_UPLOAD_BYTES:
        raise ImageValidationError("Image must be 10 MB or smaller.")

    try:
        with Image.open(BytesIO(data)) as image:
            width, height = image.size
    except UnidentifiedImageError as exc:
        raise ImageValidationError("The file does not appear to be a valid image.") from exc

    if width < MIN_DIMENSION or height < MIN_DIMENSION:
        raise ImageValidationError(
            f"Image must be at least {MIN_DIMENSION}×{MIN_DIMENSION} pixels."
        )

    if width > MAX_DIMENSION or height > MAX_DIMENSION:
        raise ImageValidationError(
            f"Image must be at most {MAX_DIMENSION}×{MAX_DIMENSION} pixels."
        )

    return ValidatedImage(
        filename=file.filename,
        content_type=content_type,
        width=width,
        height=height,
        data=data,
    )

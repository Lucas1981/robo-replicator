from io import BytesIO

from PIL import Image

from app.config import DALLE2_EDIT_SIZE, DALLE2_MAX_BYTES
from app.services.image_validation import ValidatedImage


def prepare_for_dalle2_edit(image: ValidatedImage) -> tuple[bytes, bytes]:
    """Return (source_png, mask_png) as square PNG bytes for DALL-E 2 edits."""
    with Image.open(BytesIO(image.data)) as opened:
        rgba = opened.convert("RGBA")

    square = _pad_to_square(rgba, fill=(255, 255, 255, 255))
    resized = square.resize((DALLE2_EDIT_SIZE, DALLE2_EDIT_SIZE), Image.Resampling.LANCZOS)

    source_bytes = _encode_png(resized, max_bytes=DALLE2_MAX_BYTES)
    mask = Image.new("RGBA", (DALLE2_EDIT_SIZE, DALLE2_EDIT_SIZE), (0, 0, 0, 0))
    mask_bytes = _encode_png(mask, max_bytes=DALLE2_MAX_BYTES)

    return source_bytes, mask_bytes


def prepare_for_gpt_image_edit(image: ValidatedImage) -> bytes:
    """Return PNG bytes for GPT image model edits (no square requirement)."""
    with Image.open(BytesIO(image.data)) as opened:
        rgba = opened.convert("RGBA")

    longest = max(rgba.width, rgba.height, 1)
    if longest > 2048:
        scale = 2048 / longest
        rgba = rgba.resize(
            (max(1, int(rgba.width * scale)), max(1, int(rgba.height * scale))),
            Image.Resampling.LANCZOS,
        )

    return _encode_png(rgba, max_bytes=50 * 1024 * 1024)


def _pad_to_square(image: Image.Image, fill: tuple[int, int, int, int]) -> Image.Image:
    width, height = image.size
    side = max(width, height)
    canvas = Image.new("RGBA", (side, side), fill)
    offset = ((side - width) // 2, (side - height) // 2)
    canvas.paste(image, offset, image if image.mode == "RGBA" else None)
    return canvas


def _encode_png(image: Image.Image, max_bytes: int) -> bytes:
    for compress_level in (6, 9):
        buffer = BytesIO()
        image.save(buffer, format="PNG", compress_level=compress_level)
        data = buffer.getvalue()
        if len(data) <= max_bytes:
            return data

    raise ValueError(
        "Image is too large for the OpenAI image edit API after compression. "
        "Try a smaller source image."
    )

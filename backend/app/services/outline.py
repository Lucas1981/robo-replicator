import asyncio
import base64
import logging
from io import BytesIO
from pathlib import Path

import httpx
from openai import APIStatusError, OpenAI
from PIL import Image

from app.config import (
    DALLE2_EDIT_SIZE,
    OPENAI_IMAGE_MODEL,
    OUTLINE_PROMPT,
    get_openai_api_key,
)
from app.services.image_prep import prepare_for_dalle2_edit, prepare_for_gpt_image_edit
from app.services.image_validation import ValidatedImage

logger = logging.getLogger(__name__)

GPT_IMAGE_MODELS = {"gpt-image-1", "gpt-image-1-mini", "gpt-image-1.5", "chatgpt-image-latest"}


class OutlineGenerationError(RuntimeError):
    """Raised when OpenAI fails to produce an outline image."""


def output_filename(source_filename: str) -> str:
    stem = Path(source_filename).stem or "output"
    return f"{stem}-outline.png"


def output_content_type() -> str:
    return "image/png"


async def generate_outline(image: ValidatedImage) -> bytes:
    """Generate a black-and-white outline drawing via the OpenAI image edit API."""
    api_key = get_openai_api_key()
    model = OPENAI_IMAGE_MODEL

    return await asyncio.to_thread(_generate_outline_sync, api_key, model, image)


def _generate_outline_sync(api_key: str, model: str, image: ValidatedImage) -> bytes:
    client = OpenAI(api_key=api_key)
    source_file = image.filename

    logger.info(
        "OpenAI request starting in outline.py for source file %r (model=%s, size=%dx%d)",
        source_file,
        model,
        image.width,
        image.height,
    )

    try:
        if model == "dall-e-2":
            return _generate_with_dalle2(client, image)
        if model in GPT_IMAGE_MODELS:
            return _generate_with_gpt_image(client, model, image)
        raise OutlineGenerationError(
            f"Unsupported OPENAI_IMAGE_MODEL '{model}'. "
            "Use 'gpt-image-1' or another GPT image model."
        )
    except OutlineGenerationError:
        raise
    except APIStatusError as exc:
        _log_openai_api_error(source_file, model, exc)
        raise OutlineGenerationError(_format_openai_error(source_file, model, exc)) from exc
    except Exception as exc:
        logger.exception(
            "Unexpected error in outline.py while processing source file %r (model=%s)",
            source_file,
            model,
        )
        raise OutlineGenerationError(
            f"OpenAI image generation failed for {source_file!r}: {exc}"
        ) from exc


def _generate_with_dalle2(client: OpenAI, image: ValidatedImage) -> bytes:
    source_bytes, mask_bytes = prepare_for_dalle2_edit(image)

    logger.debug(
        "Prepared DALL-E 2 payload for %r: source=%d bytes, mask=%d bytes",
        image.filename,
        len(source_bytes),
        len(mask_bytes),
    )

    response = client.images.edit(
        model="dall-e-2",
        image=("source.png", source_bytes, "image/png"),
        mask=("mask.png", mask_bytes, "image/png"),
        prompt=OUTLINE_PROMPT,
        n=1,
        size=f"{DALLE2_EDIT_SIZE}x{DALLE2_EDIT_SIZE}",
    )

    item = response.data[0]
    if item.b64_json:
        return _decode_response_image(item.b64_json, image.filename)

    if item.url:
        return _download_image_url(item.url, image.filename)

    raise OutlineGenerationError(
        f"OpenAI returned no image data for source file {image.filename!r}."
    )


def _generate_with_gpt_image(client: OpenAI, model: str, image: ValidatedImage) -> bytes:
    source_bytes = prepare_for_gpt_image_edit(image)

    logger.debug(
        "Prepared GPT image payload for %r: source=%d bytes",
        image.filename,
        len(source_bytes),
    )

    response = client.images.edit(
        model=model,
        image=("source.png", source_bytes, "image/png"),
        prompt=OUTLINE_PROMPT,
        n=1,
        size="1024x1024",
        background="opaque",
        output_format="png",
    )

    item = response.data[0]
    if item.b64_json:
        return _decode_response_image(item.b64_json, image.filename)

    raise OutlineGenerationError(
        f"OpenAI returned no image data for source file {image.filename!r}."
    )


def _decode_response_image(b64_json: str | None, source_file: str) -> bytes:
    if not b64_json:
        raise OutlineGenerationError(
            f"OpenAI returned an empty image payload for source file {source_file!r}."
        )

    raw = base64.b64decode(b64_json)
    with Image.open(BytesIO(raw)) as decoded:
        decoded.verify()
    return raw


def _download_image_url(url: str, source_file: str) -> bytes:
    response = httpx.get(url, timeout=60.0)
    response.raise_for_status()
    raw = response.content
    with Image.open(BytesIO(raw)) as decoded:
        decoded.verify()
    return raw


def _log_openai_api_error(source_file: str, model: str, exc: APIStatusError) -> None:
    body = exc.response.text if exc.response is not None else "(no response body)"
    logger.error(
        "OpenAI API error in outline.py for source file %r (model=%s, status=%s): %s",
        source_file,
        model,
        exc.status_code,
        body,
    )


def _format_openai_error(source_file: str, model: str, exc: APIStatusError) -> str:
    detail = exc.message
    try:
        payload = exc.response.json()
        detail = payload.get("error", {}).get("message", detail)
    except Exception:
        pass

    hint = ""
    if model == "dall-e-2" and "does not exist" in detail.lower():
        hint = " Try setting OPENAI_IMAGE_MODEL=gpt-image-1 in backend/.env."

    return (
        f"OpenAI rejected the request for source file {source_file!r} "
        f"(model={model}): {detail}.{hint}"
    )

import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response

from app.services.image_validation import ImageValidationError, validate_upload
from app.services.portrait import CartoonError, cartoonize, find_photo, save_photo

router = APIRouter(prefix="/portrait", tags=["portrait"])
logger = logging.getLogger(__name__)


@router.post("/photo")
async def save_portrait_photo(file: UploadFile = File(...)) -> dict[str, str]:
    """Save a webcam capture to camera/ and return its file name."""
    try:
        validated = await validate_upload(file)
        path = save_photo(validated.data)
    except ImageValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except CartoonError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info("Saved portrait photo %s (%dx%d)", path.name, validated.width, validated.height)
    return {"photo": path.name}


@router.post("/cartoon")
async def create_portrait_cartoon(photo: str = Form(...)) -> Response:
    """Let Vin turn a saved photo into a cartoon SVG, saved to image/."""
    try:
        photo_path = find_photo(photo)
    except CartoonError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    logger.info("Vin is sketching %s", photo_path.name)
    try:
        svg_path = await run_in_threadpool(cartoonize, photo_path)
    except CartoonError as exc:
        status = 503 if "NEBIUS_API_KEY" in str(exc) else 502
        logger.error("Vin failed for %s: %s", photo_path.name, exc)
        raise HTTPException(status_code=status, detail=str(exc)) from exc

    logger.info("Saved cartoon %s", svg_path.name)
    headers = {"Content-Disposition": f'attachment; filename="{svg_path.name}"'}
    return Response(content=svg_path.read_bytes(), media_type="image/svg+xml", headers=headers)

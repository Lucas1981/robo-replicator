import logging

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.config import MissingApiKeyError, OPENAI_IMAGE_MODEL
from app.services.image_validation import ImageValidationError, validate_upload
from app.services.outline import (
    OutlineGenerationError,
    generate_outline,
    output_content_type,
    output_filename,
)

router = APIRouter(tags=["process"])
logger = logging.getLogger(__name__)


@router.post("/process")
async def process_image(file: UploadFile = File(...)) -> Response:
    logger.info("Received process request for %s", file.filename)
    try:
        validated = await validate_upload(file)
        logger.info(
            "Validated %s (%dx%d), calling %s",
            validated.filename,
            validated.width,
            validated.height,
            OPENAI_IMAGE_MODEL,
        )
        outline_bytes = await generate_outline(validated)
        logger.info("Outline ready for %s (%d bytes)", validated.filename, len(outline_bytes))
    except ImageValidationError as exc:
        logger.warning("Validation failed for %s: %s", file.filename, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MissingApiKeyError as exc:
        logger.error("Missing API key while processing %s", file.filename)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except OutlineGenerationError as exc:
        logger.error("Outline generation failed for %s: %s", file.filename, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        logger.warning("Bad request for %s: %s", file.filename, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    filename = output_filename(validated.filename)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}

    return Response(content=outline_bytes, media_type=output_content_type(), headers=headers)

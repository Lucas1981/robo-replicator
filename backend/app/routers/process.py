from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.services.image_validation import ImageValidationError, validate_upload
from app.services.outline import generate_outline, output_filename

router = APIRouter(tags=["process"])


@router.post("/process")
async def process_image(file: UploadFile = File(...)) -> Response:
    try:
        validated = await validate_upload(file)
        svg = await generate_outline(validated)
    except ImageValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    filename = output_filename(validated.filename)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}

    return Response(content=svg, media_type="image/svg+xml", headers=headers)

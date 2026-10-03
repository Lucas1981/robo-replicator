import logging

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.config import DEBUG_SKIP_ROBOT_STEP
from app.services.robot_dataset import (
    RobotDatasetError,
    dataset_output_content_type,
    dataset_output_filename,
    svg_to_robot_dataset,
)

router = APIRouter(tags=["robot"])
logger = logging.getLogger(__name__)

ACCEPTED_SVG_TYPES = {
    "image/svg+xml",
    "application/octet-stream",
    "text/xml",
    "application/xml",
}


@router.post("/robot-dataset")
async def create_robot_dataset(file: UploadFile = File(...)) -> Response:
    filename = file.filename or "paths.svg"
    logger.info("Received robot dataset request for %s", filename)

    if not filename.lower().endswith(".svg"):
        raise HTTPException(status_code=400, detail="Upload must be an SVG file (.svg).")

    content_type = (file.content_type or "").split(";", 1)[0].strip().lower()
    if content_type and content_type not in ACCEPTED_SVG_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported content type {content_type!r}. Upload an SVG file.",
        )

    svg_bytes = await file.read()
    if not svg_bytes.strip():
        raise HTTPException(status_code=400, detail="SVG file is empty.")

    if not svg_bytes.lstrip().startswith((b"<?xml", b"<svg", b"<SVG")):
        raise HTTPException(status_code=400, detail="File does not look like SVG XML.")

    try:
        if DEBUG_SKIP_ROBOT_STEP:
            logger.info("Skipping robot dataset build for %s (DEBUG_SKIP_ROBOT_STEP=true)", filename)
        else:
            logger.info("Building LeRobotDataset from SVG %s", filename)

        dataset_bytes = svg_to_robot_dataset(svg_bytes, filename)
        logger.info("Robot dataset ready for %s (%d bytes)", filename, len(dataset_bytes))
    except RobotDatasetError as exc:
        logger.error("Robot dataset export failed for %s: %s", filename, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    output_filename = dataset_output_filename(filename)
    headers = {"Content-Disposition": f'attachment; filename="{output_filename}"'}

    return Response(content=dataset_bytes, media_type=dataset_output_content_type(), headers=headers)

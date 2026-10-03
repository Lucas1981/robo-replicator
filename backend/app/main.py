import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import (
    CORS_ORIGINS,
    DEBUG_OUTLINE_SAMPLE_PATH,
    DEBUG_PATHS_SAMPLE_PATH,
    DEBUG_SKIP_LLM_STEP,
    DEBUG_SKIP_VECTORIZE_STEP,
)
from app.routers import process

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(
    title="Robo Replicator API",
    description="Backend for image-to-robot-drawing pipeline.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in CORS_ORIGINS if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(process.router, prefix="/api")


@app.on_event("startup")
def log_startup_config() -> None:
    if DEBUG_SKIP_LLM_STEP:
        logger.warning(
            "DEBUG_SKIP_LLM_STEP=true — OpenAI outline generation is disabled; "
            "using sample file at %s",
            DEBUG_OUTLINE_SAMPLE_PATH,
        )
    if DEBUG_SKIP_VECTORIZE_STEP:
        logger.warning(
            "DEBUG_SKIP_VECTORIZE_STEP=true — bitmap vectorization is disabled; "
            "using sample file at %s",
            DEBUG_PATHS_SAMPLE_PATH,
        )


@app.get("/api/health")
def health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "debug_skip_llm_step": DEBUG_SKIP_LLM_STEP,
        "debug_skip_vectorize_step": DEBUG_SKIP_VECTORIZE_STEP,
    }

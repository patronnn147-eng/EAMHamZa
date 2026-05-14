"""
EAM ML Prediction Service - FastAPI Entry Point
Version 2.0.0 - Microservice Architecture
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.router import router as ml_router
import uvicorn
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


# ── Lifespan must be defined BEFORE FastAPI() ──────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler (replaces deprecated @app.on_event).
    Logs per-model load status at startup; yields for request handling; cleans up on shutdown.
    """
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("=" * 50)
    logger.info("EAM ML Prediction Service v2.0.0 STARTING")
    logger.info("=" * 50)

    from src.core.model_loader import startup_check
    startup_check()
    logger.info("=" * 50)

    yield  # ← application runs here

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("EAM ML Prediction Service shutting down")


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="EAM ML Prediction Service",
    description="P1-P6 ML predictions for Sagemcom Enterprise Asset Management",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Restrict origins to internal services via env var.
# Default is backend-only; set ALLOWED_ORIGINS=* for local dev.
_allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://backend:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include ML router
app.include_router(ml_router)


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    from src.core.model_loader import load_p1, load_p2, load_p3, load_p4, load_p5, load_p6

    return {
        "status": "healthy",
        "service": "ml-prediction",
        "version": "2.0.0",
        "models": {
            "p1_failure":      load_p1() is not None,
            "p2_failure_type": load_p2() is not None,
            "p3_rul":          load_p3() is not None,
            "p4_anomaly":      load_p4() is not None,
            "p5_priority":     load_p5() is not None,
            "p6_schedule":     load_p6() is not None,
        }
    }


@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "EAM ML Prediction Service",
        "version": "2.0.0",
        "docs":    "/docs",
        "health":  "/health",
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )

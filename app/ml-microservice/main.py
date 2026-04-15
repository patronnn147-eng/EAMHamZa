"""
EAM ML Prediction Service - FastAPI Entry Point
Version 2.0.0 - Microservice Architecture
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.router import router as ml_router
import uvicorn
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="EAM ML Prediction Service",
    description="P1-P6 ML predictions for Sagemcom Enterprise Asset Management",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include ML router
app.include_router(ml_router)


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    from src.model_loader import get_model, _ml_model_p2, _ml_model_p3, _ml_model_p4, _ml_model_p5, _ml_model_p6
    
    return {
        "status": "healthy",
        "service": "ml-prediction",
        "version": "2.0.0",
        "models": {
            "p1_failure": get_model() is not None,
            "p2_failure_type": _ml_model_p2 is not None,
            "p3_rul": _ml_model_p3 is not None,
            "p4_anomaly": _ml_model_p4 is not None,
            "p5_priority": _ml_model_p5 is not None,
            "p6_schedule": _ml_model_p6 is not None,
        }
    }


@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "EAM ML Prediction Service",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# Startup event - log which models are loaded
@app.on_event("startup")
async def startup_event():
    logger.info("=" * 50)
    logger.info("EAM ML Prediction Service v2.0.0 STARTING")
    logger.info("=" * 50)
    
    # Import and trigger model loading
    from src import model_loader
    from src.predictions import MachineLearningService
    
    logger.info("ML models loaded successfully")
    logger.info("=" * 50)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
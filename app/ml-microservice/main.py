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
    level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


_W2_CSV_CANDIDATES = [
    "/app/ai4i2020.csv",
    "/workspace/ai4i2020.csv",
    os.path.join(os.path.dirname(__file__), "ai4i2020.csv"),
    os.path.join(os.path.dirname(__file__), "..", "ai4i2020.csv"),
]

_W2_SENSOR_KEYS = [
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]",
]

_W2_FEATURE_NAMES = [
    "air_temperature",
    "process_temperature",
    "rotational_speed",
    "torque",
    "tool_wear",
]

_W2_PINN_WINDOW = 20  # timesteps per sequence


def _startup_fit_anomaly_ensemble(x_all, rows, feature_names):
    """Fit AnomalyEnsemble on healthy (failure==0) rows. Errors are non-fatal."""
    try:
        from src.anomaly_cusum import fit_anomaly_ensemble

        failure_col = "Machine failure" if "Machine failure" in rows[0] else None
        if failure_col:
            healthy_mask = [
                i
                for i, row in enumerate(rows)
                if row.get(failure_col, "0").strip() in ("0", "0.0", "False")
            ]
            x_healthy = x_all[healthy_mask] if healthy_mask else x_all
        else:
            x_healthy = x_all

        fit_anomaly_ensemble(x_healthy, feature_names)
        logger.info(f"AnomalyEnsemble fitted on {len(x_healthy)} healthy samples.")
    except Exception as e:
        logger.warning(f"AnomalyEnsemble startup fit failed: {e}", exc_info=True)


def _startup_fit_pinn_rul(x_all, rows, rul_col):
    """Fit PINN RUL estimator on sequence/label pairs. Errors are non-fatal."""
    try:
        from src.pinn_rul import create_pinn_estimator, TORCH_AVAILABLE

        if not TORCH_AVAILABLE:
            logger.warning("PINN skipped: PyTorch not available.")
            return

        sequences = []
        rul_labels = []

        if rul_col and rul_col in rows[0]:
            for i in range(_W2_PINN_WINDOW, len(x_all), _W2_PINN_WINDOW):
                seq = x_all[i - _W2_PINN_WINDOW : i]
                try:
                    rul = float(rows[i - 1].get(rul_col, 60))
                except ValueError:
                    rul = 60.0
                sequences.append(seq)
                rul_labels.append(rul)
        else:
            for i in range(_W2_PINN_WINDOW, len(x_all), _W2_PINN_WINDOW):
                seq = x_all[i - _W2_PINN_WINDOW : i]
                wear = seq[-1, 4]  # tool_wear is index 4
                rul = max(0.0, 300.0 - float(wear))
                sequences.append(seq)
                rul_labels.append(rul)

        if len(sequences) < 3:
            logger.warning("PINN startup fit skipped: too few sequences.")
            return

        if len(sequences) > 500:
            step = len(sequences) // 500
            sequences = sequences[::step][:500]
            rul_labels = rul_labels[::step][:500]

        pinn = create_pinn_estimator(reference_rul=60.0)
        pinn.train(sequences, rul_labels, epochs=30, lr=1e-3)
        logger.info(f"PINN RUL fitted on {len(sequences)} sequences.")

    except Exception as e:
        logger.warning(f"PINN startup fit failed: {e}", exc_info=True)


def _fit_wave2_models():
    """
    Fit Wave 2 transient models (AnomalyEnsemble + PINN) from ai4i2020.csv.
    Called once at startup. Failures are logged but do not block the service.

    Both models require training data — they cannot run from a saved pkl.
    - AnomalyEnsemble: fits Isolation Forest baseline on healthy sensor readings
    - PINN RUL: trains physics-informed NN on (sequence, RUL) pairs
    """
    import numpy as np

    csv_path = None
    for p in _W2_CSV_CANDIDATES:
        if os.path.exists(p):
            csv_path = p
            break

    if csv_path is None:
        logger.warning(
            "Wave 2 startup fit skipped: ai4i2020.csv not found. "
            "pinn_rul and anomaly model outputs will be null."
        )
        return

    try:
        import csv

        rows = []
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)

        rul_col = "RUL" if "RUL" in rows[0] else None
        x_all = []
        for row in rows:
            try:
                x = [float(row[f]) for f in _W2_SENSOR_KEYS]
                x_all.append(x)
            except (KeyError, ValueError):
                continue

        if len(x_all) < 50:
            logger.warning("Wave 2 startup fit skipped: too few valid rows in CSV.")
            return

        x_all = np.array(x_all, dtype=np.float32)
        _startup_fit_anomaly_ensemble(x_all, rows, _W2_FEATURE_NAMES)
        _startup_fit_pinn_rul(x_all, rows, rul_col)

    except Exception as e:
        logger.warning(f"Wave 2 startup fit failed: {e}", exc_info=True)


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

    # Fit transient Wave 2 models from training data
    logger.info("Fitting Wave 2 transient models (AnomalyEnsemble + PINN)...")
    _fit_wave2_models()

    logger.info("=" * 50)

    yield  # <- application runs here

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
    from src.core.model_loader import (
        load_p1,
        load_p2,
        load_p3,
        load_p4,
        load_p5,
        load_p6,
    )
    from src.anomaly_cusum import get_anomaly_ensemble
    from src.pinn_rul import get_pinn_estimator

    ensemble = get_anomaly_ensemble()
    pinn = get_pinn_estimator()

    return {
        "status": "healthy",
        "service": "ml-prediction",
        "version": "2.0.0",
        "models": {
            "p1_failure": load_p1() is not None,
            "p2_failure_type": load_p2() is not None,
            "p3_rul": load_p3() is not None,
            "p4_anomaly": load_p4() is not None,
            "p5_priority": load_p5() is not None,
            "p6_schedule": load_p6() is not None,
            "anomaly_ensemble": ensemble is not None and ensemble.is_fitted,
            "pinn_rul": pinn is not None and pinn.is_fitted,
        },
    }


@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "EAM ML Prediction Service",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=8000,
        reload=False,
        log_level="info",
    )

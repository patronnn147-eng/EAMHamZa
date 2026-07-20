"""ML router — thin composition root.

Split from a single ~1700-line file into modules/ml/routes/, grouped by
concern:
  routes/health.py       — unified-health (DST fusion) + manual telemetry
  routes/predictions.py  — per-machine RUL / failure-probability / failure-type
  routes/fleet.py         — fleet dashboard + critical-risk list
  routes/shadow_logs.py   — PDCA shadow logs, P4 anomaly review, P7 feedback report
  routes/procurement.py   — P7 parts demand, readiness/timeline, procurement drafts
  routes/admin.py         — retraining control, service status, model health (ADMIN)
  routes/forecast.py      — C8 downtime/labor/budget forecasts + schedule optimizer
  routes/_common.py       — shared constants/helpers (no APIRouter)

Add new endpoints to the relevant routes/*.py module, not here.
"""
from fastapi import APIRouter

from .routes import admin, fleet, forecast, health, predictions, procurement, shadow_logs

router = APIRouter(prefix="/api/v1/ml", tags=["Machine Learning"])

router.include_router(health.router)
router.include_router(predictions.router)
router.include_router(fleet.router)
router.include_router(shadow_logs.router)
router.include_router(procurement.router)
router.include_router(admin.router)
router.include_router(forecast.router)

# Re-exported: chat_context.py imports get_unified_health directly from this module.
from .routes.health import get_unified_health  # noqa: E402, F401

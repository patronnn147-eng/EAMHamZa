# Phase 3: ML Integration - Context

**Gathered:** 2026-03-04
**Status:** Ready for planning
**Source:** Codebase analysis

---

<domain>
## Phase Boundary

Implement ML-powered predictive maintenance:
- Predictive maintenance API endpoint
- Failure probability calculation
- Remaining Useful Life (RUL) estimation
- Anomaly detection
- Frontend predictive panel

**Existing codebase:** ML module in `app/backend/modules/ml/`, trained models in `app/backend/modules/ml/models/`, frontend `PredictivePanel.tsx`

</domain>

<decisions>
## Implementation Decisions

### ML Service
- **Prediction API:** Already exists in `modules/ml/router.py`
- **ML Service:** Already exists in `modules/ml/ml_predictive.py`
- **Models:** Trained models exist in `modules/ml/models/`

### Frontend Integration
- **PredictivePanel.tsx:** Already exists and calls `/api/v1/ml/machines/{id}/prediction`
- **Health Score:** Already calculated in `utils/healthScore.ts`

### Data Pipeline
- **Telemetry:** Can receive sensor data (air temp, process temp, RPM, torque, tool wear)
- **Logging:** ML predictions logged to `ml_prediction_logs` table

</decisions>

<specifics>
## Specific Ideas

**From existing code:**
- `app/backend/modules/ml/router.py` - ML API endpoints
- `app/backend/modules/ml/ml_predictive.py` - ML service class
- `app/backend/modules/ml/models/*.pkl` - Trained models
- `app/frontend/src/modules/shared/machines/components/PredictivePanel.tsx` - UI

**Features:**
- Failure probability (0-100%)
- Risk level (LOW/MEDIUM/HIGH/CRITICAL)
- Remaining Useful Life (RUL) in days
- Predicted failure date

</specifics>

<deferred>
## Deferred Ideas

- Groq integration for natural language explanations (future phase)
- Advanced anomaly detection algorithms (future phase)
- Real-time sensor streaming (future phase)

</deferred>

---

*Phase: 03-ml-integration*
*Context gathered: 2026-03-04*

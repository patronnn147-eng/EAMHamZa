# Phase 08 Context — Intelligence & Automation Features

**User Decisions from Discussion:**

## Selected Features

### Intelligence & Automation Layer

1. **Predictive Maintenance/Alerts**
   - Uses historical data (or simple thresholds) to predict when an asset *will* need attention
   - Should integrate with existing ML P1-P6 models already in production

2. **Automated Reporting Engine**
   - Users can schedule weekly PDF/Excel summaries of asset health, costs, or utilization
   - Reports sent directly to email

3. **AI Chat Interface**
   - Natural Language Query feature
   - Example: "Which assets in Building A are due for maintenance this month?"

### Integration & Visibility Layer

4. **IoT/Sensor Integration**
   - Dashboard consuming real-time data (temperature, vibration, runtime hours) from connected hardware

5. **Audit Trail/History Log**
   - Granular, immutable log tracking every change to an asset
   - Who changed what, and when — for compliance and accountability

## Tech Stack (Already in Project)

- **Backend:** FastAPI + SQLAlchemy + PostgreSQL
- **Frontend:** React + TypeScript + Tailwind CSS + shadcn/ui
- **ML:** XGBoost models (P1-P6 already trained and in production)
- **Queue:** Celery for background tasks
- **Email:** Already configured in `core/email.py`

## Existing Assets to Build On

- ML models already trained (P1: Failure Prediction, P2: Failure Type, P3: RUL, P4: Anomaly, P5: Priority, P6: Scheduling)
- ML Dashboard already exists (Phase 06)
- Notification system already exists (`core/notifications.py`)
- Email service already exists (`core/email.py`)
- Audit table `archives` exists in database

## Decisions Made

- Use existing ML models (P1-P6) as the intelligence layer
- Implement threshold-based alerts first, then enhance with ML predictions
- Audit trail should append-only (no updates/deletes)
- Reports use existing email infrastructure
- Chat interface will use existing ML prediction APIs

## Deferred Ideas

- None explicitly deferred yet

## What's NOT in Scope for This Phase

- Complex NLP for chat (use simple keyword matching + existing ML APIs)
- Real IoT hardware integration (mock data only for dashboard)
- Full offline support

---

*Context created: 2026-04-09*

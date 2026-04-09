# Phase 08 Research — Intelligence & Automation Features

## Feature Analysis

### 1. Predictive Maintenance/Alerts

**Current State:** ML models P1-P6 already trained and exposed via API. Dashboard exists.

**Implementation Options:**

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Threshold-based alerts using existing ML predictions | Fast, uses existing models | Simple |
| B | Combine ML failure probability + time since last maintenance | More intelligent | More complex |
| C | ML P3 (RUL) + configurable threshold (e.g., alert when RUL < 7 days) | Most actionable | Requires telemetry data |

**Recommendation:** Option C — Use existing RUL (Remaining Useful Life) predictions with configurable thresholds. Alert when RUL < N days.

### 2. Automated Reporting Engine

**Current State:** `rapports` service exists. Email service exists in `core/email.py`.

**Implementation Options:**

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Celery periodic task with HTML email | Existing infrastructure | Basic |
| B | PDF generation with weasyprint | Professional output | Requires additional deps |
| C | Excel export with openpyxl | Excel users love it | Additional deps |

**Recommendation:** Start with Option A (Celery + HTML), add Excel (Option C) as enhancement.

### 3. AI Chat Interface

**Current State:** No chat interface exists.

**Implementation Options:**

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Keyword matching + ML API calls | Simple, no external API | Limited intelligence |
| B | RAG with existing docs | More capable | Complex setup |
| C | LLM integration (Azure OpenAI) | Most capable | Cost, setup |

**Recommendation:** Start with Option A — Simple keyword matching that calls existing ML APIs. Build a query parser that maps natural language to SQLAlchemy filters.

### 4. IoT/Sensor Integration

**Current State:** Machine telemetry stored in database (air_temperature, process_temperature, etc.)

**Implementation Options:**

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Dashboard showing historical telemetry trends | Uses existing data | No real-time |
| B | Mock IoT with random data generators | Shows concept | Fake data |
| C | WebSocket real-time updates | Real-time feel | More complex |

**Recommendation:** Start with Option A — Create IoT Dashboard showing telemetry trends over time using existing data. Mock real-time with polling.

### 5. Audit Trail/History Log

**Current State:** `archives` table exists but may not track all changes.

**Implementation Options:**

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | SQLAlchemy event listeners (before_update, before_delete) | Automatic | Performance overhead |
| B | Explicit audit calls in services | Explicit control | Easy to miss |
| C | Database-level triggers (postgres) | Most performant | Harder to maintain |

**Recommendation:** Option A — Use SQLAlchemy event listeners for automatic audit logging. Ensure append-only (no deletes).

---

## Technical Dependencies

| Feature | Depends On | Creates |
|---------|------------|---------|
| Predictive Alerts | ML P1-P6 APIs, notifications service | New alerts table, API endpoint |
| Reporting Engine | Email service, Celery | New scheduled reports, report templates |
| AI Chat | ML APIs, machines service | New chat endpoint, query parser |
| IoT Dashboard | Machines service, telemetry data | New dashboard page |
| Audit Trail | All services that modify data | Archive entries on every change |

---

## Risk Assessment

| Feature | Complexity | Risk | Mitigation |
|---------|------------|------|------------|
| Predictive Alerts | Medium | Alert storms | Rate limiting, configurable thresholds |
| Reporting Engine | Low | Email failures | Retry queue, fallback to in-app |
| AI Chat | Medium | Wrong interpretations | Show confidence, allow feedback |
| IoT Dashboard | Low | Empty data | Mock data fallback |
| Audit Trail | Medium | Performance | Async logging, batch inserts |

---

*Research completed: 2026-04-09*

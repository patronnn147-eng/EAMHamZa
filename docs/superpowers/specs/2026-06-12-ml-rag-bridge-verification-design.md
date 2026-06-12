# ML↔RAG Chat Bridge — Live Verification Design

**Date:** 2026-06-12
**Status:** Approved
**Scope:** Verify the ML context injection feature (commit `1c4be92`) works end-to-end on the real running stack.

---

## Context

Commit `1c4be92` wired live ML predictions into the machine-scoped chat: when a chat request carries a `machine_id`, the backend fetches the unified-health ML snapshot in parallel with RAG retrieval and injects a French `[ETAT ML EN TEMPS REEL]` block into the LLM prompt. 20 unit tests cover the formatting logic (`tests/backend/ml_chat_context.test.py`), but nothing has verified the live pipeline: real Postgres telemetry → real ml-service predictions → real Groq answer.

Approach chosen: **live-stack verification** (real services, no mocks), saved as a repeatable smoke script. Mock-based integration tests rejected — they prove wiring, not the actual stack users touch.

## Architecture

Three sequential layers. Each layer gates the next — no point testing the bridge if the stack is down.

### Layer 1 — Stack health
1. `make rebuild` (or `make up` if images current), wait for healthchecks.
2. Assert:
   - Backend: `GET /docs` → 200
   - RAG service: `GET :8003/health` → `{"status": "ok"}`
   - ML service responding (via backend `is_ml_service_available` path or direct healthcheck)
   - RAG corpus loaded: `GET /api/v1/rag/documents` lists the 10 `*-*.txt` manual files

### Layer 2 — API-level bridge test (core)
Script: `app/backend/scripts/smoke_ml_rag_bridge.py` (httpx, runs from host against `localhost:8000`).

1. Login as a seeded user → JWT token.
2. Pick a target machine: prefer a Reflow Oven (ID 9 or 15) with telemetry rows; fall back to any machine that `unified-health` returns data for.
3. `GET /api/v1/ml/machines/{id}/unified-health` → capture `unified_health_score`, `risk_level`, `failure_probability`, sensor values. Assert 200 + numeric fields present.
4. `POST /api/v1/chat/ai/chat` with `{message: "Quel est l'état actuel de cette machine ? Donne les valeurs des capteurs et le score de santé.", machine_id: <id>}`.
   - Assert 200 and non-empty answer.
   - Assert answer references live ML state: at least 2 of — health score number (±1 tolerance after rounding), risk level word, a sensor value, RUL days, "ANOMALIE"/anomaly status.
5. Same question WITHOUT `machine_id`.
   - Assert 200, non-empty answer (RAG/tools path intact).

LLM answers are non-deterministic → assertions use fuzzy matching (number appears within rounding, keyword sets), not exact strings. A failed match prints the full answer for human judgment instead of hard-failing the whole run (reported as WARN, not FAIL, when the answer is plausible but unmatched).

### Layer 3 — Degradation test (safety)
1. `docker stop` the ml-service container.
2. Repeat the machine-scoped chat question.
   - Assert 200 + non-empty answer (manual/RAG-only) — NO 5xx, no user-visible error.
3. `docker start` the container; wait until healthy again.

## Components

| Unit | Purpose | Depends on |
|------|---------|-----------|
| `app/backend/scripts/smoke_ml_rag_bridge.py` | All Layer 2+3 HTTP assertions; CLI flags `--skip-degradation`, `--machine-id N` | httpx, running stack, seeded login creds |
| Shell steps (run by operator/agent) | rebuild, healthcheck waits, docker stop/start ml-service | docker compose |
| Verification report | Pass/fail per layer + captured answers, printed at end of script | — |

Login credentials: read from env (`SMOKE_USER` / `SMOKE_PASS`), defaulting to the seeded admin account used by existing scripts. The script never hardcodes secrets.

## Error handling

- Stack not healthy after timeout (5 min) → Layer 1 FAIL, abort with diagnostic (docker compose ps + last log lines).
- unified-health returns no telemetry for chosen machine → auto-pick another machine from `GET /machines`; if none works, FAIL with "no machine has telemetry — seed telemetry first".
- Groq 503 (no API key / rate limit) → FAIL with explicit cause; not a bridge bug.
- Degradation layer always restarts ml-service in a `finally` block — never leaves the stack degraded.

## Pass criteria

All three layers green:
1. Stack healthy + 10 manual docs present
2. Machine-scoped answer demonstrably grounded in live ML values; no-machine answer unaffected
3. ML-down chat still answers without error

## Testing the test

Smoke script is itself exercised by running it — no meta-tests. It is idempotent (read-only except for chat sessions it creates) and safe to re-run.

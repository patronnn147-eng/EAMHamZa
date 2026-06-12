# ML↔RAG Chat Bridge — Live Verification Design

**Date:** 2026-06-12
**Status:** Approved (rev 2 — review feedback incorporated)
**Scope:** Verify the ML context injection feature (commit `1c4be92`) works end-to-end on the real running stack.

**Rev 2 changes (from review):** direct injection proof via `ml_context_used` response field; dynamic machine discovery (no hardcoded IDs); destructive degradation test gated behind `--allow-destructive`; bridge vs LLM verification separated; soft RAG doc assertions; WARN replaced by MANUAL_REVIEW with distinct exit code.

---

## Context

Commit `1c4be92` wired live ML predictions into the machine-scoped chat: when a chat request carries a `machine_id`, the backend fetches the unified-health ML snapshot in parallel with RAG retrieval and injects a French `[ETAT ML EN TEMPS REEL]` block into the LLM prompt. 20 unit tests cover the formatting logic (`tests/backend/ml_chat_context.test.py`), but nothing has verified the live pipeline: real Postgres telemetry → real ml-service predictions → real Groq answer.

Approach chosen: **live-stack verification** (real services, no mocks), saved as a repeatable smoke script. Mock-based integration tests rejected — they prove wiring, not the actual stack users touch.

## Prerequisite production change — injection proof

The chat response gains one field so injection is **proven, not inferred**:

- `ChatResponse.ml_context_used: bool` — `true` only when an ML snapshot was fetched AND the `[ETAT ML EN TEMPS REEL]` block was appended to the LLM messages.
- Backend also logs one line at INFO: `[ml_bridge] machine_id=<id> ml_context_used=<bool>`.
- Field is harmless in production and enables a future "live ML data used" badge in the chat UI.

## Architecture

Three sequential layers. Each layer gates the next — no point testing the bridge if the stack is down.

**Bridge vs LLM separation:** the report scores two independent verdicts so a Groq outage never masquerades as a bridge failure:
- **BRIDGE** — unified-health works, snapshot built, `ml_context_used=true` returned.
- **LLM** — Groq produced a grounded answer.

### Layer 1 — Stack health
1. `make rebuild` (or `make up` if images current), wait for healthchecks.
2. Assert:
   - Backend: `GET /docs` → 200
   - RAG service: `GET :8003/health` → `{"status": "ok"}`
   - ML service responding (via backend `is_ml_service_available` path or direct healthcheck)
   - RAG corpus loaded: `GET /api/v1/rag/documents` returns **at least one** `doc_type=manual` document whose filename matches the factory-manual set (soft check — never assert exact counts; documentation evolves).

### Layer 2 — API-level bridge test (core)
Script: `app/backend/scripts/smoke_ml_rag_bridge.py` (httpx, runs from host against `localhost:8000`).

1. Login as a seeded user → JWT token.
2. **Dynamic machine discovery — no hardcoded IDs.** `GET /machines` (or equivalent list endpoint), iterate machines, select the first whose `unified-health` returns valid numeric telemetry. Optional `--machine-id N` override. If none qualifies → FAIL "no machine has telemetry — seed telemetry first".
3. `GET /api/v1/ml/machines/{id}/unified-health` → capture `unified_health_score`, `risk_level`, `failure_probability`, sensor values. Assert 200 + numeric fields present. *(BRIDGE evidence part 1)*
4. `POST /api/v1/chat/ai/chat` with `{message: "Quel est l'état actuel de cette machine ? Donne les valeurs des capteurs et le score de santé.", machine_id: <id>}`.
   - Assert 200.
   - **Assert `ml_context_used == true`** — direct proof the ML block reached the LLM prompt. *(BRIDGE evidence part 2 — the decisive check)*
   - Assert non-empty answer referencing live ML state: at least 2 of — health score number (±1 after rounding), risk level word, a sensor value, RUL days, anomaly status. *(LLM grounding check)*
   - If Groq returns 503: **BRIDGE remains assessable** via step 3 + log line; report `LLM: FAIL (Groq unavailable)` separately instead of failing the whole run.
5. Same question WITHOUT `machine_id`.
   - Assert 200, non-empty answer, **`ml_context_used == false`** (no ML state leaked into machine-less chat).

LLM answers are non-deterministic → grounding assertions use fuzzy matching (number within rounding tolerance, keyword sets). Result states are explicit:

| Status | Meaning | Exit code |
|--------|---------|-----------|
| PASS | Verification succeeded | 0 |
| FAIL | Definitively failed | 1 |
| MANUAL_REVIEW | Answer plausible but unmatched — full answer printed, human must read it | 2 |

No silent WARNs — MANUAL_REVIEW exits non-zero so it cannot be ignored by CI or habit.

### Layer 3 — Degradation test (safety, opt-in)
**Destructive — gated behind `--allow-destructive` flag.** Without the flag the layer is SKIPPED with an explicit notice. Intended for local environments only; never run against shared/staging stacks.

1. `docker stop` the ml-service container.
2. Repeat the machine-scoped chat question.
   - Assert 200 + non-empty answer — NO 5xx, no user-visible error.
   - `ml_context_used` may legitimately stay `true`: the backend falls back to
     rule-based scoring (RULCalculator, `score_source=fallback_additive`) computed
     from raw telemetry, so a valid context block is still injected with the ML
     container down. Discovered during execution — degradation is stronger than
     originally assumed; the safety property is "answers without error", not
     "no context".
3. `docker start` the container in a `finally` block; wait until healthy again.

## Components

| Unit | Purpose | Depends on |
|------|---------|-----------|
| `ChatResponse.ml_context_used` + chat.py wiring + INFO log line | Direct injection proof (production change, ~10 lines) | existing bridge code |
| `app/backend/scripts/smoke_ml_rag_bridge.py` | All Layer 2+3 HTTP assertions; CLI flags `--allow-destructive`, `--machine-id N` | httpx, running stack, seeded login creds |
| Shell steps (run by operator/agent) | rebuild, healthcheck waits, docker stop/start ml-service (Layer 3 only, flag-gated) | docker compose |
| Verification report | BRIDGE + LLM verdicts per layer, PASS/FAIL/MANUAL_REVIEW statuses, captured answers | — |

Login credentials: read from env (`SMOKE_USER` / `SMOKE_PASS`), defaulting to the seeded admin account used by existing scripts. The script never hardcodes secrets.

## Error handling

- Stack not healthy after timeout (5 min) → Layer 1 FAIL, abort with diagnostic (docker compose ps + last log lines).
- No machine with telemetry found during discovery → FAIL with "no machine has telemetry — seed telemetry first".
- Groq 503 (no API key / rate limit) → `LLM: FAIL (Groq unavailable)`; BRIDGE verdict still computed from unified-health + `ml_context_used` evidence — a Groq outage never reports the bridge as broken.
- Degradation layer always restarts ml-service in a `finally` block — never leaves the stack degraded.

## Pass criteria

1. Stack healthy + manual corpus present (soft check)
2. **BRIDGE: PASS** — `ml_context_used=true` on machine-scoped chat, `false` without machine
3. **LLM: PASS** — answer grounded in live ML values (or MANUAL_REVIEW with printed answer for human judgment)
4. Layer 3 (if `--allow-destructive`): ML-down chat answers without error, `ml_context_used=false`

## Testing the test

Smoke script is itself exercised by running it — no meta-tests. It is idempotent (read-only except for chat sessions it creates) and safe to re-run.

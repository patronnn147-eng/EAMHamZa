# ML↔RAG Bridge Live Verification — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the ML context injection (commit `1c4be92`) works on the live stack — injection proven mechanically via a new `ml_context_used` response field, plus a repeatable smoke script with BRIDGE/LLM verdict separation.

**Architecture:** One small production change (response flag + log line), one self-contained smoke script (httpx against localhost:8000), one execution phase (Docker up → script run → flag-gated degradation test).

**Tech Stack:** FastAPI/Pydantic, httpx 0.28 (host Python 3.13), docker compose.

**Spec:** `docs/superpowers/specs/2026-06-12-ml-rag-bridge-verification-design.md`

**Facts discovered (do not re-derive):**
- Login: `POST /api/v1/auth/login` body `{"email": ..., "password": ...}` → `TokenResponse` with `access_token`
- `ChatResponse` defined at `app/backend/schemas/ai_chat.py:53`
- Single `ChatResponse(` construction in `app/backend/modules/shared/routes/chat.py:492`
- ML injection block in chat.py section "4c" — `if ml_snapshot is not None:` … `if ml_text:`
- Machines list: `GET /api/v1/machines` (client.entities.machines — standard CRUD router)
- RAG docs list: `GET /api/v1/rag/documents` (ADMIN sees all; any authenticated role can list)
- unified-health: `GET /api/v1/ml/machines/{id}/unified-health` (no auth dependency in router signature)
- ml-service container: `asset_management_ml_service`
- Docker Desktop NOT running at plan time — execution must start it first
- Host has httpx 0.28.1 + requests 2.32.5
- No seeded admin in repo — smoke script reads `SMOKE_USER`/`SMOKE_PASS` env; operator supplies or registers a user

---

### Task 1: `ml_context_used` response field (production change)

**Files:**
- Modify: `app/backend/schemas/ai_chat.py` (ChatResponse, line ~53)
- Modify: `app/backend/modules/shared/routes/chat.py` (injection block + return)
- Test: `tests/backend/ml_chat_context.test.py` (append schema test)

- [ ] **Step 1: Add failing test** — append to `tests/backend/ml_chat_context.test.py`:

```python
class TestChatResponseFlag:
    def test_ml_context_used_defaults_false(self):
        from schemas.ai_chat import ChatResponse
        r = ChatResponse(message="x")
        assert r.ml_context_used is False

    def test_ml_context_used_settable(self):
        from schemas.ai_chat import ChatResponse
        r = ChatResponse(message="x", ml_context_used=True)
        assert r.ml_context_used is True
```

- [ ] **Step 2: Run — expect FAIL** `python -m pytest "tests\backend\ml_chat_context.test.py::TestChatResponseFlag" -v` → ValidationError/AttributeError.

- [ ] **Step 3: Add field** to `ChatResponse` in `app/backend/schemas/ai_chat.py` after `session_title`:

```python
    ml_context_used: bool = Field(
        default=False,
        description="True when live ML predictions were injected into the LLM prompt",
    )
```

- [ ] **Step 4: Wire chat.py.** In the "4c" ML injection block, set a flag and log:

```python
    ml_context_injected = False
    if ml_snapshot is not None:
        ml_text = build_ml_context(ml_snapshot)
        if ml_text:
            ml_context_injected = True
            ...existing two messages.append(...)...
    if machine_id is not None:
        logger.info(f"[ml_bridge] machine_id={machine_id} ml_context_used={ml_context_injected}")
```

And in the `return ChatResponse(` at line ~492 add `ml_context_used=ml_context_injected,`.
NOTE: `ml_context_injected` must be initialized BEFORE the `if rag_chunks:` block (top of message assembly) so it always exists at return.

- [ ] **Step 5: Run tests — expect PASS** `python -m pytest "tests\backend\ml_chat_context.test.py" -v` → 22 passed.

- [ ] **Step 6: Commit** `feat(chat): ml_context_used response flag — mechanical proof of ML injection`

---

### Task 2: Smoke script

**Files:**
- Create: `app/backend/scripts/smoke_ml_rag_bridge.py`

- [ ] **Step 1: Write script.** Self-contained httpx script, no project imports. Structure:

```python
"""
Smoke test: ML <-> RAG chat bridge (spec: docs/superpowers/specs/2026-06-12-*.md)

Usage:
  python smoke_ml_rag_bridge.py [--machine-id N] [--allow-destructive] [--base-url http://localhost:8000]
Env:
  SMOKE_USER / SMOKE_PASS  — login credentials (required)
Exit codes: 0 PASS, 1 FAIL, 2 MANUAL_REVIEW
"""
```

Functions (each prints `[layer] check: PASS/FAIL/SKIP` lines):
- `login(client, base) -> token` — POST /api/v1/auth/login, FAIL-fast on error
- `layer1_stack_health(client, base, token)`:
  - GET {base}/docs → 200
  - GET http://localhost:8003/health → status ok
  - GET /api/v1/rag/documents → ≥1 doc with `doc_type == "manual"` (soft check; print count)
- `discover_machine(client, base, token, override)`:
  - if override: use it
  - else GET /api/v1/machines (paginated/list), iterate, first machine where GET unified-health returns 200 AND `unified_health_score` is not None AND `air_temperature` is not None → return (id, health_payload)
  - none → FAIL "no machine has telemetry"
- `layer2_bridge(client, base, token, mid, health)`:
  - POST /api/v1/chat/ai/chat {"message": QUESTION_FR, "machine_id": mid}
  - Groq 503 → record LLM=FAIL(groq unavailable), BRIDGE judged on: unified-health OK (already have) — print instruction to check backend log line `[ml_bridge] machine_id=… ml_context_used=True`; return
  - 200 → assert `ml_context_used is True` (BRIDGE decisive check)
  - grounding fuzzy match: count hits among [round(health_score) as str, risk_level word, str(int(rpm)), rul_days rounded, "anomal" (case-insens)] in answer; ≥2 → LLM=PASS, else LLM=MANUAL_REVIEW + print full answer
  - POST same question WITHOUT machine_id → 200 AND `ml_context_used is False`
- `layer3_degradation(client, base, token, mid)` — only with --allow-destructive:
  - `docker stop asset_management_ml_service` (subprocess)
  - try: POST chat with machine_id → assert 200, non-empty answer, `ml_context_used is False`
  - finally: `docker start asset_management_ml_service`, poll unified-health until 200 or 120s
- `main()` — argparse, run layers, print verdict table:

```
==== VERDICT ====
Layer 1 stack:    PASS
BRIDGE:           PASS
LLM:              PASS | FAIL(groq) | MANUAL_REVIEW
Layer 3 degrade:  PASS | SKIPPED (--allow-destructive not set)
```

Exit code = max severity (PASS 0 < MANUAL_REVIEW 2; any FAIL → 1; SKIP ignored).

- [ ] **Step 2: Syntax check** `python -m py_compile app\backend\scripts\smoke_ml_rag_bridge.py`

- [ ] **Step 3: Commit** `test(smoke): ML-RAG bridge live verification script`

---

### Task 3: Execute verification

- [ ] **Step 1: Start Docker Desktop** (it was down at plan time), then `make up` (rebuild only backend if needed: `docker compose up -d --build backend`). Backend image must contain Task 1 change.
- [ ] **Step 2: Wait healthy** — poll `GET /docs` + `:8003/health` up to 5 min; on timeout print `docker compose ps` + last 50 log lines of failing service → FAIL.
- [ ] **Step 3: Resolve credentials** — operator supplies SMOKE_USER/SMOKE_PASS (ask user if no known account; or query db: `docker exec asset_management_db psql -U postgres -d asset_management -c "SELECT email, role FROM utilisateurs LIMIT 5"` then ask user for that account's password).
- [ ] **Step 4: Run** `python app\backend\scripts\smoke_ml_rag_bridge.py --allow-destructive` (local env — destruction approved by spec for local).
- [ ] **Step 5: Cross-check backend log** `docker logs asset_management_backend 2>&1 | Select-String ml_bridge` — confirm `ml_context_used=True` line for the machine-scoped call.
- [ ] **Step 6: Report** — verdict table + captured answer excerpts to user (plain language). MANUAL_REVIEW → show answer, ask user to judge grounding.
- [ ] **Step 7: Commit** any fixes discovered; update CLAUDE.md changelog with verification result.

---

## Self-review

- Spec coverage: injection proof (T1), dynamic discovery (T2 discover_machine), destructive gate (T2 layer3 + T3 step 4 explicit local approval), BRIDGE/LLM split (T2 layer2), soft doc check (T2 layer1), MANUAL_REVIEW exit 2 (T2 main) — all six review points covered. ✓
- No placeholders; exact endpoints/paths/container names embedded. ✓
- Type consistency: `ml_context_used` bool everywhere. ✓

# RAG Quality Roadmap — Design Spec

**Date:** 2026-06-11  
**Status:** Approved  
**Scope:** Prioritized implementation order for 7 remaining RAG/chat features

---

## Context

Phase 13 completed Postgres-native hybrid search (BM25 + vector RRF). Reranker, OCR, machine_id filter, and 3-stage Groq agent loop are already live. Seven features remain unimplemented.

Driver: **data quality first** (corpus growing, must fix integrity before optimizing quality), **feature completeness second**. Corpus state: growing — real documents being ingested, production usage starting.

---

## Priority Order

| # | Feature | Category | Rationale |
|---|---------|----------|-----------|
| 1 | Doc versioning + dedup | Data integrity | Ticking clock — duplicate chunks silently degrade hybrid search. Every re-upload poisons the corpus. Fix while corpus is still small. |
| 2 | Eval harness (precision@k, MRR) | Quality measurement | Baseline score before any further tuning. Can't know if Phase 13 helped without measurement. Required before fine-tuning is meaningful. |
| 3 | Citation UI (clickable sources) | Trust / UX | RAG answers currently unverifiable. Users can't trace answer to source document. Trust blocker for production adoption. |
| 4 | Streaming responses | UX | Chat feels unresponsive without streaming. Becomes painful as real usage grows. |
| 5 | All Ps in chat (P1–P7) | Feature completeness | Connects existing ML pipeline into chat context. Two mechanisms: auto-injection + direct querying. |
| 6 | Conversation export | Feature completeness | Reporting use case. Low urgency. |
| 7 | Fine-tuned domain embeddings | Quality optimization | Corpus too thin now. Revisit when 6+ months of real ingestion complete. |

---

## Feature Designs

### 1. Doc Versioning + Dedup

**Problem:** Re-uploading the same document (or a revised version) currently creates duplicate chunks in `doc_chunks`. Hybrid search returns redundant results, inflating the appearance of confidence.

**Design:**
- On ingest, compute `sha256(file_bytes)` as `content_hash`
- Add `content_hash VARCHAR(64)` column to `documents` table (Alembic migration)
- On `POST /rag/documents`: check if `content_hash` already exists
  - **Exact duplicate:** reject with `409 Conflict`, return existing document ID
  - **Same filename, different hash:** treat as version update — delete old chunks, re-ingest, increment `version` int column
- Add `version INT DEFAULT 1` to `documents` table
- `PUT /rag/documents/{id}` (replace) already exists — wire the hash check into it too
- No chunk-level dedup needed — document-level hash is sufficient

**Files:** `app/rag-service/ingestor.py`, `app/backend/modules/shared/routes/rag_docs.py`, new Alembic migration

---

### 2. Eval Harness (precision@k, MRR)

**Problem:** No way to measure retrieval quality. Can't validate Phase 13 impact or future improvements.

**Design:**
- `app/rag-service/eval/` module with:
  - `golden_set.json` — hand-curated query→expected_chunk_ids pairs (start with 20–50 queries)
  - `eval.py` — runs each query through `/retrieve`, computes precision@1, precision@5, MRR, recall@5
  - `run_eval.sh` — CLI wrapper: `docker compose exec rag-service python eval/eval.py`
- Output: JSON report + human-readable table with per-query breakdown
- Golden set seeded from Phase 13 smoke corpus (OT-SEED-* work orders + any real docs)
- No CI integration required now — manual run before/after major retrieval changes

**Files:** `app/rag-service/eval/eval.py`, `app/rag-service/eval/golden_set.json`, `app/rag-service/eval/run_eval.sh`

---

### 3. Citation UI (Clickable Sources)

**Problem:** RAG chunks are injected into the system prompt but never returned to the frontend. Users cannot see which documents the answer came from.

**Design:**
- `rag-service /retrieve` response already returns chunk metadata (doc_id, content snippet, similarity score)
- Backend chat route: after RAG retrieval, attach `rag_sources` list to the chat response alongside `content`
  - Each source: `{ doc_id, filename, page, snippet (first 120 chars), score }`
- Frontend `ChatInterface.tsx`: render `rag_sources` as a collapsible "Sources" block below AI message
  - Each source: filename + page number as a clickable link → hits `GET /rag/documents/{id}/download` (existing presigned URL endpoint, admin-gated) OR opens a preview modal
  - For non-admin: show filename + page, no download link
- Role-aware: admins get download link, others get read-only citation

**Files:** `app/backend/modules/shared/routes/chat.py`, `app/frontend/src/modules/shared/ChatInterface.tsx`, `app/frontend/src/lib/types.ts`

---

### 4. Streaming Responses

**Problem:** Chat responses arrive all-at-once after full LLM generation. Feels slow and unresponsive.

**Design:**
- Groq SDK supports streaming (`stream=True`)
- Backend: replace `groq_client.complete()` with a streaming variant returning `AsyncGenerator`
- Chat route: return `StreamingResponse` (FastAPI) with `text/event-stream` content type
- SSE format: `data: {"delta": "...", "done": false}\n\n` per token, `data: {"done": true, "sources": [...]}\n\n` at end
- Frontend: switch from `fetch` + `await res.json()` to EventSource / `fetch` with `ReadableStream` reader, appending tokens to message as they arrive
- Sources delivered in the final SSE frame (after full generation)
- Cache: Groq cache still applies at the application layer (cache key unchanged); streaming bypasses cache on miss, same as today

**Files:** `app/backend/core/groq_client.py`, `app/backend/modules/shared/routes/chat.py`, `app/frontend/src/modules/shared/ChatInterface.tsx`

---

### 5. All Ps in Chat (P1–P7)

**Problem:** Existing ML pipeline (P1–P7 + Wave 2 DST) is not accessible via chat. Users must navigate to the ML tab separately.

**Design — two mechanisms:**

**A. Auto-injection (context):**
- In chat route, before building system prompt: detect machine reference in user query
  - Pattern: `machine\s*\d+`, `M\d+`, `machine id \d+`, or work-order refs that resolve to a machine
- On match: fetch `GET /api/v1/ml/unified-health/{machine_id}` (internal call)
- Format P1–P7 + DST snapshot as structured context block (business names only — no P-labels per CLAUDE.md)
- Inject alongside RAG chunks into system prompt
- Runs in parallel with RAG retrieval (asyncio.gather)
- On failure: log warning, skip injection — never block chat

**B. Direct querying (tool call):**
- Add `get_ml_predictions(machine_id: int)` tool to `ai_agents.py` Collector agent
- Tool body: calls unified-health endpoint, returns formatted snapshot
- LLM uses it when user explicitly asks about failure probability, RUL, anomaly score, etc.
- Response uses business names: "Failure Probability", "RUL Estimate", "Behavioral Anomaly", "Priority", "Schedule"

**Non-goal:** No push alerts, no proactive notifications — pull-only per chat message.

**Files:** `app/backend/modules/shared/routes/chat.py`, `app/backend/services/ai_prompts.py`, `app/backend/services/ai_agents.py`

---

### 6. Conversation Export

**Design:**
- `GET /api/v1/chat/sessions/{session_id}/export?format=json|pdf|markdown`
- Returns conversation history with timestamps, role, sources
- Markdown format: most useful for copy-paste into reports
- Frontend: export button in chat header

**Files:** `app/backend/modules/shared/routes/chat.py`, `app/frontend/src/modules/shared/ChatInterface.tsx`

---

### 7. Fine-Tuned Domain Embeddings

**Deferred.** Requires:
- Labeled query→document relevance pairs (needs 6+ months of real usage data)
- Training infrastructure (GPU or hosted fine-tuning API)
- Model serving update in rag-service

Revisit after conversation export is live and eval harness can measure embedding quality improvement.

---

## Implementation Notes

- Each feature is independently implementable — no hard dependencies between them (except: eval harness benefits from dedup being done first, and fine-tuning requires eval harness)
- Each feature maps to one GSD phase
- Streaming + citation UI can be planned together (both touch the same chat route and frontend component)

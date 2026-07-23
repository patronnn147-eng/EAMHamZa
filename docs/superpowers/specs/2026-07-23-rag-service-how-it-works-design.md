# RAG Service — How It Works (standalone HTML page)

Date: 2026-07-23
Status: Approved (brainstorming session)

## Purpose

A standalone HTML page, `rag-service-how-it-works.html`, documenting the RAG (Retrieval-Augmented Generation) microservice — both its **development history** (dated, from real `git log`) and **how it works today**. Companion piece to the existing `ml-service-how-it-works.html`; same visual design system (CSS custom-property tokens, same nav/hero/section/card/flow-step/code-block/callout patterns, same light/dark theme toggle), so the two read as a matched pair.

Not committed to the rapport yet — this is a standalone artifact first (same path the ML page took before it was later selectively integrated into `rapport/chapters/chap3_conception.tex`).

## Source of truth

All technical claims must trace to the actual codebase, read during brainstorming:

- `app/rag-service/main.py` — FastAPI app, endpoints (`/health`, `/ingest`, `/retrieve`, `/documents`, `/ocr-test`, `/cache-stats`, `/rerank-info`, `/hybrid-info`, `/cache-clear`)
- `app/rag-service/ingestor.py` — multi-format extraction (PDF native+OCR, TXT, image OCR, DOCX, XLSX, HTML), sha256 dedup, sentence-aware chunking (200 words / 20 overlap), batch embedding, pgvector insert
- `app/rag-service/embedder.py` — `BAAI/bge-m3` singleton, 1024-dim, 1h TTL query cache
- `app/rag-service/retriever.py` — orchestrates vector + keyword branches, RRF fuse, rerank, 5min TTL result cache
- `app/rag-service/hybrid.py` — Phase 13.1/13.2: Postgres FTS (french+english `tsvector` columns) keyword branch, Reciprocal Rank Fusion (k=60, overfetch=30), fail-loud on BM25 errors (no silent vector-only fallback)
- `app/rag-service/reranker.py` — `BAAI/bge-reranker-v2-m3` cross-encoder, overfetch ×4 capped at 50, graceful degradation to bi-encoder order on failure
- `app/backend/modules/shared/routes/chat.py` — `/api/v1/chat/ai/chat`: parallel RAG+ML fetch (`asyncio.gather`) when `machine_id` present, context injection, Groq LLM call, tool calling
- `app/backend/modules/ml/services/chat_context.py` — `get_ml_snapshot()`, never raises, returns `None` on any failure
- `app/backend/modules/shared/routes/rag_docs.py`, `app/backend/services/rag_storage.py` — S3/MinIO-backed document CRUD (per existing CLAUDE.md changelog entry, 2026-05-30 "later" session — matches the 2026-05-31 git commit dates below within a day, likely a timezone/session-boundary difference)
- `git log --all` on the above paths — **real dated chronology**, verified against file-level `git log --follow` for `reranker.py` and `embedder.py` specifically (reranker.py first appears 2026-06-12, confirming it postdates the Phase 13.2 hybrid work of 2026-06-06 despite hybrid.py's docstring calling it "the existing" reranker — docstrings get edited after the fact; git history is authoritative)

## Verified chronology (for history callouts + timeline strip)

| Date | Commit(s) | What shipped |
|---|---|---|
| 2026-05-11 | `e2c1254`, `b2e0258` | Phase 12.1 — pgvector RAG pipeline born as its own container. Vector-only retrieval. Dockerfile hardened (CPU torch, non-root user) same day. |
| 2026-05-12 | `55c0c73`, `50ef80e` | Admin document-management UI + chat upload button. |
| 2026-05-31 | `0f44e66`, `0773ad8`, `5da88cd`, `d55136a` | Documents moved to MinIO (`rag-docs` bucket, S3-backed), two-way sync (files dropped directly in MinIO get ingested too), OCR fallback for scanned/image PDFs (tesseract `fra+eng`). |
| 2026-06-01 | `d97f381` | Caching added, embedding model changed (to `BAAI/bge-m3`). |
| 2026-06-06 | `731e25a`, `f384209`, `62f82d4` | Phase 13.2 — hybrid retrieval: Postgres FTS keyword branch + Reciprocal Rank Fusion (k=60) added alongside vector search. |
| 2026-06-11 | `01dd6b0`, `97c6804`, `dc0f281`, `2a93aa4`, `413d928` | Content-hash dedup (sha256), HTTP 409 on duplicate ingest, document versioning on replace (PUT). |
| 2026-06-12 | `623ae76`, `14c4547` | Cross-encoder reranker (`BAAI/bge-reranker-v2-m3`) added; event-driven DB-to-RAG sync; **same day**, the ML-RAG bridge shipped (live ML snapshot injected into machine-scoped chat). |

## Page structure (approach B — interleaved history + explainer)

Pipeline-ordered walkthrough; each stage carries its history inline as a small callout rather than a separate timeline section repeating the same facts.

1. **Hero** — stat row: file types supported (12), retrieval stages (4: vector, keyword, fuse, rerank), phases (7), microservices (1, isolated container).
2. **The problem** — why RAG exists: ground the chat assistant in real technical documentation instead of letting the LLM hallucinate procedures; short, mirrors the ML page's problem-framing tone.
3. **Ingestion pipeline** — upload → format detection (pdf/txt/png/jpg/jpeg/tiff/tif/bmp/webp/docx/xlsx/html/htm) → text extraction (native layer first, OCR fallback per-page if native yields ≤10 chars) → sha256 dedup (409 on exact-match) → sentence-aware chunking (200 words, 20-word overlap, sentences never split mid-way) → batch embed (32 at a time, `BAAI/bge-m3`, 1024-dim) → pgvector insert (`doc_chunks.embedding vector(1024)`). History callouts at OCR, dedup/versioning.
4. **Storage & document lifecycle** — MinIO `rag-docs` bucket, two-way sync, version increment on replace, admin UI (bulk upload max 4 concurrent / 50 total, presigned downloads, ADMIN-only write / CHEFTECH+TECHNICIEN read-only). History callout at S3 migration + UI birth.
5. **Retrieval pipeline** — query embed (cache-checked first) → parallel branches: vector search (pgvector cosine `<=>`, threshold-gated, top-30 overfetch) and keyword search (Postgres FTS, `websearch_to_tsquery` on `content_tsv_fr`/`content_tsv_en`, `GREATEST(rank_fr, rank_en)`) → Reciprocal Rank Fusion (k=60, dedup by `chunk_id`, score = Σ 1/(k+rank)) → cross-encoder rerank (`BAAI/bge-reranker-v2-m3`, scores (query, chunk) pairs jointly) → top_k returned. History callout: vector-only at birth → hybrid+RRF Phase 13.2 → reranker.
6. **Design-principle callout** — keyword branch is fail-loud (BM25 SQL errors propagate to a 500, no silent vector-only substitution, per the service's own `CONTEXT.md` convention) vs. the chat bridge's fail-soft contract (RAG failure → empty context list, ML failure → `None`, chat always still answers). Two different reliability postures at two different layers, both deliberate.
7. **ML-RAG bridge** — `/api/v1/chat/ai/chat`: when `machine_id` present, RAG chunks and ML snapshot fetched concurrently (`asyncio.gather`), each injected as its own user/assistant context-turn pair (not merged into one blob), response carries `ml_context_used: bool` for auditability. Snapshot reuses the same `get_unified_health` route function the frontend ML tab calls — single source of truth.
8. **Full architecture diagram** — one SVG, two colored flow paths (ingestion vs. retrieval) sharing infrastructure boxes:
   - Frontend: chat widget, admin document-management page
   - Backend: `chat.py` (`/ai/chat`), `rag_docs.py` (upload/list/replace/delete), `rag_storage.py` (S3 helpers), `chat_context.py` (ML snapshot), `rag_client.py` (HTTP client to the RAG microservice)
   - RAG microservice: `ingestor.py` → `embedder.py` (shared by both flows) → `retriever.py` fanning into `hybrid.py` (keyword branch) + pgvector (vector branch) → RRF fuse → `reranker.py`
   - PostgreSQL: `documents`, `doc_chunks` (`embedding vector(1024)`, `content_tsv_fr`, `content_tsv_en` generated columns)
   - MinIO: `rag-docs` bucket
   - Groq LLM (external), final response back to frontend
   Ingestion path (upload→...→pgvector insert) and retrieval path (query→...→rerank→backend→LLM) are visually distinguished (color/dash) but pass through shared boxes (embedder, pgvector store) where they actually intersect in the real system.
9. **Timeline recap strip** — condensed horizontal strip of the 7 dated phases from the chronology table, mirroring the ML page's bottom summary section.
10. **Footer** — matches ML page's footer pattern (tech stack line + doc identifier).

## Visual design

Reuse `ml-service-how-it-works.html`'s design system verbatim: same CSS custom properties (`--bg`, `--surface`, `--card`, `--border`, `--text`, `--muted`, `--accent`, `--ok`, `--warn`, `--crit`, `--info`, `--mono`/`--sans` fonts), same component classes (`.hero`, `.stat-row`/`.stat-cell`, `.section-header`/`.step-tag`, `.card`/`.card-grid`, `.model-card`-equivalent for pipeline-stage cards, `.flow-steps`/`.flow-step`, `.code-block`, `.callout`/`.callout.warn`/`.callout.ok`, `.truth-table`, light/dark theme toggle script). No new design tokens introduced. Nav links point to the 9 sections above (condensed to the major anchors: Problem, Ingestion, Storage, Retrieval, Bridge, Architecture, Timeline).

## Out of scope

- Rapport (`.tex`) integration — this is a standalone HTML artifact only, per precedent with the ML page (integration, if wanted, is a separate future request).
- Benchmark numbers for retrieval quality (precision/recall of hybrid vs. vector-only) — not measured anywhere in the codebase; the page will describe the *mechanism* (RRF, rerank) without fabricating accuracy figures, consistent with this project's standing rule against invented metrics.
- Any code beyond what's needed to accurately describe the mechanism — no full function bodies reproduced, only the specific numbers/config that matter (chunk size, k values, model names, cache TTLs).

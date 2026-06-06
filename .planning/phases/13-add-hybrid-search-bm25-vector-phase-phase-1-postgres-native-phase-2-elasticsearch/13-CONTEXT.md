# Phase 13: Hybrid Search (BM25 + Vector) — Context

**Gathered:** 2026-06-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Add keyword-aware retrieval (BM25-style) as a second retrieval source inside `rag-service`,
fused with the existing pgvector cosine retrieval, then fed into the existing cross-encoder
reranker (BAAI/bge-reranker-v2-m3) before returning to the chat backend.

Goal: catch exact matches the bi-encoder misses — machine codes (`OT-SEED-C49-M20`), part
references, technician names, error codes — while preserving semantic recall for
natural-language questions.

Two sub-phases:
- **Phase 13.1 (this phase):** Postgres-native hybrid (no new container).
- **Phase 13.2 (kept in roadmap, conditional):** Elasticsearch upgrade — only if Phase 13.1
  quality is insufficient after real usage.

**NOT in scope:**
- Streaming responses, citation UI, eval harness — separate TODOs.
- Replacing the bi-encoder model or the reranker.
- Changing chunking strategy.
- New ingestion sources.

</domain>

<decisions>
## Implementation Decisions

### Phase split
- Phase 13.1 (Postgres-native) ships first, alone.
- Phase 13.2 (Elasticsearch) kept in roadmap as a conditional follow-up — only triggered
  if Phase 13.1's quality is insufficient after real use. Do NOT pre-build ES.

### Phase 13.1 BM25 engine
- **Postgres native FTS** via `tsvector` + `ts_rank_cd`. No new container, no new extension.
- Tradeoff acknowledged: ~80% of true BM25 quality. Acceptable for EAM corpus size.
- pg_search (ParadeDB) explicitly rejected for Phase 13.1 — extra image rebuild risk.

### FTS language config
- **Two generated tsvector columns** on `doc_chunks`:
  - `content_tsv_fr` using Postgres `french` config (stemming for French)
  - `content_tsv_en` using Postgres `english` config (stemming for English / codes)
- Query runs against BOTH; per-chunk rank = `GREATEST(rank_fr, rank_en)`.
- One GIN index per column.
- Arabic not handled by FTS this phase — deferred (vector side still catches it).

### tsvector population
- **Postgres GENERATED column**:
  ```sql
  content_tsv_fr tsvector GENERATED ALWAYS AS (to_tsvector('french', content)) STORED
  content_tsv_en tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
  ```
- Zero changes to `app/rag-service/ingestor.py`. Always in sync. Backfill is automatic when
  the column is added (Postgres computes for every existing row).

### Fusion algorithm
- **Reciprocal Rank Fusion (RRF)** with k=60 (BEIR-standard).
- Score per chunk = sum across (vector list, keyword list) of `1 / (k + rank_in_list)`.
- Score-free → no normalization between cosine similarity and `ts_rank_cd`. Robust to
  outliers. Standard 2024 hybrid-RAG pattern.
- Weighted-score fusion explicitly rejected for Phase 13.1 (needs eval harness to tune;
  not yet built).

### Overfetch shape
- Stage A (each source): vector top-30, keyword top-30.
- Stage B (fusion): RRF → up to 50 unique candidates, trim to top-30.
- Stage C (rerank): existing cross-encoder reranks 30 → returns top_k=8 to backend.
- Threshold filter (similarity > 0.30) applies to the vector side ONLY — keyword side
  uses its own `ts_rank_cd > 0.0` gate (matched any term).

### Tie-breaking (RRF identical scores)
- Sort key: `(fused_score DESC, vector_similarity DESC)`.
- Rationale: semantic relevance wins ties — better default for natural-language queries
  in this EAM use case.

### Toggle + error behavior
- New env var `HYBRID_ENABLED` (default `true`). Pattern mirrors `RERANK_ENABLED`.
- **Fail loud** on BM25 errors — 500 to caller. No silent vector-only fallback.
- Rationale: misconfigurations surface fast; chat quality regression is unambiguous in logs.

### Cache integration
- Reuse existing `_retrieve_cache` (TTLCache 5 min) in `retriever.py`.
- Cache key extended: `(query, machine_id, top_k, threshold, hybrid_enabled)`.
- Existing invalidation on `clear_retrieval_cache()` (called by ingest/delete hooks) covers
  hybrid path automatically.

### Observability
- Extend `/cache-stats` JSON with a new `hybrid` block: `{enabled, fusion, k, overfetch,
  searches, vector_only_count, keyword_only_count, both_count, fallback_count}`.
- New `GET /hybrid-info` endpoint: `{enabled, fusion: "rrf", k: 60, overfetch: 30,
  fts_configs: ["french", "english"]}`.
- Plus INFO logs per query: which source contributed each final chunk.

### Claude's Discretion
- Exact SQL phrasing for the hybrid query (CTE vs single SELECT) — pick whichever
  Postgres planner prefers in EXPLAIN ANALYZE.
- Counter naming inside `hybrid_stats()` — match the existing `rerank_stats()` shape.
- Whether to expose `tsquery` plainto vs websearch_to_tsquery — choose
  `websearch_to_tsquery` for safer user input handling.

</decisions>

<specifics>
## Specific Implementation Details

### Migration shape (new alembic revision)
- Down revision: `chat_sessions_multi` (current head)
- Steps:
  1. `ALTER TABLE doc_chunks ADD COLUMN content_tsv_fr tsvector GENERATED ALWAYS AS (to_tsvector('french', content)) STORED;`
  2. Same for `content_tsv_en` (english).
  3. `CREATE INDEX doc_chunks_tsv_fr_idx ON doc_chunks USING GIN (content_tsv_fr);`
  4. Same GIN index for `content_tsv_en`.
- Existing rows backfilled automatically by GENERATED.

### Reused existing patterns
- Singleton + lazy + async-via-executor pattern from `embedder.py` lines 21–47 → if
  we ever need a Python helper, but for Postgres FTS the SQL itself handles it.
- TTLCache + stats counters pattern from `embedder._embed_cache` and
  `retriever._retrieve_cache`.
- Env-var toggle + `*_stats()` pattern from `reranker.py` lines 28–35, 105–115.
- Healthcheck `/cache-stats` and `/hybrid-info` mirror `/rerank-info` shape in
  `app/rag-service/main.py`.

### Files modified (representative)
- NEW: `app/backend/alembic/versions/hybrid_search_tsvector.py`
- MODIFY: `app/rag-service/retriever.py` — change `retrieve_chunks()` to fan out
  vector + keyword queries, fuse via new helper, pass result to existing `rerank()`.
- NEW: `app/rag-service/hybrid.py` — RRF fusion helper, query-builder helpers,
  `hybrid_enabled()`, `hybrid_stats()`.
- MODIFY: `app/rag-service/main.py` — extend `/cache-stats`, add `/hybrid-info`.
- NO CHANGES: `app/backend/services/rag_client.py`, `routes/chat.py`,
  `app/rag-service/ingestor.py` (generated columns auto-populate).
- NO CHANGES: frontend.

### Verification queries (smoke tests)
```bash
# 1. Exact-ID query (vector usually misses)
curl -X POST http://localhost:8003/retrieve -H 'Content-Type: application/json' \
  -d '{"query":"OT-SEED-C49-M20","top_k":5,"threshold":0.30}'
# Expect: the matching work-order chunk ranks #1.

# 2. Natural-language query (semantic should still win)
curl -X POST http://localhost:8003/retrieve -H 'Content-Type: application/json' \
  -d '{"query":"machines en panne dans la zone CMS","top_k":5,"threshold":0.30}'
# Expect: same or better than vector-only baseline.

# 3. Toggle off + repeat — confirm ordering changes
HYBRID_ENABLED=false docker compose up -d rag-service
# Re-run query 1 → no longer ranks the exact match first.
```

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/rag-service/retriever.py` — entry point we modify; existing TTLCache + stats counters reused as-is.
- `app/rag-service/reranker.py` — downstream consumer, no changes needed. Already overfetch-aware.
- `app/rag-service/main.py` — `/cache-stats` and pattern for `/rerank-info` reused for `/hybrid-info`.
- pgvector cosine SQL already in retriever lines 85–94 — keep verbatim as the "vector branch".
- Alembic head `chat_sessions_multi` — straightforward new revision.
- Named volume `rag_model_cache` — not relevant (no new model downloaded).

### Established Patterns
- Env-flag toggle, default on, *_stats() counters — see reranker.py.
- Lazy singleton via `get_X()` + asyncio executor wrap — see embedder.py.
- Cache key tuple expansion when behavior diverges — already done for reranker.
- GENERATED columns already used elsewhere? Check during planning; if not, document the
  first occurrence in this repo.

### Integration Points
- `retriever.retrieve_chunks()` is the ONLY caller path for retrieval. All callers
  (`/retrieve` endpoint, future endpoints) go through it. Single point of change.
- Backend chat `app/backend/modules/shared/routes/chat.py:167–172` passes
  `top_k=8, threshold=0.30, machine_id=...` — unchanged.

### Constraints from prior decisions
- Phase 12.1 deferred hybrid search explicitly → this phase fulfills that deferral.
- Embedding migration (Phase 12.1 follow-up) made `doc_chunks.embedding` `vector(1024)`.
  Hybrid migration only adds columns; doesn't touch `embedding`.
- No infrastructure additions allowed for Phase 13.1 (locked above).

</code_context>

<deferred>
## Deferred Ideas

- **Elasticsearch container (Phase 13.2)** — kept on roadmap. Triggered only if Phase 13.1
  quality is insufficient after observed real use.
- **Arabic FTS dictionary** — Postgres doesn't ship one. If Arabic queries underperform,
  add `simple` (no-stem) tsvector column as a third source, or move to ES Arabic analyzer.
- **Weighted-score fusion + learned weights** — needs eval harness (separate TODO).
- **Synonyms ("panne" ↔ "défaillance" ↔ "failure")** — best handled by ES synonym filter
  in Phase 13.2.
- **Multi-field boost** (title weighted higher than body) — Postgres FTS supports via
  `setweight()` but our chunks have no title field. Re-evaluate when chunk metadata grows.
- **Phrase queries / proximity** — `websearch_to_tsquery` handles basics; advanced phrase
  scoring is an ES-side win.
- **Fuzzy match (Smith → Smyth)** — Postgres pg_trgm could be added later; ES handles
  natively in Phase 13.2.
- **Eval harness (precision@k, MRR)** — separate TODO item. Until then, hybrid quality
  judged by spot-check verification queries.

</deferred>

---

*Phase: 13-add-hybrid-search-bm25-vector*
*Context gathered: 2026-06-01 via /gsd:discuss-phase*

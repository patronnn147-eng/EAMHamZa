---
phase: 13-add-hybrid-search-bm25-vector-phase-phase-1-postgres-native-phase-2-elasticsearch
plan: 03
type: execute
wave: 3
depends_on:
  - "13-01"
  - "13-02"
files_modified: []
autonomous: false
requirements:
  - HYB-06
  - HYB-07
  - HYB-09
must_haves:
  truths:
    - "Exact-ID smoke query 'OT-SEED-C49-M20' ranks the matching work-order chunk at position 1 when HYBRID_ENABLED=true"
    - "Natural-language smoke query 'machines en panne dans la zone CMS' returns results at least as relevant as the vector-only baseline"
    - "Toggling HYBRID_ENABLED=false and restarting rag-service makes the exact-ID query no longer rank the matching chunk first"
    - "INFO log line per /retrieve call shows vector_hits, keyword_hits, fused count, returned count, and source_mix breakdown"
    - "/cache-stats hybrid counters move (searches, both_count, etc.) after a handful of /retrieve calls"
    - "/hybrid-info reflects the live env: 'enabled' changes when HYBRID_ENABLED is toggled and the container restarted"
    - "BM25 forced failure results in a 500 from /retrieve with a clear log message — no silent vector-only fallback"
  artifacts:
    - path: ".planning/phases/13-add-hybrid-search-bm25-vector-phase-phase-1-postgres-native-phase-2-elasticsearch/13-03-smoke-toggle-observability-SUMMARY.md"
      provides: "Documented evidence (curl outputs, log snippets, EXPLAIN, stats deltas) for each smoke truth"
      min_lines: 60
  key_links:
    - from: "smoke query OT-SEED-C49-M20"
      to: "doc_chunks with OT-SEED-C49-M20 in content"
      via: "keyword branch GIN scan + RRF top-1"
      pattern: "OT-SEED-C49-M20"
    - from: "HYBRID_ENABLED env"
      to: "/hybrid-info enabled field"
      via: "container restart picks up env"
      pattern: "enabled"
    - from: "rag-service container logs"
      to: "per-query observability"
      via: "INFO log line with source_mix"
      pattern: "hybrid query=.*source_mix="
---

<preflight>
All `<automated>` shell commands in this plan assume bash via `docker compose exec`
(Linux container shell) or WSL/Git-Bash on the Windows host. PowerShell direct
execution is NOT supported — the embedded `&&`, single-quoted heredocs, pipes,
`kill "$(cat ...)"`, and `>` redirections are bash-only.

Note on Task 1 step 6 (natural-language French smoke query): the assertion is
qualitative and informational only — there is no machine-checkable ground truth
for "intuitive relevance". The automated verify step is restricted to the
exact-ID case where ground truth is well-defined.
</preflight>

<objective>
End-to-end verification that Phase 13.1 hybrid search is wired correctly and
delivers the locked behavior. No code changes — only running queries, reading
logs, toggling env, and (briefly, in a controlled way) breaking the keyword
branch to confirm the fail-loud contract.

Purpose: prevent regression. CONTEXT.md locked "fail loud on BM25 errors" and
"INFO logs per query showing which source contributed each final chunk" — these
need to be observed live, not just unit-tested. The smoke verification gates
sign-off on Phase 13.1.

Output: a SUMMARY.md packed with the actual curl JSON, the EXPLAIN plan, the
log lines, and the before/after RRF ordering, plus a checkpoint where the user
confirms the qualitative chat retrieval improvement.
</objective>

<execution_context>
@C:/Users/Admin/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Admin/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/13-add-hybrid-search-bm25-vector-phase-phase-1-postgres-native-phase-2-elasticsearch/13-CONTEXT.md
@.planning/phases/13-add-hybrid-search-bm25-vector-phase-phase-1-postgres-native-phase-2-elasticsearch/13-RESEARCH.md
@.planning/phases/13-add-hybrid-search-bm25-vector-phase-phase-1-postgres-native-phase-2-elasticsearch/13-01-migration-tsvector-gin-SUMMARY.md
@.planning/phases/13-add-hybrid-search-bm25-vector-phase-phase-1-postgres-native-phase-2-elasticsearch/13-02-hybrid-module-and-retriever-SUMMARY.md

<interfaces>
<!-- Smoke targets + toggle pattern extracted from RESEARCH §10 + §3 + §8. -->

Smoke corpus prerequisite (per RESEARCH §10):
- Run `make db` and check:
  SELECT id, LEFT(content, 80) FROM doc_chunks WHERE content LIKE '%OT-SEED-C49-M20%' LIMIT 3;
- If zero rows: run `python app/backend/seed_ml_data_m13.py` then either
  trigger Celery `tasks.rag_sync_all` or run
  `python app/backend/scripts/sync_db_to_rag.py --tables ordres_travail`.

Smoke endpoints (default rag-service port is 8003 per docker-compose):
- POST http://localhost:8003/retrieve body
  {"query":"OT-SEED-C49-M20","top_k":5,"threshold":0.30}
- POST http://localhost:8003/retrieve body
  {"query":"machines en panne dans la zone CMS","top_k":5,"threshold":0.30}
- GET  http://localhost:8003/hybrid-info
- GET  http://localhost:8003/cache-stats

Toggle pattern (matches reranker pattern; env is read every call so a
restart-free toggle would actually flip behavior — but to match operational
reality, restart the container):
  HYBRID_ENABLED=false docker compose up -d rag-service
  # verify via /hybrid-info, then re-run the exact-ID query
  HYBRID_ENABLED=true  docker compose up -d rag-service

Fail-loud injection (controlled, reversible). Pick ONE of these reversible
break paths:
  (a) In psql: ALTER TABLE doc_chunks DROP COLUMN content_tsv_fr;
      Restore: alembic downgrade -1 then alembic upgrade head.
  (b) Or: REVOKE SELECT ON doc_chunks FROM the rag-service DB role.
      Restore: GRANT SELECT back.
  (a) is preferred because it directly tests the BM25 SQL path the new code
  added. (b) breaks the vector branch too, which is not what we want to test.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Smoke queries with HYBRID_ENABLED=true — exact-ID + natural-language + log capture + stats delta</name>
  <files>(no code — outputs captured into the plan SUMMARY)</files>
  <action>
1. Preflight — confirm corpus has the smoke target chunk:
   `make db` then run:
     SELECT id, doc_id, LEFT(content, 80) AS preview
     FROM doc_chunks
     WHERE content LIKE '%OT-SEED-C49-M20%'
     LIMIT 3;
   If zero rows, run the M13 seed + sync per the <interfaces> block. Record
   the row count and an example chunk preview in the SUMMARY.

2. Baseline /cache-stats and /hybrid-info:
     curl -s http://localhost:8003/hybrid-info | jq . > /tmp/hi_before.json
     curl -s http://localhost:8003/cache-stats | jq '.hybrid' > /tmp/cs_before.json
   Confirm `enabled` is `true` and counters are at baseline.

3. Clear retrieval cache so smoke queries hit the DB and produce log lines:
     curl -X POST http://localhost:8003/cache-clear -i

4. Tail rag-service logs in the background:
     docker compose logs --follow rag-service > /tmp/rag_smoke.log 2>&1 &
     echo $! > /tmp/rag_log_pid

5. Smoke query 1 — exact-ID (locked smoke from CONTEXT §verification 1):
     curl -s -X POST http://localhost:8003/retrieve \
       -H 'Content-Type: application/json' \
       -d '{"query":"OT-SEED-C49-M20","top_k":5,"threshold":0.30}' \
       | jq . > /tmp/smoke_exact_id.json
   Expected: top-1 chunk's `content` contains the literal string
   `OT-SEED-C49-M20`. If not, FAIL — capture the actual top-5 and stop.

6. Smoke query 2 — natural-language French (locked smoke from CONTEXT
   §verification 2). NOTE: this check is QUALITATIVE / INFORMATIONAL ONLY —
   the automated `<verify>` block intentionally does NOT assert on these
   results because there is no machine-checkable ground truth for "intuitive
   relevance". The result is recorded for the user checkpoint (Task 4):
     curl -s -X POST http://localhost:8003/retrieve \
       -H 'Content-Type: application/json' \
       -d '{"query":"machines en panne dans la zone CMS","top_k":5,"threshold":0.30}' \
       | jq . > /tmp/smoke_nl_fr.json
   Expected: 1-5 chunks. Count may be 0 if corpus lacks French manuals — note
   that case explicitly. If chunks are returned, at least one should be
   intuitively about "down machines in CMS zone".

7. Stop the log tail and extract the per-query INFO lines:
     kill "$(cat /tmp/rag_log_pid)"
     grep "hybrid query=" /tmp/rag_smoke.log
   Must show exactly 2 lines, one per /retrieve call. Each must contain
   `source_mix=(both:X, vector_only:Y, keyword_only:Z)` with the three counts
   summing to the `returned` value.

8. Stats delta:
     curl -s http://localhost:8003/cache-stats | jq '.hybrid' > /tmp/cs_after.json
     diff /tmp/cs_before.json /tmp/cs_after.json || true
   The `searches` counter must have increased by exactly 2 and at least one
   of `vector_only_count`, `keyword_only_count`, `both_count` must have
   increased.

Record everything (curl JSON, log lines, stats diff) verbatim in the plan
SUMMARY.
  </action>
  <verify>
    <automated>python -c "import json; d=json.load(open('/tmp/smoke_exact_id.json')); chunks=d.get('chunks',[]); assert chunks, 'empty chunks'; top=chunks[0]['content']; assert 'OT-SEED-C49-M20' in top, 'top-1 missing exact ID: ' + top[:120]; print('exact-ID smoke OK')"</automated>
  </verify>
  <done>
Smoke query 1 returns the OT-SEED-C49-M20 chunk at position 1. Smoke query 2
returns 0-5 chunks with documented inspection (informational only — assessed
qualitatively in Task 4). Two INFO log lines captured with the
`hybrid query=... source_mix=(both:..., vector_only:..., keyword_only:...)`
shape. /cache-stats hybrid counters moved as expected.
  </done>
</task>

<task type="auto">
  <name>Task 2: Toggle-off A/B — re-run exact-ID query with HYBRID_ENABLED=false, confirm ordering changes</name>
  <files>(no code — toggle test, outputs into SUMMARY)</files>
  <action>
1. Toggle hybrid OFF and restart the service:
     HYBRID_ENABLED=false docker compose up -d rag-service
   Wait for the container to be healthy (loop on `curl -sf
   http://localhost:8003/health`).

2. Confirm the env flipped via /hybrid-info:
     curl -s http://localhost:8003/hybrid-info | jq .
   The `enabled` field must be `false`.

3. Clear the retrieval cache (cache key includes hybrid_enabled, so the prior
   entries are stale-but-different-key — clearing is belt-and-suspenders):
     curl -X POST http://localhost:8003/cache-clear -i

4. Re-run smoke query 1 (exact-ID):
     curl -s -X POST http://localhost:8003/retrieve \
       -H 'Content-Type: application/json' \
       -d '{"query":"OT-SEED-C49-M20","top_k":5,"threshold":0.30}' \
       | jq . > /tmp/smoke_exact_id_off.json
   Compare against /tmp/smoke_exact_id.json. Expected (per RESEARCH §3.A and
   §10): vector-only no longer ranks the exact-ID chunk first OR the top-5
   ordering changes vs the hybrid-on result. The automated verify asserts at
   least one of these conditions:
   - the matching chunk has moved out of position 1, OR
   - the set/ordering of the top-5 chunk identifiers differs from the
     hybrid-on result.
   If vector alone already had it at #1 AND the top-5 order is identical, the
   test fails — that would mean the toggle had no measurable effect, which
   contradicts the locked smoke truth.

5. Toggle hybrid back ON:
     HYBRID_ENABLED=true docker compose up -d rag-service
     curl -s http://localhost:8003/hybrid-info | jq .enabled  # → true

6. Sanity re-run of the exact-ID query:
     curl -s -X POST http://localhost:8003/retrieve \
       -H 'Content-Type: application/json' \
       -d '{"query":"OT-SEED-C49-M20","top_k":5,"threshold":0.30}' \
       | jq . > /tmp/smoke_exact_id_back_on.json
   Top-1 must again contain the literal `OT-SEED-C49-M20`.

Record both off/on JSON and the qualitative ordering diff in the SUMMARY.
  </action>
  <verify>
    <automated>python -c "
import json
on   = json.load(open('/tmp/smoke_exact_id.json'))
off  = json.load(open('/tmp/smoke_exact_id_off.json'))
back = json.load(open('/tmp/smoke_exact_id_back_on.json'))

def top1_content(d):
    chunks = d.get('chunks') or [{}]
    return chunks[0].get('content', '')

def chunk_ids(d, n=5):
    # Use first 120 chars of content as a stable surrogate identifier
    return [c.get('content','')[:120] for c in d.get('chunks', [])[:n]]

on_top   = top1_content(on)
back_top = top1_content(back)
off_top  = top1_content(off)

assert 'OT-SEED-C49-M20' in on_top,   'hybrid-on baseline broken: top1=' + on_top[:120]
assert 'OT-SEED-C49-M20' in back_top, 'hybrid-on after restart broken: top1=' + back_top[:120]

# Toggle-off MUST change something: either the exact-ID chunk drops from #1,
# or the top-5 identifier list differs from the hybrid-on top-5.
hybrid_top1_id  = on_top[:120]
vector_top1_id  = off_top[:120]
hybrid_ids = chunk_ids(on, 5)
vector_ids = chunk_ids(off, 5)

assert hybrid_top1_id != vector_top1_id or sorted(hybrid_ids[:5]) != sorted(vector_ids[:5]), \
    'expected toggle-off to change ordering, but top-5 are identical'

# Informational
off_all = [c.get('content','') for c in off.get('chunks', [])]
off_anywhere = any('OT-SEED-C49-M20' in c for c in off_all)
print('toggle smoke OK; vector_only_top1_has_id=' + str('OT-SEED-C49-M20' in off_top) + ' vector_only_anywhere_in_top5=' + str(off_anywhere))
"</automated>
  </verify>
  <done>
With HYBRID_ENABLED=false, /hybrid-info shows enabled=false; the exact-ID
top-5 result differs from the hybrid-on result (either the exact-ID chunk
moved out of position 1, or the top-5 ordering changed). After toggling back
to true, behavior matches the original hybrid-on result.
  </done>
</task>

<task type="auto">
  <name>Task 3: Fail-loud BM25 — break one tsvector column, confirm HTTP 500 + clear log, then restore</name>
  <files>(no code — controlled break test, outputs into SUMMARY)</files>
  <action>
WARNING: This task intentionally breaks the schema temporarily. Run on dev
only. Restore step is mandatory.

1. Open `make db` in one terminal.

2. In a second terminal, tail rag-service logs:
     docker compose logs --follow rag-service > /tmp/rag_failloud.log 2>&1 &
     echo $! > /tmp/rag_failloud_pid

3. In psql, drop the french tsvector column (reversible via alembic):
     ALTER TABLE doc_chunks DROP COLUMN content_tsv_fr;
   This will also implicitly drop `doc_chunks_tsv_fr_idx`. Confirm with:
     \d doc_chunks

4. Clear cache and issue a /retrieve call expected to FAIL with HTTP 500.
   Capture BOTH the body and the response HTTP code separately so the
   automated verify can assert on the code:
     curl -X POST http://localhost:8003/cache-clear -i
     curl -s -o /tmp/failloud_body.json \
       -w '%{http_code}' \
       -X POST http://localhost:8003/retrieve \
       -H 'Content-Type: application/json' \
       -d '{"query":"test"}' > /tmp/failloud_code
   Expected: `cat /tmp/failloud_code` prints exactly `500`. Capture the
   response body and the matching log line:
     kill "$(cat /tmp/rag_failloud_pid)"
     grep -E "BM25 keyword branch failed|content_tsv_fr" /tmp/rag_failloud.log
   The log must show the BM25 error message from retriever.py with a clear
   reference to the missing column (Postgres "column does not exist" error).

5. RESTORE the schema:
     docker compose exec backend alembic downgrade -1
     docker compose exec backend alembic upgrade head
   (downgrade removes both tsv cols + indexes — since we already dropped
   content_tsv_fr manually, alembic may report idempotency; that's fine. The
   upgrade reapplies both columns with auto-backfill.)

6. Verify recovery:
     curl -s -X POST http://localhost:8003/retrieve \
       -H 'Content-Type: application/json' \
       -d '{"query":"OT-SEED-C49-M20","top_k":5,"threshold":0.30}' \
       | jq '.chunks[0].content' | head -c 200
   Must again return a chunk containing `OT-SEED-C49-M20`.

Record the HTTP 500, the log message, and the post-restore success in the
SUMMARY.
  </action>
  <verify>
    <automated>python -c "
import os
code = open('/tmp/failloud_code').read().strip()
assert code == '500', 'expected HTTP 500 on fail-loud, got: ' + repr(code)
log = open('/tmp/rag_failloud.log').read()
assert 'BM25 keyword branch failed' in log or 'content_tsv_fr' in log, \
    'no fail-loud log line found in rag-service logs'
print('fail-loud HTTP 500 + log message OK')
"</automated>
  </verify>
  <done>
With content_tsv_fr dropped: /retrieve returned HTTP 500 (asserted from
/tmp/failloud_code); rag-service log contains a clear BM25 failure message
naming the missing column. After restore: /retrieve again ranks
OT-SEED-C49-M20 at top-1. Schema is back to the post-13-01 state (both
tsvector cols + both GIN indexes present, all rows populated).
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 4: User confirms qualitative chat retrieval improvement</name>
  <what-built>
Phase 13.1 hybrid search (Postgres FTS + RRF). Plan 13-01 added the schema and
indexes; Plan 13-02 added the hybrid module + retriever fan-out + observability;
Tasks 1-3 above verified the locked behaviors (exact-ID at top-1, toggle-off
regression, fail-loud BM25). What is NOT auto-verifiable is the qualitative
chat experience for the user.
  </what-built>
  <how-to-verify>
1. With HYBRID_ENABLED=true (default), open the existing chat UI in the
   frontend and ask 2-3 questions that previously returned weak results:
   - One question that includes an exact code (work-order number, machine ID,
     part reference) — e.g. "What happened on OT-SEED-C49-M20?"
   - One natural-language question about a machine state — e.g. "Quelles
     machines de la zone CMS sont tombées en panne récemment?"
   - One question that mixes both — e.g. "Show me critical failures involving
     tool wear on machine 20."

2. For each, compare to memory of the pre-13 chat quality. The expected
   pattern (per CONTEXT.md goal): exact codes now hit, natural-language
   queries stay at least as good.

3. Confirm the rag-service logs show one `hybrid query=…` INFO line per chat
   message (via `docker compose logs --tail=50 rag-service`).

4. Optionally hit /cache-stats and confirm the hybrid counters keep moving.

Resume signal:
  - "approved" if exact-ID queries now hit AND natural-language quality is
    preserved.
  - "regression: <description>" if any natural-language query got worse — in
    that case escalate to a gap-closure plan (e.g., re-tune overfetch, gate
    keyword side stricter, or revisit tie-break).
  </how-to-verify>
  <resume-signal>Type "approved" or describe regressions you observed.</resume-signal>
</task>

</tasks>

<verification>
- Tasks 1-3 automated checks all green.
- User checkpoint (Task 4) approved.
- SUMMARY.md captures: smoke JSON outputs, INFO log lines, stats deltas,
  toggle-off ordering diff, fail-loud 500 + log + restore evidence, and the
  user's verbatim approval note.
</verification>

<success_criteria>
- Exact-ID smoke query ranks OT-SEED-C49-M20 at position 1 with HYBRID_ENABLED=true.
- Natural-language smoke query returns at least the baseline quality
  (qualitative, judged at the Task 4 checkpoint).
- HYBRID_ENABLED=false causes a measurable ordering change for the exact-ID
  query (asserted by Task 2 automated verify).
- /hybrid-info `enabled` field tracks the env across restarts.
- /cache-stats hybrid counters move with traffic.
- BM25 errors propagate as HTTP 500 (asserted by Task 3 automated verify
  against /tmp/failloud_code) with a clear log message — no silent fallback
  observed.
- User approves the qualitative chat improvement OR a clear regression note is
  filed for gap closure.
</success_criteria>

<output>
After completion, create
`.planning/phases/13-add-hybrid-search-bm25-vector-phase-phase-1-postgres-native-phase-2-elasticsearch/13-03-smoke-toggle-observability-SUMMARY.md`
with:
- Pre-flight corpus check (row count for `OT-SEED-C49-M20`).
- All curl JSON outputs verbatim (exact-ID, NL-FR, toggle-off, restored,
  fail-loud body + HTTP code from /tmp/failloud_code).
- All extracted INFO log lines (per-query source_mix; fail-loud BM25 error).
- /cache-stats hybrid block before/after diff.
- /hybrid-info JSON in both enabled states.
- User checkpoint result (approved / regression).
- Any anomaly notes (e.g. corpus didn't contain a French manual, so NL-FR
  query returned 0 chunks).
</output>
</output>

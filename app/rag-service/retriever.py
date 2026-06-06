"""
Semantic + keyword retrieval.

When HYBRID_ENABLED=true (default, per Phase 13.1):
    Vector top-30 (pgvector cosine, threshold-gated) is fanned out in parallel
    with keyword top-30 (Postgres FTS, GREATEST(rank_fr, rank_en)). The two
    lists are fused via Reciprocal Rank Fusion (k=60), trimmed to 30, then
    forwarded to the cross-encoder reranker (unchanged). The reranker returns
    top_k to the caller.

When HYBRID_ENABLED=false:
    Behavior is byte-identical to the pre-13 path: vector-only retrieval +
    existing reranker overfetch math.

Caching: identical (query, machine_id, top_k, threshold, hybrid_enabled)
tuples are cached in-memory for 5 minutes. The hybrid_enabled flag is part of
the key so toggling does not return stale results. Cache is reset on container
restart and on any ingest/delete (see clear_retrieval_cache()).

BM25 errors fail loud (per CONTEXT.md) -- no silent vector-only fallback.
"""
import logging
from typing import Optional

from cachetools import TTLCache
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from embedder import embed_text, vec_to_str
from hybrid import (
    HYBRID_OVERFETCH,
    HYBRID_RRF_K,
    hybrid_enabled,
    keyword_search,
    record_call,
    rrf_fuse,
)
from reranker import compute_overfetch, rerank, rerank_enabled

logger = logging.getLogger(__name__)

# Retrieval result cache
RETRIEVE_CACHE_SIZE = 512
RETRIEVE_CACHE_TTL = 300  # 5 minutes
_retrieve_cache: TTLCache = TTLCache(maxsize=RETRIEVE_CACHE_SIZE, ttl=RETRIEVE_CACHE_TTL)
_retrieve_hits = 0
_retrieve_misses = 0


def clear_retrieval_cache() -> None:
    """Invalidate the retrieval cache. Call after any ingest or delete."""
    _retrieve_cache.clear()
    logger.info("Retrieval cache cleared.")


def retrieve_cache_stats() -> dict:
    total = _retrieve_hits + _retrieve_misses
    hit_rate = (_retrieve_hits / total) if total else 0.0
    return {
        "size": len(_retrieve_cache),
        "max_size": RETRIEVE_CACHE_SIZE,
        "ttl_seconds": RETRIEVE_CACHE_TTL,
        "hits": _retrieve_hits,
        "misses": _retrieve_misses,
        "hit_rate": round(hit_rate, 4),
    }


async def retrieve_chunks(
    query: str,
    db: AsyncSession,
    machine_id: Optional[int] = None,
    top_k: int = 3,
    threshold: float = 0.30,
) -> list[dict]:
    """
    Embed query → cosine similarity search → return top-k chunks above threshold.

    Args:
        query: Natural language query string
        db: Async DB session
        machine_id: Optional filter — only chunks from docs linked to this machine
        top_k: Max number of chunks to return
        threshold: Min cosine similarity (0.0-1.0). Chunks below this are excluded.

    Returns:
        List of {content, metadata, similarity} dicts. Empty list if nothing above threshold.
    """
    global _retrieve_hits, _retrieve_misses

    hybrid_on = hybrid_enabled()
    cache_key = (query.strip(), machine_id, top_k, round(threshold, 4), hybrid_on)
    cached = _retrieve_cache.get(cache_key)
    if cached is not None:
        _retrieve_hits += 1
        return cached
    _retrieve_misses += 1

    # ── Stage 1a: vector branch ──────────────────────────────────────────────
    # Always runs (hybrid_on or vector-only). Empty list on embedding failure
    # is the existing pre-13 behavior; we preserve it in both modes. When
    # hybrid_on, the keyword branch may still produce hits even if vector fails.
    overfetch = HYBRID_OVERFETCH if hybrid_on else compute_overfetch(top_k)
    candidates: list[dict] = []
    try:
        query_vec = await embed_text(query)
        vec_str = vec_to_str(query_vec)
    except Exception as e:
        logger.error(f"Embedding failed for query: {e}")
        if not hybrid_on:
            return []
        vec_str = None  # skip vector SQL; let keyword branch run

    if vec_str is not None:
        try:
            sql = text("""
                SELECT dc.id AS chunk_id, dc.content, dc.metadata,
                       1 - (dc.embedding <=> CAST(:vec AS vector)) AS similarity
                FROM doc_chunks dc
                JOIN documents d ON dc.doc_id = d.id
                WHERE (CAST(:machine_id AS integer) IS NULL OR d.machine_id = CAST(:machine_id AS integer))
                  AND 1 - (dc.embedding <=> CAST(:vec AS vector)) > :threshold
                ORDER BY dc.embedding <=> CAST(:vec AS vector)
                LIMIT :top_k
            """)

            result = await db.execute(sql, {
                "vec": vec_str,
                "machine_id": machine_id,
                "threshold": threshold,
                "top_k": overfetch,
            })
            rows = result.fetchall()

            candidates = [
                {
                    "chunk_id": r.chunk_id,
                    "content": r.content,
                    "metadata": r.metadata,
                    "similarity": float(r.similarity),
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Retrieval SQL failed: {e}")
            if not hybrid_on:
                return []
            candidates = []  # let keyword branch still contribute

    # ── Stage 1b: keyword branch (hybrid only) ───────────────────────────────
    # FAIL LOUD on BM25 errors per CONTEXT.md -- no silent fallback.
    if hybrid_on:
        try:
            keyword_hits = await keyword_search(
                query.strip(), db, machine_id, top_k=HYBRID_OVERFETCH
            )
        except Exception as e:
            logger.error(f"BM25 keyword branch failed: {e}", exc_info=True)
            raise  # propagate to FastAPI -> 500
    else:
        keyword_hits = []

    # ── Stage 2: fusion (hybrid only) ────────────────────────────────────────
    if hybrid_on:
        fused = rrf_fuse(
            candidates, keyword_hits, k=HYBRID_RRF_K, limit=HYBRID_OVERFETCH
        )
    else:
        fused = candidates  # vector-only legacy path

    # ── Stage 3: cross-encoder rerank ────────────────────────────────────────
    if rerank_enabled() and fused:
        results = await rerank(query.strip(), fused, top_k)
    else:
        results = fused[:top_k]

    # ── Stats + INFO log (hybrid only) ───────────────────────────────────────
    if hybrid_on:
        source_mix = []
        for c in results:
            has_v = "vector_rank" in c
            has_k = "keyword_rank" in c
            source_mix.append(
                "both" if has_v and has_k
                else ("vector_only" if has_v else "keyword_only")
            )
        record_call(
            vector_n=len(candidates),
            keyword_n=len(keyword_hits),
            returned_with_source=source_mix,
        )
        logger.info(
            "hybrid query=%r machine_id=%s vector_hits=%d keyword_hits=%d "
            "fused=%d returned=%d source_mix=(both:%d, vector_only:%d, keyword_only:%d)",
            query.strip()[:80], machine_id,
            len(candidates), len(keyword_hits), len(fused), len(results),
            source_mix.count("both"),
            source_mix.count("vector_only"),
            source_mix.count("keyword_only"),
        )

    _retrieve_cache[cache_key] = results
    return results

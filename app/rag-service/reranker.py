"""
Cross-encoder reranker — stage 2 of RAG retrieval.

After bi-encoder retrieves candidate chunks via pgvector cosine similarity,
the cross-encoder scores each (query, chunk) pair jointly. This produces
more accurate relevance scores than the bi-encoder, at the cost of being
slower per pair — feasible only because we only rerank a small candidate set.

Same singleton + async-via-executor pattern as embedder.py.
"""

import asyncio
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Public model — no HF_TOKEN required. Multilingual (FR/EN/AR), ~568 MB,
# CPU-friendly, same family as the bi-encoder (BAAI/bge-m3).
MODEL_NAME = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")

# Overfetch multiplier — fetch (top_k * MULT) candidates from pgvector,
# rerank them, then trim to top_k. Capped to avoid huge cross-encoder batches.
OVERFETCH = int(os.getenv("RERANK_OVERFETCH", "4"))
OVERFETCH_MAX = int(os.getenv("RERANK_OVERFETCH_MAX", "50"))

# Lazy singleton — loaded on first call, never reloaded.
_model = None
_load_lock = asyncio.Lock()

# Stats (mirrors embedder/retriever stats pattern)
_reranks = 0  # number of rerank() calls
_candidates_seen = 0  # total candidates scored (cumulative)


def rerank_enabled() -> bool:
    """Toggle: env RERANK_ENABLED, default true."""
    return os.getenv("RERANK_ENABLED", "true").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _get_model():
    """Lazy import + load — keeps startup fast when reranker disabled."""
    global _model
    if _model is None:
        from sentence_transformers import CrossEncoder

        logger.info(f"Loading cross-encoder model: {MODEL_NAME}")
        _model = CrossEncoder(MODEL_NAME)
        logger.info("Cross-encoder model loaded.")
    return _model


def _sync_score(query: str, contents: list[str]) -> list[float]:
    """Sync scoring — run inside thread pool executor."""
    model = _get_model()
    pairs = [(query, c) for c in contents]
    scores = model.predict(pairs)
    return [float(s) for s in scores]


async def rerank(query: str, candidates: list[dict], top_k: int) -> list[dict]:
    """
    Re-rank candidates by cross-encoder relevance to query.

    Args:
        query: original user query string
        candidates: list of {content, metadata, similarity} dicts from bi-encoder
        top_k: how many to return after reranking

    Returns:
        list of candidates, sorted by rerank_score desc, trimmed to top_k.
        Each candidate gains a `rerank_score` float field. `similarity` is preserved.
        If candidates is empty, returns []. If reranker fails, returns the
        original candidates trimmed to top_k (graceful degradation).
    """
    global _reranks, _candidates_seen

    if not candidates:
        return []
    if not rerank_enabled():
        return candidates[:top_k]

    contents = [c["content"] for c in candidates]
    try:
        loop = asyncio.get_event_loop()
        scores = await loop.run_in_executor(None, _sync_score, query, contents)
    except Exception as e:
        logger.exception(f"Rerank failed, falling back to bi-encoder order: {e}")
        return candidates[:top_k]

    _reranks += 1
    _candidates_seen += len(candidates)

    for c, s in zip(candidates, scores):
        c["rerank_score"] = s

    candidates.sort(key=lambda c: c.get("rerank_score", 0.0), reverse=True)
    return candidates[:top_k]


def compute_overfetch(top_k: int) -> int:
    """How many candidates pgvector should return for reranking."""
    if not rerank_enabled():
        return top_k
    return min(top_k * OVERFETCH, OVERFETCH_MAX)


def rerank_stats() -> dict:
    """Stats endpoint payload — matches existing embedder/retriever stats shape."""
    avg = (_candidates_seen / _reranks) if _reranks else 0.0
    return {
        "enabled": rerank_enabled(),
        "model": MODEL_NAME,
        "overfetch": OVERFETCH,
        "overfetch_max": OVERFETCH_MAX,
        "reranks": _reranks,
        "candidates_scored": _candidates_seen,
        "avg_candidates_per_call": round(avg, 2),
    }

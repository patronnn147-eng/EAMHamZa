"""
Embedding model singleton.

SentenceTransformer.encode() is synchronous — call via run_in_executor
to avoid blocking the async event loop.

Caching:
  - Single-text embeddings (queries) are cached in a TTLCache for 1 hour.
  - Batch embeddings (ingestion) bypass cache — each chunk is unique anyway.
"""
import asyncio
import logging

from cachetools import TTLCache
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_NAME = "BAAI/bge-m3"
EMBEDDING_DIM = 1024

# Query embedding cache — same question asked twice → skip embed compute
EMBED_CACHE_SIZE = 1024
EMBED_CACHE_TTL = 3600  # 1 hour
_embed_cache: TTLCache = TTLCache(maxsize=EMBED_CACHE_SIZE, ttl=EMBED_CACHE_TTL)
_embed_hits = 0
_embed_misses = 0

_model: SentenceTransformer | None = None


def get_embedder() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info(f"Loading sentence-transformer model: {MODEL_NAME}")
        _model = SentenceTransformer(MODEL_NAME)
        logger.info("Model loaded.")
    return _model


def _sync_embed(texts: list[str]) -> list[list[float]]:
    """Sync batch embed — run in thread pool, never call directly in async context."""
    model = get_embedder()
    vectors = model.encode(texts, normalize_embeddings=True, batch_size=32)
    return vectors.tolist()


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Async-safe batch embed. Runs sync encode in thread pool executor."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_embed, texts)


async def embed_text(text: str) -> list[float]:
    """
    Async-safe single text embed with in-memory TTL cache.

    Cache key = raw text string (post-strip). Cache reset on container restart.
    """
    global _embed_hits, _embed_misses
    key = text.strip()
    cached = _embed_cache.get(key)
    if cached is not None:
        _embed_hits += 1
        return cached

    _embed_misses += 1
    results = await embed_batch([key])
    vec = results[0]
    _embed_cache[key] = vec
    return vec


def embed_cache_stats() -> dict:
    """Return cache hit/miss counters for debug endpoint."""
    total = _embed_hits + _embed_misses
    hit_rate = (_embed_hits / total) if total else 0.0
    return {
        "size": len(_embed_cache),
        "max_size": EMBED_CACHE_SIZE,
        "ttl_seconds": EMBED_CACHE_TTL,
        "hits": _embed_hits,
        "misses": _embed_misses,
        "hit_rate": round(hit_rate, 4),
    }


def vec_to_str(vector: list[float]) -> str:
    """Convert float list to pgvector string format: [x,y,z,...]"""
    return "[" + ",".join(f"{x:.6f}" for x in vector) + "]"

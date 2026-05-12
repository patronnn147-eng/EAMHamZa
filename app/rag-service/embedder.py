"""
Embedding model singleton.

SentenceTransformer.encode() is synchronous — call via run_in_executor
to avoid blocking the async event loop.
"""
import asyncio
import logging
from functools import partial

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384

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
    """Async-safe single text embed."""
    results = await embed_batch([text])
    return results[0]


def vec_to_str(vector: list[float]) -> str:
    """Convert float list to pgvector string format: [x,y,z,...]"""
    return "[" + ",".join(f"{x:.6f}" for x in vector) + "]"

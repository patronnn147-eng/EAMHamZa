"""
Unit tests for retriever.retrieve_chunks() — hybrid toggle, cache key
widening, fail-loud BM25, source mix.

DB is mocked (no real Postgres). embed_text + keyword_search are monkeypatched.
"""
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

# Tests run from /app inside rag-service container
sys.path.insert(0, "/app")

import retriever
from hybrid import HYBRID_OVERFETCH, HYBRID_RRF_K


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_row(chunk_id, content, similarity, metadata=None):
    """Mimic a sqlalchemy Row with attribute access."""
    return SimpleNamespace(
        chunk_id=chunk_id,
        content=content,
        metadata=metadata or {},
        similarity=similarity,
    )


def _make_db_with_vector_rows(rows):
    """Build an AsyncMock DB whose .execute() returns rows from .fetchall()."""
    db = MagicMock()
    fetch_result = MagicMock()
    fetch_result.fetchall = MagicMock(return_value=rows)
    db.execute = AsyncMock(return_value=fetch_result)
    return db


def _patch_no_rerank(monkeypatch):
    """Disable the cross-encoder so we can assert on the fused list directly."""
    monkeypatch.setattr(retriever, "rerank_enabled", lambda: False)


def _patch_embedder(monkeypatch):
    async def fake_embed(q):
        return [0.1] * 1024
    monkeypatch.setattr(retriever, "embed_text", fake_embed)
    monkeypatch.setattr(retriever, "vec_to_str", lambda v: "[fake-vec]")


def _clear_retrieval_cache():
    retriever._retrieve_cache.clear()


# ── Cache key shape ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cache_key_is_5_tuple_ending_in_hybrid_flag(monkeypatch):
    """Cache key must include hybrid_enabled as the 5th element."""
    _clear_retrieval_cache()
    monkeypatch.setenv("HYBRID_ENABLED", "true")
    _patch_no_rerank(monkeypatch)
    _patch_embedder(monkeypatch)

    async def fake_keyword(q, db, machine_id, top_k):
        return []
    monkeypatch.setattr(retriever, "keyword_search", fake_keyword)

    rows = [_make_row(1, "hello", 0.9)]
    db = _make_db_with_vector_rows(rows)

    await retriever.retrieve_chunks("q1", db, machine_id=None, top_k=3, threshold=0.3)

    keys = list(retriever._retrieve_cache.keys())
    assert len(keys) == 1
    key = keys[0]
    assert len(key) == 5
    assert key == ("q1", None, 3, 0.3, True)


@pytest.mark.asyncio
async def test_toggling_hybrid_changes_cache_key(monkeypatch):
    """Same query+machine+top_k+threshold but toggled hybrid -> different cache entry."""
    _clear_retrieval_cache()
    _patch_no_rerank(monkeypatch)
    _patch_embedder(monkeypatch)

    async def fake_keyword(q, db, machine_id, top_k):
        return []
    monkeypatch.setattr(retriever, "keyword_search", fake_keyword)

    rows = [_make_row(7, "hello", 0.9)]
    db = _make_db_with_vector_rows(rows)

    monkeypatch.setenv("HYBRID_ENABLED", "true")
    await retriever.retrieve_chunks("q", db, machine_id=None, top_k=3, threshold=0.3)

    monkeypatch.setenv("HYBRID_ENABLED", "false")
    await retriever.retrieve_chunks("q", db, machine_id=None, top_k=3, threshold=0.3)

    keys = list(retriever._retrieve_cache.keys())
    assert len(keys) == 2
    # One key ends in True, the other in False
    assert {k[-1] for k in keys} == {True, False}


# ── Vector-only path (HYBRID_ENABLED=false) ───────────────────────────────────

@pytest.mark.asyncio
async def test_hybrid_disabled_skips_keyword_branch(monkeypatch):
    """When hybrid is off, keyword_search must NOT be called."""
    _clear_retrieval_cache()
    monkeypatch.setenv("HYBRID_ENABLED", "false")
    _patch_no_rerank(monkeypatch)
    _patch_embedder(monkeypatch)

    keyword_mock = AsyncMock(return_value=[])
    monkeypatch.setattr(retriever, "keyword_search", keyword_mock)

    rows = [
        _make_row(1, "vec-a", 0.9),
        _make_row(2, "vec-b", 0.7),
    ]
    db = _make_db_with_vector_rows(rows)

    results = await retriever.retrieve_chunks(
        "q", db, machine_id=None, top_k=3, threshold=0.3
    )

    keyword_mock.assert_not_called()
    # Vector-only path -- no fused_score or vector_rank fields added.
    assert len(results) == 2
    for r in results:
        assert "fused_score" not in r
        assert "vector_rank" not in r


@pytest.mark.asyncio
async def test_hybrid_disabled_uses_compute_overfetch_top_k(monkeypatch):
    """Pre-13 behavior: vector overfetch derived from reranker.compute_overfetch."""
    _clear_retrieval_cache()
    monkeypatch.setenv("HYBRID_ENABLED", "false")
    _patch_no_rerank(monkeypatch)
    _patch_embedder(monkeypatch)
    monkeypatch.setattr(retriever, "compute_overfetch", lambda top_k: 99)

    rows = [_make_row(1, "x", 0.9)]
    db = _make_db_with_vector_rows(rows)

    await retriever.retrieve_chunks("q", db, machine_id=None, top_k=3, threshold=0.3)

    # Vector SQL was called with top_k=99 (the patched compute_overfetch return).
    args, kwargs = db.execute.call_args
    sql_params = args[1]
    assert sql_params["top_k"] == 99


# ── Hybrid path (default) ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_hybrid_enabled_uses_hybrid_overfetch(monkeypatch):
    """When hybrid is on, vector branch must use HYBRID_OVERFETCH (30), not compute_overfetch."""
    _clear_retrieval_cache()
    monkeypatch.setenv("HYBRID_ENABLED", "true")
    _patch_no_rerank(monkeypatch)
    _patch_embedder(monkeypatch)

    async def fake_keyword(q, db, machine_id, top_k):
        return []
    monkeypatch.setattr(retriever, "keyword_search", fake_keyword)

    rows = [_make_row(1, "x", 0.9)]
    db = _make_db_with_vector_rows(rows)

    await retriever.retrieve_chunks("q", db, machine_id=None, top_k=3, threshold=0.3)

    args, kwargs = db.execute.call_args
    sql_params = args[1]
    assert sql_params["top_k"] == HYBRID_OVERFETCH == 30


@pytest.mark.asyncio
async def test_hybrid_enabled_fuses_both_branches(monkeypatch):
    """RRF merges vector + keyword lists, dedup by chunk_id."""
    _clear_retrieval_cache()
    monkeypatch.setenv("HYBRID_ENABLED", "true")
    _patch_no_rerank(monkeypatch)
    _patch_embedder(monkeypatch)

    async def fake_keyword(q, db, machine_id, top_k):
        return [
            {"chunk_id": 3, "content": "kw-c", "metadata": {}, "ts_rank_cd": 0.5},
            {"chunk_id": 1, "content": "vec-a", "metadata": {}, "ts_rank_cd": 0.3},
        ]
    monkeypatch.setattr(retriever, "keyword_search", fake_keyword)

    rows = [
        _make_row(1, "vec-a", 0.9),
        _make_row(2, "vec-b", 0.7),
    ]
    db = _make_db_with_vector_rows(rows)

    results = await retriever.retrieve_chunks(
        "q", db, machine_id=None, top_k=10, threshold=0.3
    )

    # 3 unique chunks (1 appears in both branches but deduped by chunk_id).
    chunk_ids = {r["chunk_id"] for r in results}
    assert chunk_ids == {1, 2, 3}
    # All fused entries carry fused_score
    for r in results:
        assert "fused_score" in r
    # The one in both lists must have both rank stamps
    one = next(r for r in results if r["chunk_id"] == 1)
    assert "vector_rank" in one and "keyword_rank" in one


# ── Fail-loud BM25 ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bm25_error_propagates_fail_loud(monkeypatch):
    """BM25 SQL error must NOT be swallowed -- per CONTEXT.md fail-loud rule."""
    _clear_retrieval_cache()
    monkeypatch.setenv("HYBRID_ENABLED", "true")
    _patch_no_rerank(monkeypatch)
    _patch_embedder(monkeypatch)

    class BoomError(RuntimeError):
        pass

    async def boom(q, db, machine_id, top_k):
        raise BoomError("simulated BM25 failure")
    monkeypatch.setattr(retriever, "keyword_search", boom)

    rows = [_make_row(1, "x", 0.9)]
    db = _make_db_with_vector_rows(rows)

    with pytest.raises(BoomError):
        await retriever.retrieve_chunks(
            "q", db, machine_id=None, top_k=3, threshold=0.3
        )


# ── Embedding failure path ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_embedding_failure_returns_empty_when_hybrid_off(monkeypatch):
    """Pre-13 behavior preserved: embedding fails -> return []."""
    _clear_retrieval_cache()
    monkeypatch.setenv("HYBRID_ENABLED", "false")
    _patch_no_rerank(monkeypatch)

    async def bad_embed(q):
        raise RuntimeError("embed boom")
    monkeypatch.setattr(retriever, "embed_text", bad_embed)

    db = _make_db_with_vector_rows([])
    out = await retriever.retrieve_chunks(
        "q", db, machine_id=None, top_k=3, threshold=0.3
    )
    assert out == []


# ── Empty fusion -> no rerank call, return [] ─────────────────────────────────

@pytest.mark.asyncio
async def test_empty_both_branches_returns_empty_no_rerank(monkeypatch):
    """When both branches return 0 rows, rerank() must not be called."""
    _clear_retrieval_cache()
    monkeypatch.setenv("HYBRID_ENABLED", "true")
    _patch_embedder(monkeypatch)

    # rerank_enabled True but never called because fused is empty
    monkeypatch.setattr(retriever, "rerank_enabled", lambda: True)
    rerank_mock = AsyncMock(return_value=[])
    monkeypatch.setattr(retriever, "rerank", rerank_mock)

    async def fake_keyword(q, db, machine_id, top_k):
        return []
    monkeypatch.setattr(retriever, "keyword_search", fake_keyword)

    db = _make_db_with_vector_rows([])
    out = await retriever.retrieve_chunks(
        "q", db, machine_id=None, top_k=3, threshold=0.3
    )
    assert out == []
    rerank_mock.assert_not_called()


# ── Stats counter wiring ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stats_counters_increment_on_hybrid_call(monkeypatch):
    """record_call() must be invoked when hybrid is on."""
    _clear_retrieval_cache()
    monkeypatch.setenv("HYBRID_ENABLED", "true")
    _patch_no_rerank(monkeypatch)
    _patch_embedder(monkeypatch)

    async def fake_keyword(q, db, machine_id, top_k):
        return [{"chunk_id": 9, "content": "kw", "metadata": {}, "ts_rank_cd": 0.5}]
    monkeypatch.setattr(retriever, "keyword_search", fake_keyword)

    captured = {}

    def fake_record(vector_n, keyword_n, returned_with_source):
        captured["vector_n"] = vector_n
        captured["keyword_n"] = keyword_n
        captured["mix"] = list(returned_with_source)
    monkeypatch.setattr(retriever, "record_call", fake_record)

    rows = [_make_row(1, "vec", 0.9)]
    db = _make_db_with_vector_rows(rows)

    out = await retriever.retrieve_chunks(
        "q", db, machine_id=None, top_k=10, threshold=0.3
    )

    assert captured["vector_n"] == 1
    assert captured["keyword_n"] == 1
    # Two unique chunks (1 vector_only, 9 keyword_only)
    assert sorted(captured["mix"]) == ["keyword_only", "vector_only"]
    assert len(out) == 2


@pytest.mark.asyncio
async def test_stats_not_called_when_hybrid_off(monkeypatch):
    _clear_retrieval_cache()
    monkeypatch.setenv("HYBRID_ENABLED", "false")
    _patch_no_rerank(monkeypatch)
    _patch_embedder(monkeypatch)

    record_mock = MagicMock()
    monkeypatch.setattr(retriever, "record_call", record_mock)

    rows = [_make_row(1, "vec", 0.9)]
    db = _make_db_with_vector_rows(rows)

    await retriever.retrieve_chunks("q", db, machine_id=None, top_k=3, threshold=0.3)
    record_mock.assert_not_called()


# ── Constants sanity ──────────────────────────────────────────────────────────

def test_constants_match_locked_values():
    assert HYBRID_OVERFETCH == 30
    assert HYBRID_RRF_K == 60

"""
Unit tests for hybrid.rrf_fuse() + hybrid.hybrid_enabled() + constants.

Covers the worked example in 13-RESEARCH.md §4 plus edge cases:
  - dedup by chunk_id (not by content)
  - tie-break: vector-side wins over keyword-only at equal fused_score
  - empty inputs
  - one-sided inputs (vector-only, keyword-only)
  - limit parameter
  - env-toggle truthy/falsy cases for hybrid_enabled()

No DB touched -- pure function tests.
"""
import sys

import pytest

# Tests run from /app inside rag-service container
sys.path.insert(0, "/app")

from hybrid import (
    FTS_CONFIGS,
    HYBRID_OVERFETCH,
    HYBRID_RRF_K,
    TIE_BREAK,
    hybrid_enabled,
    rrf_fuse,
)


# ── Constants ─────────────────────────────────────────────────────────────────

def test_constants_locked():
    assert HYBRID_RRF_K == 60
    assert HYBRID_OVERFETCH == 30
    assert FTS_CONFIGS == ("french", "english")
    assert TIE_BREAK == "vector_similarity_desc"


# ── rrf_fuse: worked example from RESEARCH §4 ─────────────────────────────────

@pytest.fixture
def worked_example_inputs():
    """The exact worked example from 13-RESEARCH.md §4."""
    vector_hits = [
        {"chunk_id": "A", "content": "doc A", "metadata": {}, "similarity": 0.82},
        {"chunk_id": "B", "content": "doc B", "metadata": {}, "similarity": 0.79},
        {"chunk_id": "C", "content": "doc C", "metadata": {}, "similarity": 0.71},
        {"chunk_id": "D", "content": "doc D", "metadata": {}, "similarity": 0.68},
    ]
    keyword_hits = [
        {"chunk_id": "C", "content": "doc C", "metadata": {}, "ts_rank_cd": 0.087},
        {"chunk_id": "E", "content": "doc E", "metadata": {}, "ts_rank_cd": 0.061},
        {"chunk_id": "A", "content": "doc A", "metadata": {}, "ts_rank_cd": 0.044},
        {"chunk_id": "F", "content": "doc F", "metadata": {}, "ts_rank_cd": 0.022},
    ]
    return vector_hits, keyword_hits


def test_rrf_worked_example_sort_order_and_scores(worked_example_inputs):
    """RESEARCH §4 expected fused output: A, C, B, E, D, F."""
    vec, kw = worked_example_inputs
    fused = rrf_fuse(vec, kw, k=60, limit=30)

    assert [h["chunk_id"] for h in fused] == ["A", "C", "B", "E", "D", "F"]

    # Fused scores (k=60).
    expected = {
        "A": 1 / 61 + 1 / 63,   # ≈ 0.03227
        "C": 1 / 63 + 1 / 61,   # ≈ 0.03227
        "B": 1 / 62,            # ≈ 0.01613
        "E": 1 / 62,            # ≈ 0.01613
        "D": 1 / 64,            # ≈ 0.01563
        "F": 1 / 64,            # ≈ 0.01563
    }
    for h in fused:
        assert h["fused_score"] == pytest.approx(expected[h["chunk_id"]], abs=1e-4)


def test_rrf_tie_break_prefers_vector_over_keyword_only(worked_example_inputs):
    """At equal fused_score (B=E and D=F), the entry with higher similarity wins.
    Keyword-only entries get similarity=0.0 so vector entries win all ties."""
    vec, kw = worked_example_inputs
    fused = rrf_fuse(vec, kw, k=60, limit=30)

    # B (sim=0.79) must come before E (keyword-only, sim defaulted to 0.0)
    ids = [h["chunk_id"] for h in fused]
    assert ids.index("B") < ids.index("E")
    # D (sim=0.68) must come before F (keyword-only, sim=0.0)
    assert ids.index("D") < ids.index("F")

    # Keyword-only entries must have similarity=0.0
    by_id = {h["chunk_id"]: h for h in fused}
    assert by_id["E"]["similarity"] == 0.0
    assert by_id["F"]["similarity"] == 0.0
    # Vector-side similarities preserved
    assert by_id["A"]["similarity"] == 0.82
    assert by_id["B"]["similarity"] == 0.79


def test_rrf_both_sides_stamped_with_ranks(worked_example_inputs):
    """A appears in both lists → both vector_rank and keyword_rank set."""
    vec, kw = worked_example_inputs
    fused = rrf_fuse(vec, kw, k=60, limit=30)
    by_id = {h["chunk_id"]: h for h in fused}

    assert by_id["A"]["vector_rank"] == 1
    assert by_id["A"]["keyword_rank"] == 3
    assert by_id["C"]["vector_rank"] == 3
    assert by_id["C"]["keyword_rank"] == 1
    # Vector-only B has no keyword_rank key
    assert "vector_rank" in by_id["B"]
    assert "keyword_rank" not in by_id["B"]
    # Keyword-only E has no vector_rank key
    assert "keyword_rank" in by_id["E"]
    assert "vector_rank" not in by_id["E"]


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_rrf_empty_both_returns_empty():
    assert rrf_fuse([], []) == []


def test_rrf_only_vector_returns_vector_list():
    vec = [
        {"chunk_id": "X", "content": "x", "metadata": {}, "similarity": 0.9},
        {"chunk_id": "Y", "content": "y", "metadata": {}, "similarity": 0.6},
    ]
    fused = rrf_fuse(vec, [], k=60, limit=30)
    assert len(fused) == 2
    assert fused[0]["chunk_id"] == "X"
    assert fused[0]["vector_rank"] == 1
    assert fused[0]["fused_score"] == pytest.approx(1 / 61, abs=1e-6)
    assert fused[1]["vector_rank"] == 2
    assert fused[1]["fused_score"] == pytest.approx(1 / 62, abs=1e-6)
    # Both stay vector-only (no keyword_rank)
    assert "keyword_rank" not in fused[0]
    assert "keyword_rank" not in fused[1]


def test_rrf_only_keyword_defaults_similarity_zero():
    kw = [
        {"chunk_id": "P", "content": "p", "metadata": {}, "ts_rank_cd": 0.05},
        {"chunk_id": "Q", "content": "q", "metadata": {}, "ts_rank_cd": 0.02},
    ]
    fused = rrf_fuse([], kw, k=60, limit=30)
    assert len(fused) == 2
    # Keyword-only -> similarity defaulted to 0.0
    for h in fused:
        assert h["similarity"] == 0.0
        assert "keyword_rank" in h
        assert "vector_rank" not in h
    assert fused[0]["chunk_id"] == "P"
    assert fused[1]["chunk_id"] == "Q"


def test_rrf_limit_caps_output(worked_example_inputs):
    vec, kw = worked_example_inputs
    fused = rrf_fuse(vec, kw, k=60, limit=2)
    assert len(fused) == 2
    assert [h["chunk_id"] for h in fused] == ["A", "C"]


def test_rrf_dedup_by_chunk_id_not_content():
    """If chunk_id collides but content differs, first-seen entry wins."""
    vec = [{"chunk_id": "Z", "content": "vector content", "metadata": {}, "similarity": 0.5}]
    kw = [{"chunk_id": "Z", "content": "keyword content!", "metadata": {}, "ts_rank_cd": 0.1}]
    fused = rrf_fuse(vec, kw, k=60, limit=30)
    assert len(fused) == 1
    # Vector seen first -> its content wins.
    assert fused[0]["content"] == "vector content"
    # Both ranks present -> the same chunk_id was matched on both sides.
    assert fused[0]["vector_rank"] == 1
    assert fused[0]["keyword_rank"] == 1
    # Fused score = both contributions
    assert fused[0]["fused_score"] == pytest.approx(2.0 / 61, abs=1e-6)


# ── hybrid_enabled() env truthy/falsy ─────────────────────────────────────────

def test_hybrid_enabled_default_true(monkeypatch):
    monkeypatch.delenv("HYBRID_ENABLED", raising=False)
    assert hybrid_enabled() is True


@pytest.mark.parametrize("val", ["1", "true", "TRUE", "yes", "YES", "on", "On"])
def test_hybrid_enabled_truthy_values(monkeypatch, val):
    monkeypatch.setenv("HYBRID_ENABLED", val)
    assert hybrid_enabled() is True


@pytest.mark.parametrize("val", ["0", "false", "FALSE", "no", "NO", "off", "Off", "anything-else"])
def test_hybrid_enabled_falsy_values(monkeypatch, val):
    monkeypatch.setenv("HYBRID_ENABLED", val)
    assert hybrid_enabled() is False

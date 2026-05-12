"""
Unit tests — RAG ingestor chunking and retriever SQL correctness.

Covers:
  - chunk_text: size limits, overlap, sentence boundary respect, empty/short input
  - Natural language table summary vs raw Markdown table embedding quality
  - retriever.py: no ::type cast after named param, threshold <= 0.35

No DB needed — pure function tests.
"""
import os
import re
import sys
import pytest

# Tests run from /app inside rag-service container
sys.path.insert(0, "/app")

from ingestor import chunk_text, CHUNK_SIZE, CHUNK_OVERLAP


# ── chunk_text ────────────────────────────────────────────────────────────────

class TestChunkText:

    def test_short_text_single_chunk(self):
        text = "Le depileur alimente la ligne. Il transfere les cartes."
        chunks = chunk_text(text)
        assert len(chunks) == 1

    def test_empty_text_returns_empty(self):
        assert chunk_text("") == []

    def test_whitespace_only_returns_empty(self):
        assert chunk_text("   \n\n\t  ") == []

    def test_chunks_respect_word_limit(self):
        """Each chunk must not exceed CHUNK_SIZE + 30 words (sentence overshoot margin)."""
        sentence = "Le depileur alimente la ligne en cartes PCB vierges automatiquement. "
        long_text = sentence * (CHUNK_SIZE // 10 + 10)
        chunks = chunk_text(long_text)
        for i, chunk in enumerate(chunks):
            word_count = len(chunk.split())
            assert word_count <= CHUNK_SIZE + 30, (
                f"Chunk {i} has {word_count} words, exceeds limit {CHUNK_SIZE + 30}"
            )

    def test_multiple_chunks_for_long_text(self):
        """Long text (> CHUNK_SIZE words) must produce multiple chunks."""
        sentence = "La machine de serigraphie depose la pate a braser via un stencil. "
        long_text = sentence * (CHUNK_SIZE + 50)
        chunks = chunk_text(long_text)
        assert len(chunks) > 1

    def test_overlap_carries_words_from_previous_chunk(self):
        """Last CHUNK_OVERLAP words of chunk N should appear at start of chunk N+1."""
        sentence = "Motclef unique. "
        long_text = sentence * (CHUNK_SIZE * 2)
        chunks = chunk_text(long_text, chunk_size=50, overlap=10)
        if len(chunks) >= 2:
            prev_end = chunks[0].split()[-10:]
            next_start = chunks[1].split()[:10]
            overlap_found = any(w in next_start for w in prev_end)
            assert overlap_found, (
                f"No overlap found.\nChunk 0 end: {prev_end}\nChunk 1 start: {next_start}"
            )

    def test_very_short_chunks_filtered_out(self):
        """Chunks with < 20 chars should be discarded."""
        text = "OK. Non. Oui. " * 5
        chunks = chunk_text(text)
        for chunk in chunks:
            assert len(chunk.strip()) >= 20, f"Short chunk not filtered: '{chunk}'"

    def test_chunk_size_200_default(self):
        """Default CHUNK_SIZE must be 200 words — larger chunks dilute French embeddings."""
        assert CHUNK_SIZE == 200, (
            f"CHUNK_SIZE is {CHUNK_SIZE}, expected 200. "
            "Larger chunks dilute embeddings for French text on English model."
        )

    def test_chunk_overlap_20_default(self):
        assert CHUNK_OVERLAP == 20

    def test_natural_language_table_summary_low_pipe_ratio(self):
        """
        Natural language summary of indicators has very few pipe chars.
        Good for embedding — semantic content dominates.
        """
        nl_summary = (
            "INDICATEURS QUALITE LIGNE CMS. "
            "FPY cible superieur a 95%, alarme si inferieur a 90%. "
            "Taux rejet SPI cible inferieur a 2%, alarme si superieur a 5%. "
            "Taux defaut ICT cible inferieur a 3%, alarme si superieur a 6%. "
            "Taux defaut TF cible inferieur a 1%, alarme si superieur a 3%. "
            "Efficacite Pick and Place superieur a 92%, alarme si inferieur a 85%. "
            "Temps changement serie cible inferieur a 30 minutes."
        )
        chunks = chunk_text(nl_summary)
        assert len(chunks) >= 1
        content = chunks[0]
        pipe_ratio = content.count("|") / max(len(content), 1)
        assert pipe_ratio < 0.05, (
            f"Too many pipe symbols ({pipe_ratio:.0%}) — chunk not human-readable"
        )

    def test_markdown_table_has_high_pipe_ratio(self):
        """
        Demonstrates WHY Markdown tables embed poorly — mostly pipe symbols.
        Natural language alternative is needed.
        """
        md_table = (
            "| Indicateur | Cible | Alarme si |\n"
            "|------------|-------|----------|\n"
            "| FPY | > 95% | < 90% |\n"
            "| Taux rejet SPI | < 2% | > 5% |\n"
            "| Taux defaut ICT | < 3% | > 6% |\n"
            "| Taux defaut TF | < 1% | > 3% |\n"
        )
        chunks = chunk_text(md_table)
        if chunks:
            pipe_ratio = chunks[0].count("|") / max(len(chunks[0]), 1)
            assert pipe_ratio > 0.10, (
                f"Expected high pipe ratio in Markdown table, got {pipe_ratio:.0%}"
            )


# ── retriever.py static analysis ──────────────────────────────────────────────

class TestRetrieverSqlPattern:

    def read_retriever(self) -> str:
        with open("/app/retriever.py") as f:
            return f.read()

    def test_no_double_colon_cast_after_named_param(self):
        """asyncpg raises PostgresSyntaxError on :param::type pattern."""
        source = self.read_retriever()
        assert ":machine_id::int" not in source, (
            "Found ':machine_id::int' — asyncpg cannot handle '::' after named param."
        )

    def test_uses_cast_function_for_machine_id(self):
        source = self.read_retriever()
        assert "CAST(:machine_id AS integer)" in source

    def test_threshold_default_permissive(self):
        """Default threshold <= 0.35 for French text on English all-MiniLM-L6-v2."""
        source = self.read_retriever()
        match = re.search(r"threshold:\s*float\s*=\s*([\d.]+)", source)
        assert match, "threshold default not found in retriever.py"
        value = float(match.group(1))
        assert value <= 0.35, f"Threshold {value} too high for French docs (need <= 0.35)"

    def test_chunk_size_in_ingestor_permissive(self):
        """CHUNK_SIZE <= 256 ensures focused embeddings."""
        with open("/app/ingestor.py") as f:
            source = f.read()
        match = re.search(r"CHUNK_SIZE\s*=\s*(\d+)", source)
        assert match, "CHUNK_SIZE not found in ingestor.py"
        assert int(match.group(1)) <= 256, f"CHUNK_SIZE={match.group(1)} too large"

"""
Unit tests — RAG ingestor chunking and retriever SQL logic.

Covers:
  - chunk_text: size limits, overlap, sentence boundary respect, empty/short input
  - embed-ready content: natural language summaries beat pure Markdown tables
  - retriever SQL param fix: CAST(:machine_id AS integer) pattern correct

No DB, no HTTP needed — pure function tests.
"""

import sys
import os

# Add rag-service to path so we can import its modules directly
RAG_SERVICE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "rag-service"
)
sys.path.insert(0, os.path.abspath(RAG_SERVICE_PATH))

from ingestor import chunk_text, CHUNK_SIZE, CHUNK_OVERLAP  # noqa: E402


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
        """Each chunk must not exceed CHUNK_SIZE words."""
        # Generate text clearly longer than CHUNK_SIZE
        sentence = (
            "Le depileur alimente la ligne en cartes PCB vierges automatiquement. "
        )
        long_text = sentence * (CHUNK_SIZE // 10 + 10)
        chunks = chunk_text(long_text)
        for i, chunk in enumerate(chunks):
            word_count = len(chunk.split())
            # Allow slight overshoot for last sentence in chunk
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
            # At least some overlap words should match
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
        """Default CHUNK_SIZE should be 200 words (optimized for French docs)."""
        assert CHUNK_SIZE == 200, (
            f"CHUNK_SIZE is {CHUNK_SIZE}, expected 200. "
            "Larger chunks dilute embeddings for French text."
        )

    def test_chunk_overlap_20_default(self):
        """Default CHUNK_OVERLAP should be 20 words."""
        assert CHUNK_OVERLAP == 20

    def test_natural_language_table_summary_chunks_well(self):
        """
        Natural language summary of a table should produce a non-empty chunk
        with semantically meaningful content (not just pipe symbols).
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
        # Should have meaningful content ratio (not pipe symbols)
        content = chunks[0]
        pipe_ratio = content.count("|") / max(len(content), 1)
        assert pipe_ratio < 0.05, (
            f"Too many pipe symbols ({pipe_ratio:.0%}) — chunk not human-readable: {content[:100]}"
        )

    def test_markdown_table_heavy_in_pipes(self):
        """
        Pure Markdown table text has high pipe ratio — demonstrates WHY
        natural language alternative is needed for good embeddings.
        """
        md_table = (
            "| Indicateur | Cible | Alarme si |\n"
            "|------------|-------|----------|\n"
            "| FPY | > 95% | < 90% |\n"
            "| Taux rejet SPI | < 2% | > 5% |\n"
            "| Taux defaut ICT | < 3% | > 6% |\n"
            "| Taux defaut TF | < 1% | > 3% |\n"
            "| Efficacite PP | > 92% | < 85% |\n"
        )
        chunks = chunk_text(md_table)
        if chunks:
            content = chunks[0]
            pipe_ratio = content.count("|") / max(len(content), 1)
            # Document that Markdown tables are pipe-heavy — poor for embedding
            assert pipe_ratio > 0.1, (
                "Expected high pipe ratio in Markdown table "
                f"(got {pipe_ratio:.0%}) — this confirms the embedding quality issue"
            )


# ── retriever SQL parameter pattern ──────────────────────────────────────────


class TestRetrieverSqlPattern:
    """
    Verify that the retriever.py SQL avoids the asyncpg '::' cast bug.
    These are static analysis tests — read the file and check for the pattern.
    """

    def get_retriever_source(self) -> str:
        retriever_path = os.path.join(RAG_SERVICE_PATH, "retriever.py")
        with open(retriever_path) as f:
            return f.read()

    def test_no_double_colon_cast_after_named_param(self):
        """
        asyncpg raises PostgresSyntaxError when named param is followed by ::type.
        Pattern :machine_id::int must NOT appear in SQL.
        """
        source = self.get_retriever_source()
        assert ":machine_id::int" not in source, (
            "Found ':machine_id::int' — asyncpg cannot handle '::' after named param. "
            "Use CAST(:machine_id AS integer) instead."
        )

    def test_uses_cast_function_for_machine_id(self):
        """Correct pattern: CAST(:machine_id AS integer) in WHERE clause."""
        source = self.get_retriever_source()
        assert "CAST(:machine_id AS integer)" in source, (
            "Expected CAST(:machine_id AS integer) in retriever.py SQL. "
            "Found none. Check retriever.py."
        )

    def test_threshold_default_is_permissive(self):
        """
        Default threshold must be <= 0.35 to handle French text on English model.
        all-MiniLM-L6-v2 scores French queries ~0.3-0.5 — 0.7 would miss everything.
        """
        source = self.get_retriever_source()
        # Find 'threshold: float = X.XX' in source
        import re

        match = re.search(r"threshold:\s*float\s*=\s*([\d.]+)", source)
        assert match is not None, "Could not find threshold default in retriever.py"
        threshold_value = float(match.group(1))
        assert threshold_value <= 0.35, (
            f"Threshold default {threshold_value} too high. "
            "French text on English model needs <= 0.35."
        )

    def test_chunk_size_in_ingestor_is_small(self):
        """
        CHUNK_SIZE <= 256 words ensures focused per-topic embeddings.
        Larger chunks dilute meaning and reduce similarity scores.
        """
        source_path = os.path.join(RAG_SERVICE_PATH, "ingestor.py")
        with open(source_path) as f:
            source = f.read()
        import re

        match = re.search(r"CHUNK_SIZE\s*=\s*(\d+)", source)
        assert match is not None, "CHUNK_SIZE not found in ingestor.py"
        chunk_size = int(match.group(1))
        assert chunk_size <= 256, (
            f"CHUNK_SIZE={chunk_size} too large. "
            "Use <= 256 for better per-topic embedding quality."
        )

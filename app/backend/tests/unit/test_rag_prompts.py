"""
Unit tests — RAG prompt injection and priority behavior.

Covers:
  - build_rag_context: structure, priority instruction present, content truncation
  - build_full_system_prompt: RAG section appended when chunks provided
  - RAG context injection as conversation turn (tool-override guard)

No DB or HTTP needed — pure function tests.
"""

from services.ai_prompts import build_rag_context, build_full_system_prompt


# ── Helpers ───────────────────────────────────────────────────────────────────


def make_chunk(
    content: str,
    filename: str = "guide_cms.txt",
    similarity: float = 0.45,
    page: int = 1,
) -> dict:
    return {
        "content": content,
        "metadata": {"filename": filename, "page": page, "doc_type": "manual"},
        "similarity": similarity,
    }


INDICATEURS_CHUNK = make_chunk(
    content=(
        "INDICATEURS QUALITE LIGNE CMS. "
        "FPY cible superieur a 95%, alarme si inferieur a 90%. "
        "Taux rejet SPI cible inferieur a 2%, alarme si superieur a 5%. "
        "Taux defaut ICT cible inferieur a 3%, alarme si superieur a 6%. "
        "Taux defaut TF cible inferieur a 1%, alarme si superieur a 3%. "
        "Efficacite PP cible superieur a 92%, alarme si inferieur a 85%."
    ),
    similarity=0.52,
)

DEPILEUR_CHUNK = make_chunk(
    content=(
        "Alarme D-02 Bourrage carte (Card Jam). "
        "CAUSE: PCB mal alignee, gauchissement excessif. "
        "ACTION: 1. Appuyer sur ARRET D'URGENCE. "
        "2. Ouvrir le capot de protection lateral. "
        "3. Retirer la carte coincee MANUELLEMENT."
    ),
    similarity=0.38,
)


# ── build_rag_context ─────────────────────────────────────────────────────────


class TestBuildRagContext:
    def test_empty_chunks_returns_empty_string(self):
        assert build_rag_context([]) == ""

    def test_none_chunks_returns_empty_string(self):
        # Should handle None gracefully (caller may pass None)
        assert build_rag_context(None) == ""

    def test_contains_contexte_documentaire_header(self):
        result = build_rag_context([INDICATEURS_CHUNK])
        assert "[CONTEXTE DOCUMENTAIRE]" in result

    def test_contains_fin_contexte_documentaire(self):
        result = build_rag_context([INDICATEURS_CHUNK])
        assert "[FIN CONTEXTE DOCUMENTAIRE]" in result

    def test_priority_instruction_present(self):
        """Critical: LLM must be told to use docs before calling tools."""
        result = build_rag_context([INDICATEURS_CHUNK])
        # Should contain some form of instruction to prioritize doc context
        assert any(
            keyword in result.lower()
            for keyword in [
                "priorit",
                "sans appeler",
                "n'utilise pas",
                "reponds directement",
            ]
        ), f"No priority instruction found in:\n{result}"

    def test_chunk_content_included(self):
        result = build_rag_context([INDICATEURS_CHUNK])
        assert "FPY" in result or "INDICATEURS" in result

    def test_source_filename_included(self):
        result = build_rag_context([INDICATEURS_CHUNK])
        assert "guide_cms.txt" in result

    def test_similarity_displayed_as_percentage(self):
        result = build_rag_context([INDICATEURS_CHUNK])
        assert "52%" in result  # 0.52 → 52%

    def test_multiple_chunks_all_included(self):
        result = build_rag_context([INDICATEURS_CHUNK, DEPILEUR_CHUNK])
        assert "FPY" in result or "INDICATEURS" in result
        assert "Bourrage" in result or "D-02" in result

    def test_content_truncated_at_1500_chars(self):
        # Use 'z' — does not appear in any instruction string, so count is exact
        long_chunk = make_chunk(content="z" * 3000)
        result = build_rag_context([long_chunk])
        z_count = result.count("z")
        assert z_count <= 1500, f"Content not truncated: {z_count} 'z' chars in output"

    def test_page_number_shown_when_present(self):
        result = build_rag_context([INDICATEURS_CHUNK])  # page=1
        assert "page 1" in result

    def test_no_page_number_when_none(self):
        chunk = make_chunk(content="test content", page=None)
        chunk["metadata"].pop("page", None)
        result = build_rag_context([chunk])
        # Should not crash and should not show "page None"
        assert "page None" not in result


# ── build_full_system_prompt with RAG ─────────────────────────────────────────


class TestBuildFullSystemPromptWithRag:
    def test_no_rag_chunks_no_contexte_section(self):
        prompt = build_full_system_prompt("ADMIN", "hamza", rag_chunks=None)
        assert "[CONTEXTE DOCUMENTAIRE]" not in prompt

    def test_empty_rag_chunks_no_contexte_section(self):
        prompt = build_full_system_prompt("ADMIN", "hamza", rag_chunks=[])
        assert "[CONTEXTE DOCUMENTAIRE]" not in prompt

    def test_rag_chunks_injects_contexte_section(self):
        prompt = build_full_system_prompt(
            "ADMIN", "hamza", rag_chunks=[INDICATEURS_CHUNK]
        )
        assert "[CONTEXTE DOCUMENTAIRE]" in prompt

    def test_rag_section_appended_after_role_prompt(self):
        prompt = build_full_system_prompt(
            "CHEFTECH", "hamza", rag_chunks=[DEPILEUR_CHUNK]
        )
        contexte_pos = prompt.index("[CONTEXTE DOCUMENTAIRE]")
        # Role-based content should come before RAG context
        assert contexte_pos > 0, "RAG context appeared before role prompt"

    def test_all_roles_accept_rag_chunks(self):
        for role in ["ADMIN", "CHEFTECH", "CHETOP", "TECHNICIEN"]:
            prompt = build_full_system_prompt(
                role, "user", rag_chunks=[INDICATEURS_CHUNK]
            )
            assert "[CONTEXTE DOCUMENTAIRE]" in prompt, f"RAG missing for role {role}"

    def test_multiple_chunks_all_in_prompt(self):
        prompt = build_full_system_prompt(
            "ADMIN", "hamza", rag_chunks=[INDICATEURS_CHUNK, DEPILEUR_CHUNK]
        )
        # Both source filenames should be in the prompt
        assert prompt.count("guide_cms.txt") >= 2

    def test_rag_chunks_with_memories(self):
        """RAG + memories both present — no crash, both injected."""
        from types import SimpleNamespace

        # Matches actual AIMemory ORM fields: memory_key, memory_value, memory_type
        fake_memory = SimpleNamespace(
            memory_key="procedure_depileur",
            memory_value="Appuyer sur ARRET avant ouverture capot",
            memory_type="strategy",
        )
        prompt = build_full_system_prompt(
            "TECHNICIEN",
            "ali",
            memories=[fake_memory],
            rag_chunks=[DEPILEUR_CHUNK],
        )
        assert "[CONTEXTE DOCUMENTAIRE]" in prompt
        assert "[MEMOIRE UTILISATEUR]" in prompt


# ── RAG priority over tool-calling ───────────────────────────────────────────


class TestRagPriorityInstruction:
    """
    Verify that when RAG context is present, the system prompt
    contains explicit instructions NOT to use tools.
    These tests define the expected behavior that fixes the tool-override bug.
    """

    def test_priority_instruction_forbids_tool_use(self):
        """
        The instruction must clearly tell the LLM to skip tool calls
        when documentation context is available.
        """
        result = build_rag_context([INDICATEURS_CHUNK])
        # Must contain at least one of these directives
        directives = [
            "n'utilise pas",
            "sans appeler",
            "ne pas appeler",
            "reponds directement",
            "pas d'outil",
        ]
        found = any(d in result.lower() for d in directives)
        assert found, (
            f"No tool-override instruction found. Directives checked: {directives}\n"
            f"Context output:\n{result}"
        )

    def test_cite_source_instruction_present(self):
        """LLM should be told to cite the document filename in its response."""
        result = build_rag_context([INDICATEURS_CHUNK])
        assert (
            "source" in result.lower()
            or "cite" in result.lower()
            or "fichier" in result.lower()
        )

    def test_instruction_critique_label_present(self):
        """The 'INSTRUCTION CRITIQUE' label makes priority unambiguous to LLM."""
        result = build_rag_context([INDICATEURS_CHUNK])
        assert (
            "INSTRUCTION" in result
            or "CRITIQUE" in result
            or "PRIORIT" in result.upper()
        )

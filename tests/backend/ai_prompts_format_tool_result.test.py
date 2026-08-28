"""Unit tests for format_tool_result() in app/backend/services/ai_prompts.py.

Covers the token-bloat fix: a tool result with many rows or long free-text
fields (e.g. a multi-paragraph problem_description) must not be dumped
verbatim into the LLM-facing message, or composite queries risk blowing
Groq's tokens-per-minute limit.
"""
from services.ai_prompts import format_tool_result


def test_empty_result_says_no_data_found():
    assert "Aucun resultat" in format_tool_result("get_machines", [])


def test_error_result_is_passed_through():
    result = format_tool_result("get_machines", {"error": "boom"})
    assert "Erreur" in result and "boom" in result


def test_small_result_is_not_truncated():
    rows = [{"id": 1, "nom": "Machine A"}]
    result = format_tool_result("search_machines", rows)
    assert "1 resultat" in result
    assert "Machine A" in result
    assert "autres" not in result


def test_row_count_is_capped_at_max_items():
    rows = [{"id": i} for i in range(57)]
    result = format_tool_result("get_interventions", rows)
    assert "57 resultat" in result
    assert "(... et 47 autres)" in result
    # Only the first max_items rows should actually appear in the payload.
    assert '"id": 10' not in result
    assert '"id": 9' in result


def test_long_string_field_is_truncated():
    long_description = "A" * 500
    rows = [{"id": 320, "problem_description": long_description}]
    result = format_tool_result("get_interventions", rows)
    assert long_description not in result
    assert "A" * 150 + "…" in result


def test_short_string_field_is_untouched():
    rows = [{"id": 1, "problem_description": "short text"}]
    result = format_tool_result("get_interventions", rows)
    assert "short text" in result

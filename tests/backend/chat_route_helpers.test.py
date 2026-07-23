"""Unit tests for the ai_chat() helper functions in
app/backend/modules/shared/routes/chat.py."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

import modules.shared.routes.chat as chat_mod
from modules.shared.routes.chat import (
    _execute_tools,
    _fetch_rag_chunks,
    _inject_ml_context,
    _inject_rag_context,
    _load_db_history,
    _load_ranked_memories,
    _record_memory_feedback,
    _resolve_chat_session,
    _run_tool_call,
)


# ── _resolve_chat_session ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_resolve_chat_session_creates_new_when_no_session_id():
    session_svc = SimpleNamespace(get_or_create=AsyncMock(return_value="new-session"))
    request = SimpleNamespace(session_id=None)
    result = await _resolve_chat_session(request, SimpleNamespace(id=1), session_svc)
    assert result == "new-session"
    session_svc.get_or_create.assert_awaited_once_with(1)


@pytest.mark.asyncio
async def test_resolve_chat_session_invalid_uuid_raises_400():
    session_svc = SimpleNamespace()
    request = SimpleNamespace(session_id="not-a-uuid")
    with pytest.raises(HTTPException) as exc_info:
        await _resolve_chat_session(request, SimpleNamespace(id=1), session_svc)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_resolve_chat_session_not_found_raises_404():
    session_svc = SimpleNamespace(get_by_id=AsyncMock(return_value=None))
    request = SimpleNamespace(session_id="12345678-1234-5678-1234-567812345678")
    with pytest.raises(HTTPException) as exc_info:
        await _resolve_chat_session(request, SimpleNamespace(id=1), session_svc)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_resolve_chat_session_found_returns_it():
    session_svc = SimpleNamespace(get_by_id=AsyncMock(return_value="existing-session"))
    request = SimpleNamespace(session_id="12345678-1234-5678-1234-567812345678")
    result = await _resolve_chat_session(request, SimpleNamespace(id=1), session_svc)
    assert result == "existing-session"


# ── _load_ranked_memories ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_load_ranked_memories_sorts_by_success_count_desc():
    mems = [SimpleNamespace(success_count=1), SimpleNamespace(success_count=5)]
    memory_svc = SimpleNamespace(get_by_user=AsyncMock(return_value=mems))
    result = await _load_ranked_memories(memory_svc, user_id=1)
    assert [m.success_count for m in result] == [5, 1]


@pytest.mark.asyncio
async def test_load_ranked_memories_caps_at_15():
    mems = [SimpleNamespace(success_count=i) for i in range(20)]
    memory_svc = SimpleNamespace(get_by_user=AsyncMock(return_value=mems))
    result = await _load_ranked_memories(memory_svc, user_id=1)
    assert len(result) == 15


@pytest.mark.asyncio
async def test_load_ranked_memories_returns_empty_on_error():
    memory_svc = SimpleNamespace(get_by_user=AsyncMock(side_effect=RuntimeError("boom")))
    result = await _load_ranked_memories(memory_svc, user_id=1)
    assert result == []


# ── _fetch_rag_chunks ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_rag_chunks_success(monkeypatch):
    monkeypatch.setattr(chat_mod.rag_client, "retrieve_chunks", AsyncMock(return_value=["chunk1"]))
    result = await _fetch_rag_chunks("query", machine_id=1)
    assert result == ["chunk1"]


@pytest.mark.asyncio
async def test_fetch_rag_chunks_returns_empty_on_error(monkeypatch):
    monkeypatch.setattr(chat_mod.rag_client, "retrieve_chunks", AsyncMock(side_effect=RuntimeError("boom")))
    result = await _fetch_rag_chunks("query", machine_id=1)
    assert result == []


# ── _load_db_history ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_load_db_history_success():
    session_svc = SimpleNamespace(get_history_by_session=AsyncMock(return_value=["msg1"]))
    result = await _load_db_history(session_svc, SimpleNamespace(id=1), user_id=1)
    assert result == ["msg1"]


@pytest.mark.asyncio
async def test_load_db_history_returns_empty_on_error():
    session_svc = SimpleNamespace(get_history_by_session=AsyncMock(side_effect=RuntimeError("boom")))
    result = await _load_db_history(session_svc, SimpleNamespace(id=1), user_id=1)
    assert result == []


# ── _inject_rag_context ───────────────────────────────────────────────────────

def test_inject_rag_context_noop_when_no_chunks():
    messages = []
    _inject_rag_context(messages, [])
    assert messages == []


def test_inject_rag_context_appends_two_turns(monkeypatch):
    monkeypatch.setattr(chat_mod, "build_rag_context", lambda chunks: "rag-text")
    messages = []
    _inject_rag_context(messages, ["chunk"])
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert "rag-text" in messages[0]["content"]
    assert messages[1]["role"] == "assistant"


# ── _inject_ml_context ────────────────────────────────────────────────────────

def test_inject_ml_context_false_when_snapshot_none():
    messages = []
    assert _inject_ml_context(messages, None) is False
    assert messages == []


def test_inject_ml_context_false_when_text_empty(monkeypatch):
    monkeypatch.setattr(chat_mod, "build_ml_context", lambda snap: "")
    messages = []
    assert _inject_ml_context(messages, {"some": "snapshot"}) is False
    assert messages == []


def test_inject_ml_context_true_and_appends_turns(monkeypatch):
    monkeypatch.setattr(chat_mod, "build_ml_context", lambda snap: "ml-text")
    messages = []
    assert _inject_ml_context(messages, {"some": "snapshot"}) is True
    assert len(messages) == 2
    assert "ml-text" in messages[0]["content"]


# ── _run_tool_call ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_tool_call_success(monkeypatch):
    monkeypatch.setattr(chat_mod, "execute_tool", AsyncMock(return_value={"data": 1}))
    monkeypatch.setattr(chat_mod, "format_tool_result", lambda name, result: "formatted")
    tool_call = {"id": "tc1", "function": {"name": "get_machines", "arguments": "{}"}}
    messages = []
    source, success, failed = await _run_tool_call(tool_call, messages, db=None)
    assert success is True and failed is False
    assert source == {"tool": "get_machines", "result": {"data": 1}}
    assert len(messages) == 2


@pytest.mark.asyncio
async def test_run_tool_call_empty_result_is_failure(monkeypatch):
    monkeypatch.setattr(chat_mod, "execute_tool", AsyncMock(return_value=None))
    monkeypatch.setattr(chat_mod, "format_tool_result", lambda name, result: "formatted")
    tool_call = {"id": "tc1", "function": {"name": "get_machines", "arguments": "{}"}}
    _, success, failed = await _run_tool_call(tool_call, [], db=None)
    assert success is False and failed is True


@pytest.mark.asyncio
async def test_run_tool_call_exception_is_failure(monkeypatch):
    monkeypatch.setattr(chat_mod, "execute_tool", AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(chat_mod, "format_tool_result", lambda name, result: "formatted")
    tool_call = {"id": "tc1", "function": {"name": "get_machines", "arguments": "{}"}}
    source, success, failed = await _run_tool_call(tool_call, [], db=None)
    assert success is False and failed is True
    assert "error" in source["result"]


@pytest.mark.asyncio
async def test_run_tool_call_parses_dict_arguments(monkeypatch):
    monkeypatch.setattr(chat_mod, "execute_tool", AsyncMock(return_value={"ok": True}))
    monkeypatch.setattr(chat_mod, "format_tool_result", lambda name, result: "formatted")
    tool_call = {"id": "tc1", "function": {"name": "get_machines", "arguments": {"already": "dict"}}}
    _, success, _ = await _run_tool_call(tool_call, [], db=None)
    assert success is True


# ── _execute_tools ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_execute_tools_no_tool_calls_returns_initial_content():
    content, sources, success, failure = await _execute_tools([], [], db=None, groq=None, initial_content="hi")
    assert (content, sources, success, failure) == ("hi", None, False, False)


@pytest.mark.asyncio
async def test_execute_tools_runs_and_calls_groq_again(monkeypatch):
    monkeypatch.setattr(chat_mod, "execute_tool", AsyncMock(return_value={"data": 1}))
    monkeypatch.setattr(chat_mod, "format_tool_result", lambda name, result: "formatted")
    groq = SimpleNamespace(chat=lambda messages: {"choices": [{"message": {"content": "final answer"}}]})
    tool_calls = [{"id": "tc1", "function": {"name": "get_machines", "arguments": "{}"}}]
    content, sources, success, failure = await _execute_tools(tool_calls, [], db=None, groq=groq, initial_content="initial")
    assert content == "final answer"
    assert success is True and failure is False
    assert len(sources) == 1


@pytest.mark.asyncio
async def test_execute_tools_groq_failure_keeps_initial_content(monkeypatch):
    monkeypatch.setattr(chat_mod, "execute_tool", AsyncMock(return_value={"data": 1}))
    monkeypatch.setattr(chat_mod, "format_tool_result", lambda name, result: "formatted")

    def _boom(messages):
        raise RuntimeError("groq down")

    groq = SimpleNamespace(chat=_boom)
    tool_calls = [{"id": "tc1", "function": {"name": "get_machines", "arguments": "{}"}}]
    content, _, _, _ = await _execute_tools(tool_calls, [], db=None, groq=groq, initial_content="fallback")
    assert content == "fallback"


# ── _record_memory_feedback ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_record_memory_feedback_noop_without_memories_or_tool_calls():
    memory_svc = SimpleNamespace(increment_success=AsyncMock(), increment_failure=AsyncMock())
    await _record_memory_feedback([], memory_svc, [], True, False)
    memory_svc.increment_success.assert_not_awaited()


@pytest.mark.asyncio
async def test_record_memory_feedback_increments_success_for_strategy_memory():
    memory_svc = SimpleNamespace(increment_success=AsyncMock(), increment_failure=AsyncMock())
    memories = [SimpleNamespace(memory_type="strategy", id="m1")]
    await _record_memory_feedback(memories, memory_svc, tool_calls=["tc"], tool_success=True, tool_failure=False)
    memory_svc.increment_success.assert_awaited_once_with("m1")


@pytest.mark.asyncio
async def test_record_memory_feedback_increments_failure_for_failure_memory():
    memory_svc = SimpleNamespace(increment_success=AsyncMock(), increment_failure=AsyncMock())
    memories = [SimpleNamespace(memory_type="failure", id="m2")]
    await _record_memory_feedback(memories, memory_svc, tool_calls=["tc"], tool_success=False, tool_failure=True)
    memory_svc.increment_failure.assert_awaited_once_with("m2")


@pytest.mark.asyncio
async def test_record_memory_feedback_swallows_exceptions():
    memory_svc = SimpleNamespace(
        increment_success=AsyncMock(side_effect=RuntimeError("boom")),
        increment_failure=AsyncMock(),
    )
    memories = [SimpleNamespace(memory_type="strategy", id="m1")]
    await _record_memory_feedback(memories, memory_svc, tool_calls=["tc"], tool_success=True, tool_failure=False)
    # must not raise

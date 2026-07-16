import asyncio
import json
import logging
from typing import List, Any, Dict, Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs

from uuid import UUID

from schemas.ai_chat import (
    ChatRequest,
    ChatResponse,
    ChatSessionSummary,
    CreateSessionRequest,
    RenameSessionRequest,
)
from services.ai_tools import get_tool_definitions, execute_tool
from services.ai_prompts import (
    build_full_system_prompt,
    format_tool_result,
    build_rag_context,
    build_ml_context,
)
from modules.ml.services.chat_context import get_ml_snapshot
import services.rag_client as rag_client
from services.ai_memory import AIMemoryService
from services.chat_session_service import ChatSessionService
from services.ai_agents import run_eam_analysis
from core.groq_client import get_groq_client, groq_cache_stats, clear_groq_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

# Shared literals (deduplicated per sonar S1192)
_INVALID_SESSION_ID_MSG = "Invalid session_id"
_SESSION_NOT_FOUND_MSG = "Session not found"
_DEFAULT_SESSION_TITLE = "Nouvelle conversation"


# ---------------------------------------------------------------------------
# Suggestions — static per role, no external import needed
# ---------------------------------------------------------------------------

_SUGGESTIONS: Dict[str, List[str]] = {
    "ADMIN": [
        "Montre toutes les machines en panne",
        "Alertes critiques actives",
        "Ordres de travail en attente",
        "Reparations les plus couteuses",
        "Analyse complete de la Zone_Nord",
    ],
    "CHEFTECH": [
        "Machines necessitant maintenance urgente",
        "Interventions en cours",
        "Alertes haute priorite",
        "Planning de la semaine",
        "Analyse predictive par zone",
    ],
    "CHETOP": [
        "Ordres de travail en attente",
        "Machines en panne dans ma zone",
        "Planning production",
        "Demandes d'intervention ouvertes",
    ],
    "TECHNICIEN": [
        "Mes ordres de travail assignes",
        "Machines a inspecter aujourd'hui",
        "Alertes pour mes machines",
    ],
}

_DEFAULT_SUGGESTIONS = [
    "Montre les machines en panne",
    "Alertes actives",
    "Ordres de travail en cours",
]


@router.get("/suggestions", response_model=List[str])
async def get_suggestions(
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """Role-based query suggestions."""
    role = current_user.role.value if current_user.role else ""
    return _SUGGESTIONS.get(role, _DEFAULT_SUGGESTIONS)


# ---------------------------------------------------------------------------
# Cache debug — ADMIN only
# ---------------------------------------------------------------------------


@router.get("/cache-stats")
async def get_cache_stats(
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """Return Groq LLM response cache hit/miss counters."""
    return {"groq_cache": groq_cache_stats()}


@router.post("/cache-clear", status_code=204, responses={403: {"description": "ADMIN role required."}})
async def post_cache_clear(
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """Force clear Groq response cache."""
    if not current_user.role or current_user.role.value != "ADMIN":
        raise HTTPException(status_code=403, detail="ADMIN role required.")
    clear_groq_cache()
    return None


# ---------------------------------------------------------------------------
# History — DB-backed, survives restarts
# ---------------------------------------------------------------------------


@router.get("/history", responses={400: {"description": "Invalid session_id"}, 404: {"description": "Session not found"}})
async def get_history(
    *,
    limit: Annotated[int, Query(le=50)] = 20,
    session_id: Annotated[Optional[str], Query()] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """
    Chat history. If session_id is given, returns that session's messages
    (ownership-checked). If omitted, returns the user's most-recent session.
    """
    session_svc = ChatSessionService(db)
    if session_id:
        try:
            sid = UUID(session_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=_INVALID_SESSION_ID_MSG)
        session = await session_svc.get_by_id(sid, current_user.id)
        if session is None:
            raise HTTPException(status_code=404, detail=_SESSION_NOT_FOUND_MSG)
        messages = session.messages or []
        return {
            "history": messages[-limit:],
            "total": len(messages),
            "session_id": str(session.id),
            "title": session.title or _DEFAULT_SESSION_TITLE,
            "last_query": session.last_query,
        }
    info = await session_svc.get_session_info(current_user.id)
    messages = info["history"]
    return {
        "history": messages[-limit:],
        "total": info["total"],
        "session_id": info["session_id"],
        "title": info.get("title", _DEFAULT_SESSION_TITLE),
        "last_query": info["last_query"],
    }


@router.delete("/history")
async def clear_history(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """Clear messages on user's most-recent session (does NOT delete the row)."""
    session_svc = ChatSessionService(db)
    await session_svc.clear(current_user.id)
    return {"message": "Historique efface."}


# ---------------------------------------------------------------------------
# Multi-conversation sessions — sidebar CRUD
# ---------------------------------------------------------------------------


@router.get("/sessions", response_model=List[ChatSessionSummary])
async def list_sessions(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """List all chat sessions for the current user, newest first."""
    session_svc = ChatSessionService(db)
    summaries = await session_svc.list_for_user(current_user.id)
    return summaries


@router.post("/sessions", response_model=ChatSessionSummary, status_code=201)
async def create_session(
    *, payload: CreateSessionRequest = CreateSessionRequest(),
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """Create a new empty chat session."""
    session_svc = ChatSessionService(db)
    s = await session_svc.create(current_user.id, title=payload.title)
    return {
        "id": str(s.id),
        "title": s.title,
        "message_count": s.message_count or 0,
        "last_query": s.last_query,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


@router.delete("/sessions/{session_id}", status_code=204, responses={400: {"description": "Invalid session_id"}, 404: {"description": "Session not found"}})
async def delete_session(
    session_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """Delete a chat session (ownership-checked)."""
    try:
        sid = UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=_INVALID_SESSION_ID_MSG)
    session_svc = ChatSessionService(db)
    ok = await session_svc.delete(sid, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail=_SESSION_NOT_FOUND_MSG)
    return None


@router.patch("/sessions/{session_id}", response_model=ChatSessionSummary, responses={400: {"description": "Invalid session_id"}, 404: {"description": "Session not found"}})
async def rename_session(
    session_id: str,
    payload: RenameSessionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """Rename a chat session (ownership-checked)."""
    try:
        sid = UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=_INVALID_SESSION_ID_MSG)
    session_svc = ChatSessionService(db)
    s = await session_svc.rename(sid, current_user.id, payload.title)
    if s is None:
        raise HTTPException(status_code=404, detail=_SESSION_NOT_FOUND_MSG)
    return {
        "id": str(s.id),
        "title": s.title,
        "message_count": s.message_count or 0,
        "last_query": s.last_query,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


# ---------------------------------------------------------------------------
# AI chat — private helpers to keep ai_chat CC < 15
# ---------------------------------------------------------------------------


async def _resolve_chat_session(request, current_user, session_svc):
    """Resolve or create the target chat session."""
    if not request.session_id:
        return await session_svc.get_or_create(current_user.id)
    try:
        sid = UUID(request.session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=_INVALID_SESSION_ID_MSG)
    session = await session_svc.get_by_id(sid, current_user.id)
    if session is None:
        raise HTTPException(status_code=404, detail=_SESSION_NOT_FOUND_MSG)
    return session


async def _load_ranked_memories(memory_svc, user_id: int) -> list:
    """Load and rank user memories by success count. Returns [] on failure."""
    try:
        mems = await memory_svc.get_by_user(user_id)
        mems.sort(key=lambda m: m.success_count, reverse=True)
        return mems[:15]
    except Exception as e:
        logger.warning(f"Memory load failed, continuing without: {e}")
        return []


async def _fetch_rag_chunks(query: str, machine_id) -> list:
    """Retrieve RAG chunks, returning [] on any failure."""
    try:
        return await rag_client.retrieve_chunks(
            query=query, machine_id=machine_id, top_k=8, threshold=0.30,
        )
    except Exception as e:
        logger.warning(f"RAG retrieval failed, continuing without context: {e}")
        return []


async def _load_db_history(session_svc, session, user_id: int) -> list:
    """Load DB conversation history for a session, returning [] on failure."""
    try:
        return await session_svc.get_history_by_session(session.id, user_id, limit=20)
    except Exception as e:
        logger.warning(f"History load failed, continuing without: {e}")
        return []


def _inject_rag_context(messages: list, rag_chunks: list) -> None:
    """Append RAG doc context turns to messages if chunks are present."""
    if not rag_chunks:
        return
    rag_text = build_rag_context(rag_chunks)
    messages.append({
        "role": "user",
        "content": (
            f"[BASE DOCUMENTAIRE] Extraits pertinents de la documentation:\n{rag_text}\n\n"
            "Utilise ces extraits comme contexte. "
            "Si la question demande une liste exhaustive, un comptage, "
            "ou des donnees structurees (machines, ordres, alertes, pieces), "
            "appelle l'outil approprie pour obtenir la donnee complete depuis la base."
        ),
    })
    messages.append({
        "role": "assistant",
        "content": "Compris. J'utilise la documentation comme contexte et "
                   "j'appelle les outils quand la question necessite des donnees completes.",
    })


def _inject_ml_context(messages: list, ml_snapshot) -> bool:
    """Append live ML state turns if available. Returns True if injected."""
    if ml_snapshot is None:
        return False
    ml_text = build_ml_context(ml_snapshot)
    if not ml_text:
        return False
    messages.append({
        "role": "user",
        "content": (
            f"{ml_text}\n\n"
            "Ces donnees ML sont en temps reel pour la machine concernee. "
            "Combine cet etat actuel avec la documentation pour donner "
            "un diagnostic precis et actionnable. Mentionne les capteurs "
            "en ATTENTION ou CRITIQUE si pertinent."
        ),
    })
    messages.append({
        "role": "assistant",
        "content": "Compris. Je dispose de l'etat ML en temps reel de cette machine "
                   "et je l'integre dans mon analyse avec la documentation technique.",
    })
    return True


async def _run_tool_call(tool_call: dict, messages: list, db) -> tuple:
    """Execute one tool call, append result turns to messages. Returns (source, success, failed)."""
    func_name = tool_call["function"]["name"]
    func_args_raw = tool_call["function"]["arguments"]
    func_args = json.loads(func_args_raw) if isinstance(func_args_raw, str) else func_args_raw
    success = False
    failed = False
    try:
        result = await execute_tool(func_name, func_args, db)
        success = bool(result)
        if not result:
            failed = True
    except Exception as e:
        safe_name = str(func_name).replace("\r", "").replace("\n", "")
        logger.exception(f"Tool {safe_name} failed: {e}")
        result = {"error": str(e)}
        failed = True
    messages.append({"role": "assistant", "content": None, "tool_calls": [tool_call]})
    messages.append({"role": "tool", "tool_call_id": tool_call["id"],
                     "content": format_tool_result(func_name, result)})
    return {"tool": func_name, "result": result}, success, failed


async def _execute_tools(tool_calls: list, messages: list, db, groq, initial_content: str) -> tuple:
    """Run all tool calls, do second Groq call, return (content, sources, success, failure)."""
    if not tool_calls:
        return initial_content, None, False, False
    sources = []
    tool_success = False
    tool_failure = False
    for tc in tool_calls:
        src, ok, fail = await _run_tool_call(tc, messages, db)
        sources.append(src)
        tool_success = tool_success or ok
        tool_failure = tool_failure or fail
    try:
        final_resp = groq.chat(messages=messages)
        final_choices = final_resp.get("choices", [])
        if final_choices:
            initial_content = final_choices[0].get("message", {}).get("content", initial_content) or initial_content
    except Exception as e:
        logger.warning(f"Final Groq call failed: {e}")
        initial_content = initial_content or "J'ai execute les actions demandees."
    return initial_content, sources, tool_success, tool_failure


async def _record_memory_feedback(memories, memory_svc, tool_calls, tool_success, tool_failure):
    """Update memory success/failure counters after tool execution."""
    if not memories or not tool_calls:
        return
    try:
        if tool_success:
            top = next((m for m in memories if m.memory_type == "strategy"), None)
            if top:
                await memory_svc.increment_success(str(top.id))
        elif tool_failure:
            top = next((m for m in memories if m.memory_type == "failure"), None)
            if top:
                await memory_svc.increment_failure(str(top.id))
    except Exception as e:
        logger.warning(f"Memory feedback failed: {e}")


# ---------------------------------------------------------------------------
# AI chat — LLM + tool calling + memory + DB history
# ---------------------------------------------------------------------------


@router.post("/ai/chat", response_model=ChatResponse, responses={400: {"description": "Invalid session_id"}, 404: {"description": "Session not found"}, 500: {"description": "No response from AI"}, 503: {"description": "Service Unavailable"}})
async def ai_chat(
    request: ChatRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """
    AI-powered chat using Groq LLM with role-based system prompt, memory, RAG, tool calling.
    """
    role_name = current_user.role.value if current_user.role else "TECHNICIEN"
    user_name = current_user.nom or "User"
    machine_id = getattr(request, "machine_id", None)

    memory_svc = AIMemoryService(db)
    session_svc = ChatSessionService(db)

    target_session = await _resolve_chat_session(request, current_user, session_svc)
    memories = await _load_ranked_memories(memory_svc, current_user.id)

    # RAG + ML snapshot (parallel when machine_id present)
    if machine_id is not None:
        rag_chunks, ml_snapshot = await asyncio.gather(
            _fetch_rag_chunks(request.message, machine_id),
            get_ml_snapshot(machine_id, db),
        )
    else:
        rag_chunks = await _fetch_rag_chunks(request.message, machine_id)
        ml_snapshot = None

    system_prompt = build_full_system_prompt(role_name, user_name, memories, rag_chunks)
    messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]

    if request.history:
        for msg in request.history:
            messages.append({"role": msg.role, "content": msg.content})
    else:
        for msg in await _load_db_history(session_svc, target_session, current_user.id):
            if msg.get("role") in ("user", "assistant"):
                messages.append(msg)

    _inject_rag_context(messages, rag_chunks)
    ml_context_injected = _inject_ml_context(messages, ml_snapshot)

    if machine_id is not None:
        logger.info(f"[ml_bridge] machine_id={str(machine_id).replace(chr(13), '').replace(chr(10), '')} ml_context_used={ml_context_injected}")

    messages.append({"role": "user", "content": request.message})

    tools = get_tool_definitions()
    try:
        groq = get_groq_client()
        response = groq.chat(messages=messages, tools=tools)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception(f"Groq error: {e}")
        raise HTTPException(status_code=503, detail=f"AI service unavailable: {e}")

    choices = response.get("choices", [])
    if not choices:
        raise HTTPException(status_code=500, detail="No response from AI")

    resp_msg = choices[0].get("message", {})
    content: str = resp_msg.get("content", "") or ""
    tool_calls = resp_msg.get("tool_calls", [])

    content, sources, tool_success, tool_failure = await _execute_tools(
        tool_calls, messages, db, groq, content
    )
    final_content = content or "J'ai traite votre requete."

    try:
        await session_svc.append_to_session(
            target_session.id, current_user.id,
            [{"role": "user", "content": request.message},
             {"role": "assistant", "content": final_content}],
        )
    except Exception as e:
        logger.warning(f"Failed to persist AI chat messages: {e}")

    await _record_memory_feedback(memories, memory_svc, tool_calls, tool_success, tool_failure)

    try:
        await db.refresh(target_session)
    except Exception:
        pass

    formatted_tool_calls = [
        {"id": tc["id"], "name": tc["function"]["name"],
         "arguments": json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"]}
        for tc in tool_calls
    ] if tool_calls else None

    return ChatResponse(
        message=final_content,
        tool_calls=formatted_tool_calls,
        sources=sources,
        session_id=str(target_session.id),
        session_title=target_session.title or _DEFAULT_SESSION_TITLE,
        ml_context_used=ml_context_injected,
    )


# ---------------------------------------------------------------------------
# Multi-agent deep analysis
# ---------------------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    query: str


class AnalyzeResponse(BaseModel):
    query: str
    analysis: str
    plan: Dict[str, Any]
    data_sources: List[Dict[str, Any]]


@router.post("/analyze", response_model=AnalyzeResponse, responses={500: {"description": "Internal Server Error"}, 503: {"description": "Service Unavailable"}})
async def analyze(
    request: AnalyzeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """
    Multi-agent deep EAM analysis.

    Three sequential specialized agents (all Groq):
      1. DataCollector  — calls EAM tools to gather relevant data
      2. Analyst        — diagnoses problems from collected data
      3. Planner        — produces prioritized structured action plan (JSON)

    Use for complex decisions, root-cause analysis, resource planning.
    For simple queries use /ai/chat.
    """
    role_name = current_user.role.value if current_user.role else "TECHNICIEN"

    # RAG context for analysis (injected as extra context string, not system prompt)
    rag_context_str = ""
    try:
        rag_chunks = await rag_client.retrieve_chunks(
            query=request.query,
            top_k=3,
            threshold=0.30,
        )
        if rag_chunks:
            rag_context_str = build_rag_context(rag_chunks)
    except Exception as e:
        logger.warning(f"RAG retrieval failed for analyze: {e}")

    # Append RAG context to query if available
    enriched_query = request.query
    if rag_context_str:
        enriched_query = request.query + "\n\n" + rag_context_str

    try:
        result = await run_eam_analysis(query=enriched_query, db=db, role=role_name)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception(f"Multi-agent analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

    try:
        session_svc = ChatSessionService(db)
        plan_summary = result["plan"].get("resume", "")
        await session_svc.append_messages(
            current_user.id,
            [
                {"role": "user", "content": f"[ANALYSE] {request.query}"},
                {
                    "role": "assistant",
                    "content": f"[PLAN] {plan_summary}\n\n{result['analysis']}",
                },
            ],
        )
    except Exception as e:
        logger.warning(f"Failed to persist analyze messages: {e}")

    return AnalyzeResponse(**result)

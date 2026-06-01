import json
import logging
from typing import List, Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs

from schemas.ai_chat import ChatRequest, ChatResponse
from services.ai_tools import get_tool_definitions, execute_tool
from services.ai_prompts import build_full_system_prompt, format_tool_result, build_rag_context
import services.rag_client as rag_client
from services.ai_memory import AIMemoryService
from services.chat_session_service import ChatSessionService
from services.ai_agents import run_eam_analysis
from core.groq_client import get_groq_client, groq_cache_stats, clear_groq_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


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
    current_user: Utilisateurs = Depends(get_current_user),
):
    """Role-based query suggestions."""
    role = current_user.role.value if current_user.role else ""
    return _SUGGESTIONS.get(role, _DEFAULT_SUGGESTIONS)


# ---------------------------------------------------------------------------
# Cache debug — ADMIN only
# ---------------------------------------------------------------------------

@router.get("/cache-stats")
async def get_cache_stats(
    current_user: Utilisateurs = Depends(get_current_user),
):
    """Return Groq LLM response cache hit/miss counters."""
    return {"groq_cache": groq_cache_stats()}


@router.post("/cache-clear", status_code=204)
async def post_cache_clear(
    current_user: Utilisateurs = Depends(get_current_user),
):
    """Force clear Groq response cache."""
    if not current_user.role or current_user.role.value != "ADMIN":
        raise HTTPException(status_code=403, detail="ADMIN role required.")
    clear_groq_cache()
    return None


# ---------------------------------------------------------------------------
# History — DB-backed, survives restarts
# ---------------------------------------------------------------------------

@router.get("/history")
async def get_history(
    limit: int = Query(default=20, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """Chat history for current user — DB-backed, survives restarts."""
    session_svc = ChatSessionService(db)
    info = await session_svc.get_session_info(current_user.id)
    messages = info["history"]
    return {
        "history": messages[-limit:],
        "total": info["total"],
        "session_id": info["session_id"],
        "last_query": info["last_query"],
    }


@router.delete("/history")
async def clear_history(
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """Clear chat history for current user."""
    session_svc = ChatSessionService(db)
    await session_svc.clear(current_user.id)
    return {"message": "Historique efface."}


# ---------------------------------------------------------------------------
# AI chat — LLM + tool calling + memory + DB history
# ---------------------------------------------------------------------------

@router.post("/ai/chat", response_model=ChatResponse)
async def ai_chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """
    AI-powered chat using Groq LLM with:
    - Role-based system prompt
    - User memory context (preferences, strategies, failures)
    - DB-persisted conversation history
    - Tool calling for structured EAM data
    - Memory feedback (success/failure tracking)
    """
    role_name = current_user.role.value if current_user.role else "TECHNICIEN"
    user_name = current_user.nom or "User"

    memory_svc = AIMemoryService(db)
    session_svc = ChatSessionService(db)

    # ── 1. Load + rank memories ───────────────────────────────────────────
    try:
        memories = await memory_svc.get_by_user(current_user.id)
        memories.sort(key=lambda m: m.success_count, reverse=True)
        memories = memories[:15]
    except Exception as e:
        logger.warning(f"Memory load failed, continuing without: {e}")
        memories = []

    # ── 2. RAG retrieval (before system prompt — chunks injected into it) ────
    rag_chunks = []
    try:
        rag_chunks = await rag_client.retrieve_chunks(
            query=request.message,
            machine_id=getattr(request, "machine_id", None),
            top_k=8,
            threshold=0.30,
        )
    except Exception as e:
        logger.warning(f"RAG retrieval failed, continuing without context: {e}")

    # ── 3. System prompt + memory + RAG context ───────────────────────────
    system_prompt = build_full_system_prompt(role_name, user_name, memories, rag_chunks)

    # ── 4. Message list (client history → DB fallback) ────────────────────
    messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]

    if request.history:
        for msg in request.history:
            messages.append({"role": msg.role, "content": msg.content})
    else:
        try:
            db_history = await session_svc.get_history(current_user.id, limit=20)
            for msg in db_history:
                if msg.get("role") in ("user", "assistant"):
                    messages.append(msg)
        except Exception as e:
            logger.warning(f"History load failed, continuing without: {e}")

    # ── 4b. RAG pre-turn: inject doc context as conversation turn ──────────
    # When RAG chunks found, prime the conversation with a user→assistant exchange
    # so the LLM answers from documentation BEFORE attempting any tool call.
    if rag_chunks:
        rag_text = build_rag_context(rag_chunks)
        messages.append({
            "role": "user",
            "content": (
                f"[BASE DOCUMENTAIRE] Voici les extraits pertinents de la documentation officielle:\n"
                f"{rag_text}\n\n"
                "Reponds directement depuis cette documentation. Ne pas appeler d'outil."
            ),
        })
        messages.append({
            "role": "assistant",
            "content": (
                "J'ai bien les extraits documentaires. "
                "Je vais repondre directement depuis la documentation officielle."
            ),
        })

    messages.append({"role": "user", "content": request.message})

    # ── 5. Groq call ──────────────────────────────────────────────────────
    tools = get_tool_definitions()
    try:
        groq = get_groq_client()
        response = groq.chat(messages=messages, tools=tools)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Groq error: {e}")
        raise HTTPException(status_code=503, detail=f"AI service unavailable: {e}")

    choices = response.get("choices", [])
    if not choices:
        raise HTTPException(status_code=500, detail="No response from AI")

    choice = choices[0]
    response_message = choice.get("message", {})
    content: str = response_message.get("content", "") or ""
    tool_calls = response_message.get("tool_calls", [])

    # ── 5. Tool execution ─────────────────────────────────────────────────
    sources = None
    tool_success = False
    tool_failure = False

    if tool_calls:
        sources = []
        for tool_call in tool_calls:
            func_name = tool_call["function"]["name"]
            func_args_raw = tool_call["function"]["arguments"]
            func_args = (
                json.loads(func_args_raw)
                if isinstance(func_args_raw, str)
                else func_args_raw
            )

            try:
                result = await execute_tool(func_name, func_args, db)
                tool_success = bool(result)
                if not result:
                    tool_failure = True
            except Exception as e:
                logger.error(f"Tool {func_name} failed: {e}")
                result = {"error": str(e)}
                tool_failure = True

            sources.append({"tool": func_name, "result": result})

            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [tool_call],
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": format_tool_result(func_name, result),
            })

        # ── 6. Second Groq call with tool results ─────────────────────────
        try:
            final_response = groq.chat(messages=messages)
            final_choices = final_response.get("choices", [])
            if final_choices:
                content = (
                    final_choices[0].get("message", {}).get("content", content) or content
                )
        except Exception as e:
            logger.warning(f"Final Groq call failed: {e}")
            content = content or "J'ai execute les actions demandees."

    final_content = content or "J'ai traite votre requete."

    # ── 7. Persist exchange ───────────────────────────────────────────────
    try:
        await session_svc.append_messages(
            current_user.id,
            [
                {"role": "user", "content": request.message},
                {"role": "assistant", "content": final_content},
            ],
        )
    except Exception as e:
        logger.warning(f"Failed to persist AI chat messages: {e}")

    # ── 8. Memory feedback ────────────────────────────────────────────────
    if memories and tool_calls:
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

    # ── 9. Return ─────────────────────────────────────────────────────────
    return ChatResponse(
        message=final_content,
        tool_calls=(
            [
                {
                    "id": tc["id"],
                    "name": tc["function"]["name"],
                    "arguments": (
                        json.loads(tc["function"]["arguments"])
                        if isinstance(tc["function"]["arguments"], str)
                        else tc["function"]["arguments"]
                    ),
                }
                for tc in tool_calls
            ]
            if tool_calls
            else None
        ),
        sources=sources,
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


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    request: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
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
        logger.error(f"Multi-agent analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

    try:
        session_svc = ChatSessionService(db)
        plan_summary = result["plan"].get("resume", "")
        await session_svc.append_messages(
            current_user.id,
            [
                {"role": "user", "content": f"[ANALYSE] {request.query}"},
                {"role": "assistant", "content": f"[PLAN] {plan_summary}\n\n{result['analysis']}"},
            ],
        )
    except Exception as e:
        logger.warning(f"Failed to persist analyze messages: {e}")

    return AnalyzeResponse(**result)

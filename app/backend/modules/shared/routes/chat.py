import logging
from typing import Optional, List, Any, Dict
from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs, UserRole
from services import chat as chat_service

# AI Chat imports
from schemas.ai_chat import ChatRequest, ChatResponse
from services.ai_tools import get_tool_definitions, execute_tool
from services.ai_prompts import get_system_prompt
from core.groq_client import get_groq_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

# In-memory chat history (in production, use Redis or DB)
CHAT_HISTORY: dict = defaultdict(list)
RATE_LIMIT = 10  # queries per minute


class ChatQueryRequest(BaseModel):
    query: str


class ChatQueryResponse(BaseModel):
    intent: str
    results: List[dict]
    confidence: float
    formatted_message: str
    suggestions: List[str]
    query: str


@router.post("/query", response_model=ChatQueryResponse)
async def chat_query(
    request: ChatQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """
    Process a natural language query and return structured results.
    """
    # Rate limiting check
    user_history = CHAT_HISTORY.get(current_user.id, [])
    now = datetime.utcnow()
    recent_queries = [q for q in user_history if q.get("timestamp") and 
                     (now - q["timestamp"]).total_seconds() < 60]
    
    if len(recent_queries) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait before sending another query."
        )
    
    # Parse the query
    parsed = chat_service.parse_query(request.query)
    
    # Execute query
    results = await chat_service.execute_query(
        db, 
        parsed["intent"], 
        parsed["params"]
    )
    
    # Format response
    formatted = chat_service.format_response(
        results, 
        parsed["intent"], 
        parsed["params"]
    )
    
    # Get suggestions
    suggestions = chat_service.get_suggestions(current_user.role.value if current_user.role else None)
    
    # Save to history
    chat_entry = {
        "query": request.query,
        "intent": parsed["intent"],
        "results_count": len(results),
        "timestamp": now
    }
    CHAT_HISTORY[current_user.id].append(chat_entry)
    
    # Keep only last 50 entries per user
    if len(CHAT_HISTORY[current_user.id]) > 50:
        CHAT_HISTORY[current_user.id] = CHAT_HISTORY[current_user.id][-50:]
    
    return ChatQueryResponse(
        intent=parsed["intent"],
        results=results,
        confidence=parsed["confidence"],
        formatted_message=formatted["message"],
        suggestions=suggestions,
        query=request.query
    )


@router.get("/suggestions", response_model=List[str])
async def get_suggestions(
    current_user: Utilisateurs = Depends(get_current_user),
):
    """
    Get suggested queries based on user role.
    """
    return chat_service.get_suggestions(
        current_user.role.value if current_user.role else None
    )


@router.get("/history")
async def get_history(
    limit: int = Query(default=20, le=50),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """
    Get chat query history for the current user.
    """
    history = CHAT_HISTORY.get(current_user.id, [])
    return {
        "history": history[-limit:],
        "total": len(history)
    }


@router.post("/ai/chat", response_model=ChatResponse)
async def ai_chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """
    AI-powered chat using Groq LLM.
    
    No memory integration yet - plain chat with tool calling.
    """
    # Build messages
    role_name = current_user.role.value if current_user.role else "TECHNICIEN"
    system_prompt = get_system_prompt(role_name, current_user.nom or "User")
    
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add history
    if request.history:
        for msg in request.history:
            messages.append({"role": msg.role, "content": msg.content})
    
    # Add current message
    messages.append({"role": "user", "content": request.message})
    
    # Get tools
    tools = get_tool_definitions()
    
    # Call Groq
    try:
        groq = get_groq_client()
        response = groq.chat(messages=messages, tools=tools)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Groq error: {e}")
        raise HTTPException(status_code=503, detail=f"AI service unavailable: {str(e)}")
    
    # Extract response
    choices = response.get("choices", [])
    if not choices:
        raise HTTPException(status_code=500, detail="No response from AI")
    
    choice = choices[0]
    response_message = choice.get("message", {})
    content = response_message.get("content", "")
    
    # Check for tool calls
    tool_calls = response_message.get("tool_calls", [])
    
    # Execute tools if present
    sources = None
    if tool_calls:
        sources = []
        for tool_call in tool_calls:
            func_name = tool_call["function"]["name"]
            func_args = tool_call["function"]["arguments"]
            
            result = execute_tool(func_name, func_args, db)
            sources.append({
                "tool": func_name,
                "result": result
            })
            
            # Add tool result to messages for final response
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [tool_call]
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": str(result)
            })
        
        # Get final response with tool results
        try:
            final_response = groq.chat(messages=messages)
            final_choices = final_response.get("choices", [])
            if final_choices:
                content = final_choices[0].get("message", {}).get("content", content)
        except Exception as e:
            logger.warning(f"Error getting final response: {e}")
            content = content or "J'ai execute les actions demandees."
    
    return ChatResponse(
        message=content or "J'ai traite votre requete.",
        tool_calls=[{"id": tc["id"], "name": tc["function"]["name"], "arguments": tc["function"]["arguments"]} for tc in tool_calls] if tool_calls else None,
        sources=sources
    )

import logging
from typing import Optional, List
from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs, UserRole
from services import chat as chat_service

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

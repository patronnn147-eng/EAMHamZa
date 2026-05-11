"""Chat schemas for AI chat endpoint"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Single chat message"""
    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request to AI chat endpoint"""
    message: str = Field(..., description="User's message")
    history: Optional[List[ChatMessage]] = Field(
        default_factory=list,
        description="Conversation history"
    )
    machine_id: Optional[int] = Field(
        default=None,
        description="Optional machine ID for filtered RAG retrieval",
    )


class ToolCall(BaseModel):
    """Tool call requested by AI"""
    id: str
    name: str
    arguments: Dict[str, Any]


class ChatResponse(BaseModel):
    """Response from AI chat endpoint"""
    message: str = Field(..., description="AI's response")
    tool_calls: Optional[List[ToolCall]] = Field(
        default=None,
        description="Tool calls requested by AI"
    )
    sources: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Data sources used for response"
    )
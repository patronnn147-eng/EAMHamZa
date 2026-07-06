from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Annotated
from uuid import UUID

from core.database import get_db
from dependencies.auth import get_current_user
from models.utilisateurs import Utilisateurs
from schemas.ai_memory import (
    AIMemoryCreate,
    AIMemoryUpdate,
    AIMemoryResponse,
    AIMemoryListResponse,
)
from services.ai_memory import AIMemoryService

router = APIRouter(prefix="/api/v1/ai/memory", tags=["AI Memory"])

_MEMORY_NOT_FOUND_MSG = "Memory not found"


@router.post("", response_model=AIMemoryResponse, status_code=201)
async def create_memory(
    data: AIMemoryCreate,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new AI memory entry"""
    service = AIMemoryService(db)
    return await service.create(data, utilisateur_id=current_user.id)


@router.get("/my", response_model=AIMemoryListResponse)
async def get_my_memories(
    *, memory_type: Optional[str] = None,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get all memories for the current user"""
    service = AIMemoryService(db)
    memories = await service.get_by_user(
        utilisateur_id=current_user.id,
        memory_type=memory_type,
    )
    return AIMemoryListResponse(
        memories=[AIMemoryResponse.model_validate(m) for m in memories],
        total=len(memories),
    )


@router.get("/my/summary")
async def get_memory_summary(
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Get summary of all memory types for current user"""
    service = AIMemoryService(db)
    return await service.get_all_types(utilisateur_id=current_user.id)


@router.get("/{memory_id}", response_model=AIMemoryResponse)
async def get_memory(
    memory_id: UUID,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a specific memory by ID"""
    service = AIMemoryService(db)
    memory = await service.get_by_id(str(memory_id))
    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_MEMORY_NOT_FOUND_MSG,
        )
    # Only allow users to view their own memories
    if memory.utilisateur_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this memory",
        )
    return memory


@router.patch("/{memory_id}", response_model=AIMemoryResponse)
async def update_memory(
    memory_id: UUID,
    data: AIMemoryUpdate,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update an existing memory"""
    service = AIMemoryService(db)
    memory = await service.get_by_id(str(memory_id))
    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_MEMORY_NOT_FOUND_MSG,
        )
    # Only allow users to update their own memories
    if memory.utilisateur_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this memory",
        )
    return await service.update(str(memory_id), data)


@router.post("/{memory_id}/success", response_model=AIMemoryResponse)
async def mark_success(
    memory_id: UUID,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Increment success count for a memory"""
    service = AIMemoryService(db)
    memory = await service.get_by_id(str(memory_id))
    if not memory or memory.utilisateur_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=_MEMORY_NOT_FOUND_MSG
        )
    return await service.increment_success(str(memory_id))


@router.post("/{memory_id}/failure", response_model=AIMemoryResponse)
async def mark_failure(
    memory_id: UUID,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Increment failure count for a memory"""
    service = AIMemoryService(db)
    memory = await service.get_by_id(str(memory_id))
    if not memory or memory.utilisateur_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=_MEMORY_NOT_FOUND_MSG
        )
    return await service.increment_failure(str(memory_id))


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(
    memory_id: UUID,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a memory"""
    service = AIMemoryService(db)
    memory = await service.get_by_id(str(memory_id))
    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_MEMORY_NOT_FOUND_MSG,
        )
    # Only allow users to delete their own memories
    if memory.utilisateur_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this memory",
        )
    await service.delete(str(memory_id))
    return None

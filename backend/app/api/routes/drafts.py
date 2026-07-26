import uuid
from typing import Dict, Any
from fastapi import APIRouter, Depends, status, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_async_db
from app.models.user import User
from app.services.draft_service import DraftService
from app.core.exceptions import APIException

router = APIRouter(prefix="/drafts", tags=["Conversation Drafts"])

@router.get("/{conversation_id}", response_model=Dict[str, Any])
async def get_draft(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Returns the user's saved draft for a specific conversation.
    """
    draft_service = DraftService(db)
    draft = await draft_service.get_draft(conversation_id, current_user.id)
    if not draft:
        return {
            "success": True,
            "data": None
        }
    return {
        "success": True,
        "data": {
            "conversation_id": str(draft.conversation_id),
            "content": draft.content,
            "updated_at": draft.updated_at.isoformat()
        }
    }

@router.post("/{conversation_id}", response_model=Dict[str, Any])
async def save_draft(
    conversation_id: uuid.UUID,
    content: str = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Saves or updates a draft message for a specific conversation.
    """
    if not content.strip():
        raise APIException(status.HTTP_400_BAD_REQUEST, "INVALID_INPUT", "Draft content cannot be empty")
        
    draft_service = DraftService(db)
    draft = await draft_service.save_draft(conversation_id, current_user.id, content)
    return {
        "success": True,
        "data": {
            "conversation_id": str(draft.conversation_id),
            "content": draft.content,
            "updated_at": draft.updated_at.isoformat()
        }
    }

@router.delete("/{conversation_id}", response_model=Dict[str, Any])
async def delete_draft(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Clears the saved draft for a specific conversation.
    """
    draft_service = DraftService(db)
    cleared = await draft_service.clear_draft(conversation_id, current_user.id)
    return {
        "success": True,
        "data": {
            "cleared": cleared
        }
    }

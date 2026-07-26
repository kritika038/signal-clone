from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_async_db, get_current_user
from app.api.routes.common import format_conversation
from app.core.exceptions import APIException
from app.models.conversation import Conversation
from app.models.conversation_member import ConversationMember
from app.models.user import User
from app.repositories.conversation import ConversationRepository

router = APIRouter(prefix="/conversations", tags=["Conversations"])


class ConversationCreate(BaseModel):
    participant_id: uuid.UUID


class ConversationUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=255)
    is_archived: bool | None = None
    is_pinned: bool | None = None
    is_muted: bool | None = None
    mute_duration_hours: int | None = Field(default=None, ge=1, le=720)


async def _get_accessible_conversation(
    db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID
) -> Conversation:
    query = (
        select(Conversation)
        .where(Conversation.id == conversation_id, Conversation.deleted_at.is_(None))
        .options(
            selectinload(Conversation.members).selectinload(ConversationMember.user),
            selectinload(Conversation.last_message).selectinload("*"),
        )
    )
    result = await db.execute(query)
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise APIException(status.HTTP_404_NOT_FOUND, "CONVERSATION_NOT_FOUND", "Conversation not found")
    if not any(member.user_id == user_id and member.left_at is None for member in conversation.members):
        raise APIException(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "User is not a member of this conversation")
    return conversation


@router.get("", response_model=dict[str, Any])
async def list_conversations(
    limit: int = Query(default=20, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    conversations = await ConversationRepository(db).get_recent_conversations(current_user.id, limit=limit, skip=skip)
    return {"success": True, "data": [format_conversation(conversation) for conversation in conversations]}


@router.get("/search", response_model=dict[str, Any])
async def search_conversations(
    q: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    conversations = await ConversationRepository(db).search_conversations(current_user.id, q)
    return {"success": True, "data": [format_conversation(conversation) for conversation in conversations]}


@router.get("/{id}", response_model=dict[str, Any])
async def get_conversation(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    conversation = await _get_accessible_conversation(db, id, current_user.id)
    return {"success": True, "data": format_conversation(conversation)}


@router.post("", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
async def create_conversation(
    payload: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    if payload.participant_id == current_user.id:
        raise APIException(status.HTTP_400_BAD_REQUEST, "INVALID_CONVERSATION", "Cannot create a direct chat with yourself")
    participant = await db.get(User, payload.participant_id)
    if not participant or participant.deleted_at is not None:
        raise APIException(status.HTTP_404_NOT_FOUND, "USER_NOT_FOUND", "Participant not found")
    conversation = await ConversationRepository(db).create_direct_chat(current_user.id, payload.participant_id)
    conversation = await _get_accessible_conversation(db, conversation.id, current_user.id)
    return {"success": True, "data": format_conversation(conversation)}


@router.patch("/{id}", response_model=dict[str, Any])
async def update_conversation(
    id: uuid.UUID,
    payload: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    conversation = await _get_accessible_conversation(db, id, current_user.id)
    repo = ConversationRepository(db)

    if payload.name is not None:
        conversation.name = payload.name
    if payload.description is not None:
        conversation.description = payload.description
    if payload.avatar_url is not None:
        conversation.avatar_url = payload.avatar_url
    if payload.is_archived is not None:
        conversation.is_archived = payload.is_archived
    if payload.is_pinned is not None:
        await repo.pin_conversation(id, current_user.id, payload.is_pinned)
    if payload.is_muted is not None:
        await repo.mute_conversation(
            id, current_user.id, payload.is_muted, duration_hours=payload.mute_duration_hours
        )

    conversation.updated_by = current_user.id
    conversation.updated_at = datetime.now(timezone.utc)
    await db.commit()
    conversation = await _get_accessible_conversation(db, id, current_user.id)
    return {"success": True, "data": format_conversation(conversation)}


@router.delete("/{id}", response_model=dict[str, Any])
async def delete_conversation(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    conversation = await _get_accessible_conversation(db, id, current_user.id)
    conversation.deleted_at = datetime.now(timezone.utc)
    conversation.updated_by = current_user.id
    await db.commit()
    return {"success": True, "data": {"deleted": True, "id": str(id)}}

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_async_db, get_current_user
from app.api.routes.common import format_message
from app.core.exceptions import APIException
from app.models.conversation_member import ConversationMember
from app.models.enums import MessageType
from app.models.message import Message
from app.models.user import User
from app.repositories.message import MessageRepository
from app.services.message_service import MessageService

router = APIRouter(tags=["Messages"])


class MessageCreatePayload(BaseModel):
    content: str | None = Field(default=None, max_length=2000)
    message_type: MessageType = MessageType.TEXT
    reply_to_id: uuid.UUID | None = None
    attachments: list[dict[str, Any]] | None = None
    client_message_id: str | None = Field(default=None, max_length=100)
    scheduled_at: datetime | None = None


class MessageUpdatePayload(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class MessageDeletePayload(BaseModel):
    delete_type: str = Field(default="everyone")


async def _ensure_membership(db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID) -> None:
    query = select(ConversationMember).where(
        and_(
            ConversationMember.conversation_id == conversation_id,
            ConversationMember.user_id == user_id,
            ConversationMember.left_at.is_(None),
        )
    )
    result = await db.execute(query)
    if not result.scalar_one_or_none():
        raise APIException(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "User is not a member of this conversation")


@router.get("/conversations/{id}/messages", response_model=dict[str, Any])
async def list_conversation_messages(
    id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    await _ensure_membership(db, id, current_user.id)
    messages = await MessageRepository(db).get_messages_by_conversation(id, limit=limit, skip=skip)
    return {"success": True, "data": [format_message(message) for message in messages]}


@router.post("/conversations/{id}/messages", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
async def create_message(
    id: uuid.UUID,
    payload: MessageCreatePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    message = await MessageService(db).send_new_message(
        conversation_id=id,
        sender_id=current_user.id,
        content=payload.content,
        message_type=payload.message_type,
        reply_to_id=payload.reply_to_id,
        attachments_in=payload.attachments,
        client_message_id=payload.client_message_id,
        scheduled_at=payload.scheduled_at,
    )
    detailed = await MessageRepository(db).get_message_detail(message.id)
    return {"success": True, "data": format_message(detailed or message)}


@router.patch("/messages/{id}", response_model=dict[str, Any])
async def edit_message(
    id: uuid.UUID,
    payload: MessageUpdatePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    try:
        message = await MessageService(db).edit_user_message(id, current_user.id, payload.content)
    except ValueError as exc:
        raise APIException(status.HTTP_404_NOT_FOUND, "MESSAGE_NOT_FOUND", str(exc))
    except PermissionError as exc:
        raise APIException(status.HTTP_403_FORBIDDEN, "FORBIDDEN", str(exc))
    return {"success": True, "data": format_message(message)}


@router.delete("/messages/{id}", response_model=dict[str, Any])
async def delete_message(
    id: uuid.UUID,
    payload: MessageDeletePayload = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    try:
        if payload.delete_type.lower() == "me":
            await MessageService(db).delete_for_me(id, current_user.id)
            return {"success": True, "data": {"deleted": True, "scope": "me", "id": str(id)}}
        message = await MessageService(db).delete_for_everyone(id, current_user.id)
        return {"success": True, "data": format_message(message)}
    except ValueError as exc:
        raise APIException(status.HTTP_404_NOT_FOUND, "MESSAGE_NOT_FOUND", str(exc))
    except PermissionError as exc:
        raise APIException(status.HTTP_403_FORBIDDEN, "FORBIDDEN", str(exc))

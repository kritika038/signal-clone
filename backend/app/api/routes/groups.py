from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_async_db, get_current_user
from app.api.routes.common import format_conversation
from app.core.exceptions import APIException
from app.models.conversation import Conversation
from app.models.conversation_member import ConversationMember
from app.models.enums import ConversationRole, ConversationType
from app.models.user import User
from app.repositories.group import GroupRepository

router = APIRouter(prefix="/groups", tags=["Groups"])


class GroupCreatePayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    member_ids: list[uuid.UUID] = Field(default_factory=list)


class GroupUpdatePayload(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=255)


class GroupAddMemberPayload(BaseModel):
    user_id: uuid.UUID
    role: ConversationRole = ConversationRole.MEMBER


async def _get_group(db: AsyncSession, group_id: uuid.UUID, user_id: uuid.UUID) -> Conversation:
    query = (
        select(Conversation)
        .where(
            Conversation.id == group_id,
            Conversation.type == ConversationType.GROUP,
            Conversation.deleted_at.is_(None),
        )
        .options(
            selectinload(Conversation.members).selectinload(ConversationMember.user),
            selectinload(Conversation.last_message).selectinload("*"),
        )
    )
    result = await db.execute(query)
    group = result.scalar_one_or_none()
    if not group:
        raise APIException(status.HTTP_404_NOT_FOUND, "GROUP_NOT_FOUND", "Group not found")
    if not any(member.user_id == user_id and member.left_at is None for member in group.members):
        raise APIException(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "User is not a member of this group")
    return group


async def _ensure_admin(group: Conversation, user_id: uuid.UUID) -> None:
    actor = next((member for member in group.members if member.user_id == user_id and member.left_at is None), None)
    if not actor or actor.role not in {ConversationRole.OWNER, ConversationRole.ADMIN}:
        raise APIException(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Admin privileges required")


@router.post("", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
async def create_group(
    payload: GroupCreatePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    group = await GroupRepository(db).create_group(
        name=payload.name,
        description=payload.description,
        creator_id=current_user.id,
        member_ids=payload.member_ids,
    )
    group = await _get_group(db, group.id, current_user.id)

    if payload.member_ids:
        try:
            from app.services.notification_service import NotificationService
            await NotificationService(db).notify_group_invite(
                conversation=group,
                inviter=current_user,
                invited_user_ids=payload.member_ids
            )
        except Exception:
            pass

    return {"success": True, "data": format_conversation(group)}



@router.get("/{id}", response_model=dict[str, Any])
async def get_group(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    group = await _get_group(db, id, current_user.id)
    return {"success": True, "data": format_conversation(group)}


@router.patch("/{id}", response_model=dict[str, Any])
async def update_group(
    id: uuid.UUID,
    payload: GroupUpdatePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    group = await _get_group(db, id, current_user.id)
    await _ensure_admin(group, current_user.id)
    if payload.name is not None:
        group.name = payload.name
    if payload.description is not None:
        group.description = payload.description
    if payload.avatar_url is not None:
        group.avatar_url = payload.avatar_url
    group.updated_by = current_user.id
    group.updated_at = datetime.now(timezone.utc)
    await db.commit()
    group = await _get_group(db, id, current_user.id)
    return {"success": True, "data": format_conversation(group)}


@router.post("/{id}/members", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
async def add_group_member(
    id: uuid.UUID,
    payload: GroupAddMemberPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    group = await _get_group(db, id, current_user.id)
    await _ensure_admin(group, current_user.id)
    member = await GroupRepository(db).add_member(id, payload.user_id, payload.role)
    try:
        from app.services.notification_service import NotificationService
        await NotificationService(db).notify_group_invite(
            conversation=group,
            inviter=current_user,
            invited_user_ids=[payload.user_id]
        )
    except Exception:
        pass
    return {

        "success": True,
        "data": {
            "id": str(member.id),
            "conversation_id": str(member.conversation_id),
            "user_id": str(member.user_id),
            "role": member.role.value if member.role else None,
            "left_at": member.left_at.isoformat() if member.left_at else None,
        },
    }


@router.delete("/{id}/members/{member_id}", response_model=dict[str, Any])
async def remove_group_member(
    id: uuid.UUID,
    member_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    group = await _get_group(db, id, current_user.id)
    await _ensure_admin(group, current_user.id)
    removed = await GroupRepository(db).remove_member(id, member_id)
    if not removed:
        raise APIException(status.HTTP_404_NOT_FOUND, "MEMBER_NOT_FOUND", "Member not found in group")
    return {"success": True, "data": {"removed": True, "conversation_id": str(id), "member_id": str(member_id)}}

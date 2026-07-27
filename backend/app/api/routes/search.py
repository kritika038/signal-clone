from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_async_db, get_current_user
from app.api.routes.common import format_contact, format_conversation, format_message
from app.models.contact import Contact
from app.models.conversation_member import ConversationMember
from app.models.message import Message
from app.models.user import User
from app.repositories.conversation import ConversationRepository

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("", response_model=dict[str, Any])
async def global_search(
    q: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    contact_query = (
        select(Contact)
        .join(User, User.id == Contact.contact_user_id)
        .where(
            and_(
                Contact.owner_id == current_user.id,
                or_(
                    Contact.nickname.ilike(f"%{q}%"),
                    User.username.ilike(f"%{q}%"),
                    User.display_name.ilike(f"%{q}%"),
                    User.phone.ilike(f"%{q}%"),
                ),
            )
        )
        .options(selectinload(Contact.contact_user))
    )
    contact_result = await db.execute(contact_query)
    contacts = contact_result.scalars().all()

    user_query = (
        select(User)
        .where(
            and_(
                User.deleted_at.is_(None),
                or_(
                    User.username.ilike(f"%{q}%"),
                    User.display_name.ilike(f"%{q}%"),
                    User.phone.ilike(f"%{q}%"),
                )
            )
        )
        .limit(20)
    )
    user_result = await db.execute(user_query)
    users = user_result.scalars().all()

    conversations = await ConversationRepository(db).search_conversations(current_user.id, q)

    member_subquery = (
        select(ConversationMember.conversation_id)
        .where(
            and_(
                ConversationMember.user_id == current_user.id,
                ConversationMember.left_at.is_(None),
            )
        )
    )
    message_query = (
        select(Message)
        .where(
            and_(
                Message.conversation_id.in_(member_subquery),
                Message.content.ilike(f"%{q}%"),
                Message.deleted_at.is_(None),
            )
        )
        .options(
            selectinload(Message.attachments),
            selectinload(Message.reactions),
            selectinload(Message.receipts),
        )
        .order_by(Message.created_at.desc())
        .limit(50)
    )
    message_result = await db.execute(message_query)
    messages = message_result.scalars().all()

    return {
        "success": True,
        "data": {
            "users": [
                {
                    "id": str(u.id),
                    "username": u.username,
                    "display_name": u.display_name,
                    "phone": u.phone,
                }
                for u in users
            ],
            "contacts": [format_contact(contact) for contact in contacts],
            "conversations": [format_conversation(conversation) for conversation in conversations],
            "messages": [format_message(message) for message in messages],
        },
    }

@router.get("/phone", response_model=dict[str, Any])
async def search_by_phone(
    q: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    user_query = (
        select(User)
        .where(
            and_(
                User.deleted_at.is_(None),
                User.phone == q
            )
        )
    )
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()

    if not user:
        return {"success": True, "data": None}

    return {
        "success": True,
        "data": {
            "id": str(user.id),
            "username": user.username,
            "display_name": user.display_name,
            "phone": user.phone,
        },
    }

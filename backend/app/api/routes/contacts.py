from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_async_db, get_current_user
from app.api.routes.common import format_contact
from app.core.exceptions import APIException
from app.models.contact import Contact
from app.models.user import User
from app.repositories.contact import ContactRepository

router = APIRouter(prefix="/contacts", tags=["Contacts"])


class ContactCreate(BaseModel):
    contact_user_id: uuid.UUID = Field(...)
    nickname: str | None = Field(default=None, max_length=100)


@router.get("", response_model=dict[str, Any])
async def list_contacts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    query = (
        select(Contact)
        .where(Contact.owner_id == current_user.id)
        .options(selectinload(Contact.contact_user))
        .order_by(Contact.created_at.desc())
    )
    result = await db.execute(query)
    contacts = result.scalars().all()
    return {"success": True, "data": [format_contact(contact) for contact in contacts]}


@router.get("/search", response_model=dict[str, Any])
async def search_contacts(
    q: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    query = (
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
        .order_by(Contact.created_at.desc())
    )
    result = await db.execute(query)
    contacts = result.scalars().all()
    return {"success": True, "data": [format_contact(contact) for contact in contacts]}


@router.post("", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
async def create_contact(
    payload: ContactCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    if payload.contact_user_id == current_user.id:
        raise APIException(status.HTTP_400_BAD_REQUEST, "INVALID_CONTACT", "Cannot add yourself as a contact")

    target_user = await db.get(User, payload.contact_user_id)
    if not target_user or target_user.deleted_at is not None:
        raise APIException(status.HTTP_404_NOT_FOUND, "CONTACT_NOT_FOUND", "Contact user not found")

    contact_repo = ContactRepository(db)
    existing_contact = await contact_repo.get_contact_by_users(current_user.id, payload.contact_user_id)
    if existing_contact:
        raise APIException(status.HTTP_400_BAD_REQUEST, "CONTACT_ALREADY_EXISTS", "User is already in your contacts")

    contact = await contact_repo.add_contact(
        current_user.id, payload.contact_user_id, payload.nickname
    )
    await db.refresh(contact, attribute_names=["contact_user"])
    return {"success": True, "data": format_contact(contact)}


@router.delete("/{id}", response_model=dict[str, Any])
async def delete_contact(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    contact = await db.get(Contact, id)
    if not contact or contact.owner_id != current_user.id:
        raise APIException(status.HTTP_404_NOT_FOUND, "CONTACT_NOT_FOUND", "Contact not found")
    await ContactRepository(db).remove(id=id)
    return {"success": True, "data": {"deleted": True, "id": str(id)}}

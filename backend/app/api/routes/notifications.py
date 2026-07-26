from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_async_db, get_current_user
from app.models.user import User
from app.repositories.notification import NotificationRepository
from app.schemas.auth import ProfileUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationPreferencesPayload(BaseModel):
    notifications_enabled: bool


@router.get("", response_model=dict[str, Any])
async def list_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    notifications = await NotificationRepository(db).get_unread_for_user(current_user.id)
    return {
        "success": True,
        "data": [
            {
                "id": str(notification.id),
                "user_id": str(notification.user_id),
                "message_id": str(notification.message_id) if notification.message_id else None,
                "type": notification.type,
                "is_read": notification.is_read,
                "created_at": notification.created_at.isoformat(),
            }
            for notification in notifications
        ],
    }


@router.patch("/preferences", response_model=dict[str, Any])
async def update_notification_preferences(
    payload: NotificationPreferencesPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    updated_user = await UserService(db).update_profile(
        current_user.id, ProfileUpdate(notifications_enabled=payload.notifications_enabled)
    )
    return {
        "success": True,
        "data": {
            "notifications_enabled": updated_user.settings.notifications_enabled if updated_user.settings else payload.notifications_enabled
        },
    }

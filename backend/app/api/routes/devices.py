from __future__ import annotations

from typing import Any, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_async_db, get_current_user
from app.models.user import User
from app.schemas.device import DeviceRegisterSchema, DeviceResponseSchema
from app.services.device_token_service import DeviceTokenService

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.post("/register", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
async def register_device(
    payload: DeviceRegisterSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    device = await DeviceTokenService(db).register_device(
        user_id=current_user.id,
        device_id=payload.device_id,
        platform=payload.platform,
        fcm_token=payload.fcm_token,
    )
    return {
        "success": True,
        "data": {
            "id": str(device.id),
            "user_id": str(device.user_id),
            "device_id": device.device_id,
            "platform": device.platform,
            "fcm_token": device.fcm_token,
            "created_at": device.created_at.isoformat(),
            "updated_at": device.updated_at.isoformat(),
            "last_seen": device.last_seen.isoformat(),
        },
    }


@router.delete("/{device_id}", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
async def delete_device(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    removed = await DeviceTokenService(db).remove_device(current_user.id, device_id)
    return {
        "success": True,
        "data": {"removed": removed, "device_id": device_id},
    }


@router.get("", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
async def get_devices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    devices = await DeviceTokenService(db).get_user_devices(current_user.id)
    return {
        "success": True,
        "data": [
            {
                "id": str(device.id),
                "user_id": str(device.user_id),
                "device_id": device.device_id,
                "platform": device.platform,
                "fcm_token": device.fcm_token,
                "created_at": device.created_at.isoformat(),
                "updated_at": device.updated_at.isoformat(),
                "last_seen": device.last_seen.isoformat(),
            }
            for device in devices
        ],
    }

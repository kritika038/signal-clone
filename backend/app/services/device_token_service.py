import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.device_token import DeviceToken
from app.repositories.device_token_repository import DeviceTokenRepository


class DeviceTokenService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DeviceTokenRepository(db)

    async def register_device(
        self,
        user_id: uuid.UUID,
        device_id: str,
        platform: str,
        fcm_token: str
    ) -> DeviceToken:
        return await self.repo.upsert_device_token(
            user_id=user_id,
            device_id=device_id,
            platform=platform,
            fcm_token=fcm_token
        )

    async def remove_device(self, user_id: uuid.UUID, device_id: str) -> bool:
        return await self.repo.delete_by_device_id(user_id, device_id)

    async def get_user_devices(self, user_id: uuid.UUID) -> List[DeviceToken]:
        return await self.repo.get_user_tokens(user_id)

    async def remove_invalid_tokens(self, invalid_tokens: List[str]) -> int:
        return await self.repo.delete_by_fcm_tokens(invalid_tokens)

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.device_token import DeviceToken


class DeviceTokenRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert_device_token(
        self,
        user_id: uuid.UUID,
        device_id: str,
        platform: str,
        fcm_token: str
    ) -> DeviceToken:
        query = select(DeviceToken).where(
            and_(
                DeviceToken.user_id == user_id,
                DeviceToken.device_id == device_id
            )
        )
        result = await self.db.execute(query)
        device_obj = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)

        # An FCM registration token represents one app installation. A token can
        # move between accounts (for example after logging out and in again), so
        # transfer its row instead of delivering another user's pushes.
        token_result = await self.db.execute(
            select(DeviceToken).where(DeviceToken.fcm_token == fcm_token)
        )
        token_obj = token_result.scalar_one_or_none()
        if token_obj is not None and token_obj is not device_obj:
            # The target device row may contain an older token. Removing it first
            # preserves both uniqueness constraints before the token is moved.
            if device_obj is not None:
                await self.db.delete(device_obj)
                await self.db.flush()
        else:
            token_obj = device_obj

        if token_obj:
            token_obj.user_id = user_id
            token_obj.device_id = device_id
            token_obj.platform = platform
            token_obj.fcm_token = fcm_token
            token_obj.last_seen = now
            token_obj.updated_at = now
        else:
            token_obj = DeviceToken(
                user_id=user_id,
                device_id=device_id,
                platform=platform,
                fcm_token=fcm_token,
                last_seen=now,
                created_at=now,
                updated_at=now
            )
            self.db.add(token_obj)

        await self.db.commit()
        await self.db.refresh(token_obj)
        return token_obj

    async def get_by_device_id(self, user_id: uuid.UUID, device_id: str) -> Optional[DeviceToken]:
        query = select(DeviceToken).where(
            and_(
                DeviceToken.user_id == user_id,
                DeviceToken.device_id == device_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_user_tokens(self, user_id: uuid.UUID) -> List[DeviceToken]:
        query = select(DeviceToken).where(DeviceToken.user_id == user_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_tokens_for_users(self, user_ids: List[uuid.UUID]) -> List[DeviceToken]:
        if not user_ids:
            return []
        query = select(DeviceToken).where(DeviceToken.user_id.in_(user_ids))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def delete_by_device_id(self, user_id: uuid.UUID, device_id: str) -> bool:
        token_obj = await self.get_by_device_id(user_id, device_id)
        if not token_obj:
            return False
        await self.db.delete(token_obj)
        await self.db.commit()
        return True

    async def delete_by_fcm_tokens(self, fcm_tokens: List[str]) -> int:
        if not fcm_tokens:
            return 0
        stmt = delete(DeviceToken).where(DeviceToken.fcm_token.in_(fcm_tokens))
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

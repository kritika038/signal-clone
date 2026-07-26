from typing import Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user_settings import UserSettings
from app.repositories.base import BaseRepository

class SettingsRepository(BaseRepository[UserSettings]):
    def __init__(self, db: AsyncSession):
        super().__init__(UserSettings, db)

    async def get_by_user_id(self, user_id: uuid.UUID) -> Optional[UserSettings]:
        query = select(UserSettings).where(UserSettings.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

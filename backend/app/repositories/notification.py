from typing import List
import uuid
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import Notification
from app.repositories.base import BaseRepository

class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, db: AsyncSession):
        super().__init__(Notification, db)

    async def get_unread_for_user(self, user_id: uuid.UUID) -> List[Notification]:
        query = select(Notification).where(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).order_by(Notification.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def mark_all_read(self, user_id: uuid.UUID) -> None:
        query = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
            .values(is_read=True)
        )
        await self.db.execute(query)
        await self.db.commit()

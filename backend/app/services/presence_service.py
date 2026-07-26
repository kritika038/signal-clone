import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PresenceStatus
from app.repositories.user import UserRepository

logger = logging.getLogger(__name__)

class PresenceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def update_presence(self, user_id: uuid.UUID, status: PresenceStatus) -> Optional[datetime]:
        """
        Updates the user's presence status in the database.
        If status is OFFLINE, updates the last_seen timestamp and returns it.
        """
        user = await self.user_repo.get(user_id)
        if not user:
            logger.warning(f"[PresenceService] User {user_id} not found to update presence")
            return None

        user.presence_status = status
        last_seen_time = None
        if status == PresenceStatus.OFFLINE:
            last_seen_time = datetime.now(timezone.utc)
            user.last_seen = last_seen_time
            
        await self.db.commit()
        await self.db.refresh(user)
        logger.info(f"[PresenceService] Presence for user {user.phone} updated to {status}")
        return last_seen_time

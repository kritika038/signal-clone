import uuid
import logging
from typing import Optional
from sqlalchemy import select
from app.models.contact import Contact
from app.models.enums import PresenceStatus
from app.websocket.connection_manager import connection_manager

logger = logging.getLogger(__name__)

class PresenceManager:
    async def broadcast_presence_change(
        self, user_id: uuid.UUID, status: PresenceStatus, last_seen: Optional[str], db_session
    ) -> None:
        """
        Queries all users who have added user_id as a contact,
        and broadcasts user_id's status update to their private rooms.
        """
        from app.websocket.manager import sio
        user_id_str = str(user_id)
        
        # Query contacts owners who have user_id in their contacts
        query = select(Contact.owner_id).where(Contact.contact_user_id == user_id)
        res = await db_session.execute(query)
        contact_owner_ids = res.scalars().all()
        
        payload = {
            "user_id": user_id_str,
            "status": status.value if hasattr(status, "value") else str(status),
            "last_seen": last_seen
        }
        
        # Broadcast to all connected contact owners
        count = 0
        for owner_id in contact_owner_ids:
            owner_id_str = str(owner_id)
            if connection_manager.is_user_online(owner_id_str):
                room = f"user:{owner_id_str}"
                await sio.emit("presence.update", payload, to=room)
                count += 1
                
        logger.info(f"[Presence] Broadcasted presence update for user {user_id_str} ({status}) to {count} contact(s)")

# Instantiate presence manager singleton
presence_manager = PresenceManager()

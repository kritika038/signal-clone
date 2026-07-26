import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select, and_
from app.db.session import SessionLocal
from app.models.message import Message
from app.websocket.rooms import get_conversation_room

logger = logging.getLogger(__name__)

class DisappearingMessageService:
    async def start_purger_loop(self, interval_seconds: float = 10.0):
        """
        Daemon task that periodically scans the database for disappearing
        messages that have passed their expiration timestamp, deletes them,
        and broadcasts deletion events.
        """
        logger.info("[DisappearingMessageService] Initiated disappearing message purger loop")
        while True:
            try:
                await asyncio.sleep(interval_seconds)
                await self.purge_expired_messages()
            except asyncio.CancelledError:
                logger.info("[DisappearingMessageService] Disappearing message purger cancelled")
                break
            except Exception as e:
                logger.error(f"[DisappearingMessageService] Exception in purger loop: {str(e)}")

    async def purge_expired_messages(self) -> None:
        from app.websocket.manager import sio
        now = datetime.now(timezone.utc)
        
        async with SessionLocal() as db:
            query = select(Message).where(
                and_(
                    Message.expires_at.is_not(None),
                    Message.expires_at <= now,
                    Message.deleted_at.is_(None)
                )
            )
            res = await db.execute(query)
            expired_messages = res.scalars().all()
            
            if not expired_messages:
                return

            logger.info(f"[DisappearingMessageService] Found {len(expired_messages)} expired message(s) to purge")
            
            for msg in expired_messages:
                msg_id_str = str(msg.id)
                conv_id_str = str(msg.conversation_id)
                
                # Perform cascade deletion from database
                await db.delete(msg)
                await db.commit()
                
                # Broadcast message.deleted to the conversation room
                room = get_conversation_room(msg.conversation_id)
                await sio.emit("message.deleted", {
                    "message_id": msg_id_str,
                    "conversation_id": conv_id_str,
                    "is_expired": True
                }, to=room)
                
                logger.info(f"[DisappearingMessageService] Purged expired message {msg_id_str} in conversation {conv_id_str}")

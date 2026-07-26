import asyncio
import logging
import uuid
from datetime import datetime, timezone
from sqlalchemy import select, and_, update
from sqlalchemy.orm import selectinload
from app.db.session import SessionLocal
from app.models.message import Message
from app.models.enums import ReceiptStatus
from app.models.conversation_member import ConversationMember
from app.websocket.rooms import get_conversation_room, get_user_room
from app.websocket.connection_manager import connection_manager

logger = logging.getLogger(__name__)

class ScheduledMessageService:
    async def start_scheduler_loop(self, interval_seconds: float = 10.0):
        """
        Daemon task that periodically polls the database for scheduled messages
        that are due for delivery and triggers their transmission.
        """
        logger.info("[ScheduledMessageService] Initiated scheduled message daemon loop")
        while True:
            try:
                await asyncio.sleep(interval_seconds)
                await self.process_due_messages()
            except asyncio.CancelledError:
                logger.info("[ScheduledMessageService] Scheduled message daemon cancelled")
                break
            except Exception as e:
                logger.error(f"[ScheduledMessageService] Exception in daemon loop: {str(e)}")

    async def process_due_messages(self) -> None:
        from app.websocket.manager import sio
        now = datetime.now(timezone.utc)
        
        async with SessionLocal() as db:
            # Select messages that are due and haven't been sent yet (scheduled_at is not null, but <= now)
            query = (
                select(Message)
                .where(
                    and_(
                        Message.scheduled_at.is_not(None),
                        Message.scheduled_at <= now,
                        Message.deleted_at.is_(None)
                    )
                )
                .options(selectinload(Message.attachments), selectinload(Message.receipts))
            )
            res = await db.execute(query)
            due_messages = res.scalars().all()
            
            if not due_messages:
                return

            logger.info(f"[ScheduledMessageService] Found {len(due_messages)} scheduled message(s) due for sending")
            
            for msg in due_messages:
                # 1. Clear scheduled_at to mark it as sent, and update created_at
                msg.scheduled_at = None
                msg.created_at = datetime.now(timezone.utc)
                
                # 2. Update status of receipts: Sender is READ, recipient is SENT/DELIVERED
                for receipt in msg.receipts:
                    if receipt.user_id == msg.sender_id:
                        receipt.status = ReceiptStatus.READ
                    else:
                        other_uid_str = str(receipt.user_id)
                        if connection_manager.is_user_online(other_uid_str):
                            receipt.status = ReceiptStatus.DELIVERED
                            # Notify sender of message delivery
                            sender_room = get_user_room(msg.sender_id)
                            await sio.emit("message.delivered", {
                                "message_id": str(msg.id),
                                "user_id": other_uid_str
                            }, to=sender_room)
                        else:
                            receipt.status = ReceiptStatus.SENT
                
                await db.commit()
                
                # 3. Format payload
                msg_payload = {
                    "id": str(msg.id),
                    "conversation_id": str(msg.conversation_id),
                    "sender_id": str(msg.sender_id),
                    "content": msg.content,
                    "message_type": msg.message_type.value if hasattr(msg.message_type, "value") else str(msg.message_type),
                    "reply_to_id": str(msg.reply_to_id) if msg.reply_to_id else None,
                    "created_at": msg.created_at.isoformat(),
                    "attachments": [
                        {
                            "id": str(a.id),
                            "original_filename": a.original_filename,
                            "mime_type": a.mime_type,
                            "size": a.size
                        } for a in msg.attachments
                    ]
                }
                
                # 4. Broadcast message.received to all conversation members (including sender)
                room = get_conversation_room(msg.conversation_id)
                await sio.emit("message.received", msg_payload, to=room)
                
                # Also acknowledge sender with message.sent
                sender_sockets = connection_manager.get_sockets_for_user(str(msg.sender_id))
                for sid in sender_sockets:
                    await sio.emit("message.sent", msg_payload, to=sid)

                logger.info(f"[ScheduledMessageService] Sent scheduled message {msg.id}")

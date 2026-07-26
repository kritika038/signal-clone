import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import ValidationError
from sqlalchemy import and_, select

from app.db.session import SessionLocal
from app.models.conversation_member import ConversationMember
from app.models.enums import PresenceStatus, ReceiptStatus, MessageType
from app.models.message import Message
from app.schemas.websocket import (
    WSMessageSend,
    WSMessageEdit,
    WSMessageDelete,
    WSReceiptUpdate,
    WSTypingEvent,
    WSPresenceUpdate
)
from app.services.message_service import MessageService
from app.services.presence_service import PresenceService
from app.services.receipt_service import ReceiptService
from app.services.typing_service import TypingService
from app.websocket.connection_manager import connection_manager
from app.websocket.presence_manager import presence_manager
from app.websocket.typing_manager import typing_manager
from app.websocket.rooms import (
    get_conversation_room,
    get_user_room,
    sync_rooms_for_connection
)
from app.api.deps import global_rate_limiter

logger = logging.getLogger(__name__)

class WebSocketGateway:
    """
    Orchestrates real-time events.
    Parses Pydantic schemas, authorizes requests, checks rate-limits,
    executes service business logic, and handles WebSocket broadcasts.
    """
    async def _check_rate_limit(self, sid: str, user_id_str: str, event: str) -> bool:
        """
        Applies a sliding window rate limiter on socket events.
        """
        from app.websocket.manager import sio
        rate_key = f"ws:{user_id_str}:{event}"
        # Limit to 10 events per 10 seconds for standard events
        is_limited = await global_rate_limiter.is_rate_limited(rate_key, limit=10, window_seconds=10)
        if is_limited:
            await sio.emit("ws.error", {
                "message": f"Rate limit exceeded for event '{event}'. Try again in a few seconds."
            }, to=sid)
            return True
        return False

    async def handle_connect(self, sid: str, user_id: uuid.UUID) -> None:
        from app.websocket.manager import sio
        user_id_str = str(user_id)
        connection_manager.connect(sid, user_id_str)
        
        async with SessionLocal() as db:
            await sync_rooms_for_connection(sid, user_id, db)
            
            presence_service = PresenceService(db)
            await presence_service.update_presence(user_id, PresenceStatus.ONLINE)
            
            await presence_manager.broadcast_presence_change(
                user_id, PresenceStatus.ONLINE, last_seen=None, db_session=db
            )
            
            receipt_service = ReceiptService(db)
            offline_messages = await receipt_service.sync_offline_messages(user_id)
            
            if offline_messages:
                for msg in offline_messages:
                    payload = {
                        "id": str(msg.id),
                        "conversation_id": str(msg.conversation_id),
                        "sender_id": str(msg.sender_id),
                        "content": msg.content,
                        "message_type": msg.message_type.value if hasattr(msg.message_type, "value") else str(msg.message_type),
                        "reply_to_id": str(msg.reply_to_id) if msg.reply_to_id else None,
                        "created_at": msg.created_at.isoformat()
                    }
                    await sio.emit("message.received", payload, to=sid)
                    
                    sender_room = get_user_room(msg.sender_id)
                    await sio.emit("message.delivered", {
                        "message_id": str(msg.id),
                        "user_id": user_id_str
                    }, to=sender_room)

    async def handle_disconnect(self, sid: str) -> None:
        user_id_str = connection_manager.disconnect(sid)
        if user_id_str:
            user_id = uuid.UUID(user_id_str)
            async with SessionLocal() as db:
                presence_service = PresenceService(db)
                last_seen_time = await presence_service.update_presence(user_id, PresenceStatus.OFFLINE)
                
                last_seen_iso = last_seen_time.isoformat() if last_seen_time else None
                await presence_manager.broadcast_presence_change(
                    user_id, PresenceStatus.OFFLINE, last_seen=last_seen_iso, db_session=db
                )

    async def handle_heartbeat(self, sid: str) -> None:
        connection_manager.record_activity(sid)
        logger.debug(f"[WS Gateway] Received heartbeat for socket {sid}")

    async def handle_message_send(self, sid: str, data: Any) -> None:
        from app.websocket.manager import sio
        user_id_str = connection_manager.get_user_id(sid)
        if not user_id_str:
            await sio.emit("ws.error", {"message": "Unauthorized socket connection"}, to=sid)
            return

        if await self._check_rate_limit(sid, user_id_str, "message.send"):
            return

        try:
            payload = WSMessageSend(**data)
        except ValidationError as e:
            await sio.emit("ws.error", {"message": "Invalid message.send payload", "details": e.errors()}, to=sid)
            return

        scheduled_at_raw = data.get("scheduled_at")
        scheduled_at = None
        if scheduled_at_raw:
            try:
                scheduled_at = datetime.fromisoformat(scheduled_at_raw)
                if scheduled_at <= datetime.now(timezone.utc):
                    await sio.emit("ws.error", {"message": "Scheduled time must be in the future"}, to=sid)
                    return
            except ValueError:
                await sio.emit("ws.error", {"message": "Invalid scheduled_at timestamp format"}, to=sid)
                return

        user_id = uuid.UUID(user_id_str)
        async with SessionLocal() as db:
            msg_service = MessageService(db)
            try:
                msg = await msg_service.send_new_message(
                    conversation_id=payload.conversation_id,
                    sender_id=user_id,
                    content=payload.content,
                    message_type=payload.message_type,
                    reply_to_id=payload.reply_to_id,
                    attachments_in=payload.attachments,
                    client_message_id=data.get("client_message_id"),
                    scheduled_at=scheduled_at
                )
                msg = await msg_service.msg_repo.get_message_detail(msg.id)
            except ValueError as e:
                await sio.emit("ws.error", {"message": str(e)}, to=sid)
                return

            msg_payload = {
                "id": str(msg.id),
                "conversation_id": str(msg.conversation_id),
                "sender_id": str(msg.sender_id),
                "content": msg.content,
                "message_type": msg.message_type.value if hasattr(msg.message_type, "value") else str(msg.message_type),
                "reply_to_id": str(msg.reply_to_id) if msg.reply_to_id else None,
                "created_at": msg.created_at.isoformat(),
                "scheduled_at": msg.scheduled_at.isoformat() if msg.scheduled_at else None,
                "attachments": [
                    {
                        "id": str(a.id),
                        "original_filename": a.original_filename,
                        "mime_type": a.mime_type,
                        "size": a.size
                    } for a in msg.attachments
                ]
            }

            # If it is scheduled, just send acknowledgment to sender
            if msg.scheduled_at:
                await sio.emit("message.scheduled", msg_payload, to=sid)
                logger.info(f"[WS Gateway] Scheduled message {msg.id} registered for {msg.scheduled_at}")
                return

            await sio.emit("message.sent", msg_payload, to=sid)

            room = get_conversation_room(payload.conversation_id)
            await sio.emit("message.received", msg_payload, to=room, skip_sid=sid)

            from sqlalchemy import select
            from app.models.conversation_member import ConversationMember
            member_query = select(ConversationMember).where(
                ConversationMember.conversation_id == payload.conversation_id,
                ConversationMember.left_at.is_(None),
                ConversationMember.user_id != user_id
            )
            res_members = await db.execute(member_query)
            active_members = res_members.scalars().all()

            receipt_service = ReceiptService(db)
            for member in active_members:
                other_uid_str = str(member.user_id)
                if connection_manager.is_user_online(other_uid_str):
                    await receipt_service.update_receipt(msg.id, member.user_id, ReceiptStatus.DELIVERED)
                    sender_room = get_user_room(user_id)
                    await sio.emit("message.delivered", {
                        "message_id": str(msg.id),
                        "user_id": other_uid_str
                    }, to=sender_room)

    async def handle_message_edit(self, sid: str, data: Any) -> None:
        from app.websocket.manager import sio
        user_id_str = connection_manager.get_user_id(sid)
        if not user_id_str:
            return

        if await self._check_rate_limit(sid, user_id_str, "message.edit"):
            return

        try:
            payload = WSMessageEdit(**data)
        except ValidationError as e:
            await sio.emit("ws.error", {"message": "Invalid message.edit payload", "details": e.errors()}, to=sid)
            return

        user_id = uuid.UUID(user_id_str)
        async with SessionLocal() as db:
            msg_service = MessageService(db)
            try:
                msg = await msg_service.edit_user_message(payload.message_id, user_id, payload.content)
            except (ValueError, PermissionError) as e:
                await sio.emit("ws.error", {"message": str(e)}, to=sid)
                return

            room = get_conversation_room(msg.conversation_id)
            await sio.emit("message.updated", {
                "message_id": str(msg.id),
                "conversation_id": str(msg.conversation_id),
                "content": msg.content,
                "edited_at": msg.edited_at.isoformat() if msg.edited_at else None
            }, to=room)

    async def handle_message_delete(self, sid: str, data: Any) -> None:
        from app.websocket.manager import sio
        user_id_str = connection_manager.get_user_id(sid)
        if not user_id_str:
            return

        if await self._check_rate_limit(sid, user_id_str, "message.delete"):
            return

        message_id_str = data.get("message_id")
        delete_type = data.get("delete_type", "everyone").lower() # "everyone" or "me"
        
        if not message_id_str:
            await sio.emit("ws.error", {"message": "Missing message_id"}, to=sid)
            return

        message_id = uuid.UUID(message_id_str)
        user_id = uuid.UUID(user_id_str)
        
        async with SessionLocal() as db:
            msg_service = MessageService(db)
            if delete_type == "me":
                try:
                    await msg_service.delete_for_me(message_id, user_id)
                except ValueError as e:
                    await sio.emit("ws.error", {"message": str(e)}, to=sid)
                    return
                # Acknowledge deletion for me only to sender's sockets
                await sio.emit("message.deleted_for_me", {
                    "message_id": str(message_id)
                }, to=sid)
            else:
                try:
                    msg = await msg_service.delete_for_everyone(message_id, user_id)
                except (ValueError, PermissionError) as e:
                    await sio.emit("ws.error", {"message": str(e)}, to=sid)
                    return

                room = get_conversation_room(msg.conversation_id)
                await sio.emit("message.deleted", {
                    "message_id": str(msg.id),
                    "conversation_id": str(msg.conversation_id),
                    "is_expired": False
                }, to=room)

    async def handle_reaction_toggle(self, sid: str, data: Any) -> None:
        """
        Toggles a user's emoji reaction on a message.
        """
        from app.websocket.manager import sio
        user_id_str = connection_manager.get_user_id(sid)
        if not user_id_str:
            return

        if await self._check_rate_limit(sid, user_id_str, "reaction.toggle"):
            return

        message_id_str = data.get("message_id")
        emoji = data.get("emoji")
        unicode_char = data.get("unicode_char", "")
        
        if not message_id_str or not emoji:
            await sio.emit("ws.error", {"message": "Missing message_id or emoji"}, to=sid)
            return

        message_id = uuid.UUID(message_id_str)
        user_id = uuid.UUID(user_id_str)
        
        async with SessionLocal() as db:
            # 1. Fetch message to check conversation membership
            msg_query = select(Message).where(Message.id == message_id)
            res_msg = await db.execute(msg_query)
            msg = res_msg.scalar_one_or_none()
            if not msg:
                await sio.emit("ws.error", {"message": "Message not found"}, to=sid)
                return

            # Check membership
            member_query = select(ConversationMember).where(
                and_(
                    ConversationMember.conversation_id == msg.conversation_id,
                    ConversationMember.user_id == user_id,
                    ConversationMember.left_at.is_(None)
                )
            )
            res_mem = await db.execute(member_query)
            if not res_mem.scalar_one_or_none():
                await sio.emit("ws.error", {"message": "User is not a member of this conversation"}, to=sid)
                return

            # 2. Check if reaction exists
            from app.models.message_reaction import MessageReaction
            react_query = select(MessageReaction).where(
                and_(
                    MessageReaction.message_id == message_id,
                    MessageReaction.user_id == user_id,
                    MessageReaction.reaction == emoji
                )
            )
            res_react = await db.execute(react_query)
            reaction = res_react.scalar_one_or_none()
            
            if reaction:
                await db.delete(reaction)
                is_active = False
            else:
                reaction = MessageReaction(
                    message_id=message_id,
                    user_id=user_id,
                    reaction=emoji,
                    unicode=unicode_char
                )
                db.add(reaction)
                is_active = True
                
            await db.commit()

            # 3. Calculate new total counts and list of user IDs who reacted with this emoji
            count_query = select(MessageReaction.user_id).where(
                and_(
                    MessageReaction.message_id == message_id,
                    MessageReaction.reaction == emoji
                )
            )
            res_count = await db.execute(count_query)
            user_ids = [str(uid) for uid in res_count.scalars().all()]
            
            # Broadcast update
            room = get_conversation_room(msg.conversation_id)
            await sio.emit("reaction.updated", {
                "message_id": message_id_str,
                "emoji": emoji,
                "is_active": is_active,
                "user_id": user_id_str,
                "count": len(user_ids),
                "users": user_ids
            }, to=room)

    async def handle_receipt_delivered(self, sid: str, data: Any) -> None:
        from app.websocket.manager import sio
        user_id_str = connection_manager.get_user_id(sid)
        if not user_id_str:
            return

        try:
            payload = WSReceiptUpdate(**data)
        except ValidationError:
            return

        user_id = uuid.UUID(user_id_str)
        async with SessionLocal() as db:
            receipt_service = ReceiptService(db)
            receipt = await receipt_service.update_receipt(payload.message_id, user_id, ReceiptStatus.DELIVERED)
            if receipt:
                sender_room = get_user_room(receipt.message.sender_id)
                await sio.emit("message.delivered", {
                    "message_id": str(payload.message_id),
                    "user_id": user_id_str
                }, to=sender_room)

    async def handle_receipt_read(self, sid: str, data: Any) -> None:
        from app.websocket.manager import sio
        user_id_str = connection_manager.get_user_id(sid)
        if not user_id_str:
            return

        try:
            payload = WSReceiptUpdate(**data)
        except ValidationError:
            return

        user_id = uuid.UUID(user_id_str)
        async with SessionLocal() as db:
            receipt_service = ReceiptService(db)
            receipt = await receipt_service.update_receipt(payload.message_id, user_id, ReceiptStatus.READ)
            if receipt:
                sender_room = get_user_room(receipt.message.sender_id)
                await sio.emit("message.read", {
                    "message_id": str(payload.message_id),
                    "user_id": user_id_str
                }, to=sender_room)

    async def handle_typing_start(self, sid: str, data: Any) -> None:
        user_id_str = connection_manager.get_user_id(sid)
        if not user_id_str:
            return

        if await self._check_rate_limit(sid, user_id_str, "typing.start"):
            return

        try:
            payload = WSTypingEvent(**data)
        except ValidationError:
            return

        user_id = uuid.UUID(user_id_str)
        await typing_manager.set_typing(payload.conversation_id, user_id, is_typing=True)

    async def handle_typing_stop(self, sid: str, data: Any) -> None:
        user_id_str = connection_manager.get_user_id(sid)
        if not user_id_str:
            return

        try:
            payload = WSTypingEvent(**data)
        except ValidationError:
            return

        user_id = uuid.UUID(user_id_str)
        await typing_manager.set_typing(payload.conversation_id, user_id, is_typing=False)

    async def handle_presence_update(self, sid: str, data: Any) -> None:
        user_id_str = connection_manager.get_user_id(sid)
        if not user_id_str:
            return

        try:
            payload = WSPresenceUpdate(**data)
        except ValidationError:
            return

        user_id = uuid.UUID(user_id_str)
        async with SessionLocal() as db:
            presence_service = PresenceService(db)
            last_seen_time = await presence_service.update_presence(user_id, payload.status)
            last_seen_iso = last_seen_time.isoformat() if last_seen_time else None
            
            await presence_manager.broadcast_presence_change(
                user_id, payload.status, last_seen=last_seen_iso, db_session=db
            )

# Instantiate websocket gateway singleton
ws_gateway = WebSocketGateway()

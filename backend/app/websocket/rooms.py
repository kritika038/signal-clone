import uuid
import logging
from typing import List
from app.websocket.connection_manager import connection_manager

logger = logging.getLogger(__name__)

def get_user_room(user_id: uuid.UUID) -> str:
    return f"user:{str(user_id)}"

def get_conversation_room(conversation_id: uuid.UUID) -> str:
    return f"conversation:{str(conversation_id)}"

async def join_user_room(sid: str, user_id: uuid.UUID) -> None:
    from app.websocket.manager import sio
    room = get_user_room(user_id)
    await sio.enter_room(sid, room)
    connection_manager.join_room(sid, room)
    logger.debug(f"[WS Rooms] Socket {sid} joined user room {room}")

async def leave_user_room(sid: str, user_id: uuid.UUID) -> None:
    from app.websocket.manager import sio
    room = get_user_room(user_id)
    await sio.leave_room(sid, room)
    connection_manager.leave_room(sid, room)
    logger.debug(f"[WS Rooms] Socket {sid} left user room {room}")

async def join_conversation_room(sid: str, conversation_id: uuid.UUID) -> None:
    from app.websocket.manager import sio
    room = get_conversation_room(conversation_id)
    await sio.enter_room(sid, room)
    connection_manager.join_room(sid, room)
    logger.debug(f"[WS Rooms] Socket {sid} joined conversation room {room}")

async def leave_conversation_room(sid: str, conversation_id: uuid.UUID) -> None:
    from app.websocket.manager import sio
    room = get_conversation_room(conversation_id)
    await sio.leave_room(sid, room)
    connection_manager.leave_room(sid, room)
    logger.debug(f"[WS Rooms] Socket {sid} left conversation room {room}")

async def sync_rooms_for_connection(sid: str, user_id: uuid.UUID, db_session) -> None:
    """
    Subscribes the connection to the user's private room and all active conversation rooms.
    """
    from sqlalchemy import select, and_
    from app.models.conversation_member import ConversationMember
    
    # 1. Join user private room
    await join_user_room(sid, user_id)
    
    # 2. Join active conversation rooms
    query = select(ConversationMember.conversation_id).where(
        and_(
            ConversationMember.user_id == user_id,
            ConversationMember.left_at.is_(None)
        )
    )
    res = await db_session.execute(query)
    conversation_ids = res.scalars().all()
    
    for conv_id in conversation_ids:
        await join_conversation_room(sid, conv_id)
    logger.info(f"[WS Rooms] Synced {len(conversation_ids)} conversation room(s) for user {user_id} on socket {sid}")

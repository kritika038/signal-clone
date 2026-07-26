import uuid
import logging
from app.websocket.rooms import get_conversation_room
from app.websocket.typing import InMemoryTypingStateManager

logger = logging.getLogger(__name__)

# Initialize the global typing state manager (3 seconds TTL)
typing_state_store = InMemoryTypingStateManager(ttl_seconds=3.0)

class TypingManager:
    async def set_typing(self, conversation_id: uuid.UUID, user_id: uuid.UUID, is_typing: bool) -> None:
        """
        Record typing status in the state store and broadcast changes to the conversation room.
        """
        from app.websocket.manager import sio
        conv_str = str(conversation_id)
        user_str = str(user_id)
        
        await typing_state_store.set_typing(conv_str, user_str, is_typing)
        
        # Broadcast typing status updates to the room members
        room = get_conversation_room(conversation_id)
        event = "typing.start" if is_typing else "typing.stop"
        payload = {
            "conversation_id": conv_str,
            "user_id": user_str
        }
        await sio.emit(event, payload, to=room)
        logger.debug(f"[WS Typing] Broadcasted {event} for user {user_str} inside conversation {conv_str}")

# Instantiate typing manager singleton
typing_manager = TypingManager()

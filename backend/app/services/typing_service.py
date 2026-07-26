import uuid
import logging
from typing import List

logger = logging.getLogger(__name__)

class TypingService:
    async def set_user_typing(self, conversation_id: uuid.UUID, user_id: uuid.UUID, is_typing: bool) -> None:
        """
        Processes a typing start/stop event by calling the socket typing manager.
        """
        from app.websocket.typing_manager import typing_manager
        await typing_manager.set_typing(conversation_id, user_id, is_typing)

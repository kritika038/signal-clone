import asyncio
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Set, Tuple

class TypingStateManager(ABC):
    """
    Abstract interface for managing typing presence state.
    Designed so that a Redis implementation can swap in without API changes.
    """
    @abstractmethod
    async def set_typing(self, conversation_id: str, user_id: str, is_typing: bool) -> None:
        """
        Record a user's typing state inside a conversation.
        """
        pass

    @abstractmethod
    async def get_typing_users(self, conversation_id: str) -> List[str]:
        """
        Get the list of active typing user IDs in a conversation.
        """
        pass

class InMemoryTypingStateManager(TypingStateManager):
    """
    In-memory TypingStateManager implementation.
    Automatically handles self-eviction of typing states after TTL (2-3 seconds).
    """
    def __init__(self, ttl_seconds: float = 3.0):
        self.ttl = ttl_seconds
        # Maps (conversation_id, user_id) -> expire_at timestamp
        self._states: Dict[Tuple[str, str], float] = {}

    async def set_typing(self, conversation_id: str, user_id: str, is_typing: bool) -> None:
        key = (conversation_id, user_id)
        if is_typing:
            self._states[key] = time.time() + self.ttl
        else:
            self._states.pop(key, None)

    async def get_typing_users(self, conversation_id: str) -> List[str]:
        now = time.time()
        active_users: List[str] = []
        expired_keys: List[Tuple[str, str]] = []

        # Iterate and evict expired records
        for key, expire_at in list(self._states.items()):
            conv_id, user_id = key
            if conv_id == conversation_id:
                if now < expire_at:
                    active_users.append(user_id)
                else:
                    expired_keys.append(key)
            elif now >= expire_at:
                expired_keys.append(key)

        for key in expired_keys:
            self._states.pop(key, None)

        return active_users

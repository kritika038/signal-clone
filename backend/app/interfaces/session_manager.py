from abc import ABC, abstractmethod
from typing import Optional, List
import uuid
from datetime import datetime
from app.models.user_session import UserSession

class SessionManager(ABC):
    """
    Interface for authentication session lifecycle management.
    Encapsulates token hashes, token rotations, and active sessions.
    """
    @abstractmethod
    async def create_session(
        self,
        user_id: uuid.UUID,
        refresh_token: str,
        device_name: Optional[str],
        device_type: Optional[str],
        ip_address: Optional[str],
        expires_at: datetime,
        session_id: Optional[uuid.UUID] = None
    ) -> UserSession:
        """
        Create a new persistent user session.
        """
        pass

    @abstractmethod
    async def rotate_session(
        self,
        session_id: uuid.UUID,
        old_token: str,
        new_token: str,
        new_expires_at: datetime
    ) -> UserSession:
        """
        Rotates a session's refresh token. Returns the updated session.
        If the old_token is reused, it constitutes a reuse attack and triggers session revocation.
        """
        pass

    @abstractmethod
    async def get_active_session(self, session_id: uuid.UUID) -> Optional[UserSession]:
        """
        Fetch active session by UUID.
        """
        pass

    @abstractmethod
    async def revoke_session(self, session_id: uuid.UUID) -> None:
        """
        Invalidate a session (logout).
        """
        pass

    @abstractmethod
    async def clean_expired_sessions(self) -> None:
        """
        Deletes all expired sessions.
        """
        pass

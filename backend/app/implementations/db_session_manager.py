from datetime import datetime, timezone
import uuid
from typing import Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.interfaces.session_manager import SessionManager
from app.models.user_session import UserSession
from app.core.security import hash_token, verify_token_hash

class DBSessionManager(SessionManager):
    """
    SQLAlchemy-backed SessionManager implementation.
    Manages active tokens, rotation, hashing, and token reuse attack detection.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

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
        token_hash = hash_token(refresh_token)
        session = UserSession(
            id=session_id or uuid.uuid4(),
            user_id=user_id,
            refresh_token_hash=token_hash,
            device_name=device_name,
            device_type=device_type,
            ip_address=ip_address,
            expires_at=expires_at,
            last_activity=datetime.now(timezone.utc)
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def rotate_session(
        self,
        session_id: uuid.UUID,
        old_token: str,
        new_token: str,
        new_expires_at: datetime
    ) -> UserSession:
        """
        Validates the old refresh token hash, updates it to the new token's hash.
        If a reuse attack is detected (old token hash doesn't match current hash),
        the session is instantly revoked to prevent malicious access.
        """
        session = await self.get_active_session(session_id)
        if not session:
            raise ValueError("Session not found or expired")

        # Verify token hash (constant-time check)
        if not verify_token_hash(old_token, session.refresh_token_hash):
            # Reuse attack or malicious token rotation attempt! Revoke the session.
            await self.revoke_session(session_id)
            raise ValueError("Security Violation: Token reuse detected. Session revoked.")

        # Invalidate old token by saving hash of new token
        session.refresh_token_hash = hash_token(new_token)
        session.expires_at = new_expires_at
        session.last_activity = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_active_session(self, session_id: uuid.UUID) -> Optional[UserSession]:
        query = select(UserSession).where(
            UserSession.id == session_id,
            UserSession.expires_at > datetime.now(timezone.utc)
        )
        res = await self.db.execute(query)
        return res.scalar_one_or_none()

    async def revoke_session(self, session_id: uuid.UUID) -> None:
        query = delete(UserSession).where(UserSession.id == session_id)
        await self.db.execute(query)
        await self.db.commit()

    async def clean_expired_sessions(self) -> None:
        query = delete(UserSession).where(UserSession.expires_at <= datetime.now(timezone.utc))
        await self.db.execute(query)
        await self.db.commit()

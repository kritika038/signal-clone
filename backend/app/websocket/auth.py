import logging
import uuid
from typing import Dict, Any, Optional, Tuple
from jose import jwt, JWTError

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User
from app.models.user_session import UserSession
from app.implementations.db_session_manager import DBSessionManager
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

async def authenticate_socket(auth: Optional[Dict[str, Any]]) -> Optional[Tuple[User, UserSession]]:
    """
    Validates the connection auth payload containing a JWT token.
    Enforces check for user validity, deleted users, and revoked sessions.
    Returns (User, UserSession) if successful, otherwise None.
    """
    if not auth or "token" not in auth:
        logger.warning("[WS Auth] Handshake rejected: missing auth credentials")
        return None

    auth_token = auth["token"]
    token = auth_token
    if auth_token.lower().startswith("bearer "):
        token = auth_token[7:]

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str = payload.get("sub")
        session_id_str = payload.get("session_id")
        
        if not user_id_str or not session_id_str:
            logger.warning("[WS Auth] Handshake rejected: missing claims in JWT payload")
            return None
            
        user_id = uuid.UUID(user_id_str)
        session_id = uuid.UUID(session_id_str)
    except (JWTError, ValueError) as e:
        logger.warning(f"[WS Auth] Handshake rejected: JWT decoding failed - {str(e)}")
        return None

    # Resolve database session since WebSocket runs outside route scope
    async with SessionLocal() as db:
        session_manager = DBSessionManager(db)
        user_service = UserService(db)

        # Check session status
        session = await session_manager.get_active_session(session_id)
        if not session:
            logger.warning(f"[WS Auth] Handshake rejected: session {session_id} is expired or revoked")
            return None

        # Check user status
        user = await user_service.get_by_id(user_id)
        if not user:
            logger.warning(f"[WS Auth] Handshake rejected: user {user_id} not found")
            return None

        if user.deleted_at is not None:
            logger.warning(f"[WS Auth] Handshake rejected: user {user_id} is deleted")
            return None

        # Detach instance from session before closing database context,
        # so it can be safely used in socket connection state context.
        db.expunge(user)
        db.expunge(session)
        
        return user, session

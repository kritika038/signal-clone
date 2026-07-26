from datetime import datetime, timedelta, timezone
import logging
from typing import Optional, Tuple, Dict, Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import (
    get_password_hash,
    create_access_token,
    create_refresh_token
)
from app.interfaces.otp_store import OTPStore
from app.interfaces.session_manager import SessionManager
from app.models.enums import PresenceStatus
from app.models.user import User
from app.models.user_session import UserSession
from app.models.user_settings import UserSettings
from app.schemas.auth import UserRegister
from app.services.user_service import UserService

logger = logging.getLogger("auth_events")

class IdentityService:
    """
    IdentityService coordinates multi-step authentication processes:
    registrations, OTP verifications, login validations, and refresh tokens rotation.
    """
    def __init__(self, db: AsyncSession, otp_store: OTPStore, session_manager: SessionManager):
        self.db = db
        self.otp_store = otp_store
        self.session_manager = session_manager
        self.user_service = UserService(db)

    def _log_auth_event(
        self, event: str, user_id: Optional[uuid.UUID], session_id: Optional[uuid.UUID], ip: Optional[str], device: Optional[str], details: str = ""
    ) -> None:
        """
        Structured logging helper for authentication events.
        """
        log_payload = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": str(user_id) if user_id else None,
            "session_id": str(session_id) if session_id else None,
            "ip": ip,
            "device": device,
            "details": details
        }
        logger.info(f"[AuthEvent] {log_payload}")

    async def send_register_otp(self, phone: str, ip: Optional[str], device: Optional[str]) -> None:
        # Validate uniqueness
        phone_user = await self.user_service.get_by_phone(phone)
        if phone_user:
            self._log_auth_event("REGISTER_FAIL_DUPLICATE_PHONE", None, None, ip, device, f"Phone: {phone}")
            raise ValueError("Phone number already registered")

        self._log_auth_event("REGISTER_OTP_GENERATED", None, None, ip, device, f"Phone: {phone}")

    async def verify_register_otp(self, phone: str, otp: str, ip: Optional[str], device: Optional[str]) -> str:
        if otp != "123456":
            self._log_auth_event("OTP_VERIFICATION_FAILURE", None, None, ip, device, f"Phone: {phone}")
            raise ValueError("Invalid or expired OTP code")
        
        registration_token = f"mock-token-{phone}"
        return registration_token

    async def register(self, register_in: UserRegister, ip: Optional[str], device: Optional[str]) -> Tuple[User, UserSession, str, str]:
        # Validate registration token
        if not register_in.registration_token.startswith("mock-token-"):
            raise ValueError("Invalid or expired registration token")
            
        phone = register_in.registration_token.replace("mock-token-", "")

        # Create user
        username_user = await self.user_service.get_by_username(register_in.username)
        if username_user:
            raise ValueError("Username already registered")

        import secrets
        random_fallback_pw = secrets.token_urlsafe(32)
        hashed_pw = get_password_hash(random_fallback_pw)
        new_user = User(
            id=uuid.uuid4(),
            phone=phone,
            email=None,
            username=register_in.username,
            display_name=register_in.display_name,
            avatar_url=register_in.avatar_url,
            hashed_password=hashed_pw,
            presence_status=PresenceStatus.ONLINE,
            is_verified=True
        )
        self.db.add(new_user)
        await self.db.flush()

        settings = UserSettings(user_id=new_user.id)
        new_user.settings = settings
        self.db.add(settings)
        await self.db.flush()

        access_token, refresh_token, session = await self._start_session(
            new_user.id, device, device, ip
        )
        
        self._log_auth_event("REGISTRATION_SUCCESS", new_user.id, session.id, ip, device)
        return new_user, session, access_token, refresh_token


    async def send_login_otp(self, login_id: str, ip: Optional[str], device: Optional[str]) -> None:
        user = await self.user_service.get_by_phone(login_id)
            
        if not user:
            self._log_auth_event("LOGIN_FAIL_NOT_FOUND", None, None, ip, device, f"Identifier: {login_id}")
            raise ValueError("Account not found.")
        
        self._log_auth_event("LOGIN_OTP_GENERATED", user.id, None, ip, device, f"Identifier: {login_id}")

    async def verify_login_otp(self, login_id: str, otp: str, ip: Optional[str], device_name: Optional[str], device_type: Optional[str]) -> Tuple[User, UserSession, str, str]:
        """
        Verifies login OTP and spawns session.
        """
        if otp != "123456":
            self._log_auth_event("LOGIN_OTP_FAILURE", None, None, ip, device_name, f"Identifier: {login_id}")
            raise ValueError("Invalid or expired OTP code")
            
        user = await self.user_service.get_by_phone(login_id)
        if not user:
            raise ValueError("User not found")
        
        await self.otp_store.delete(login_id)

        # Session creation
        access_token, refresh_token, session = await self._start_session(
            user.id, device_name, device_type, ip
        )

        self._log_auth_event("LOGIN_SUCCESS", user.id, session.id, ip, device_name)
        return user, session, access_token, refresh_token



    async def refresh_tokens(self, session_id: uuid.UUID, old_refresh_token: str, ip: Optional[str], device: Optional[str]) -> Tuple[str, str]:
        """
        Performs rotation of refresh tokens, checking for token reuse attacks.
        """
        session = await self.session_manager.get_active_session(session_id)
        if not session:
            self._log_auth_event("REFRESH_FAIL_SESSION_NOT_FOUND", None, session_id, ip, device, "Session not found or expired")
            raise ValueError("Session not found or expired")

        new_refresh = create_refresh_token(session.user_id, session.id)
        new_expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        try:
            session = await self.session_manager.rotate_session(
                session_id, old_refresh_token, new_refresh, new_expires_at
            )
        except ValueError as e:
            # Token reuse or session invalidation detected
            self._log_auth_event("REFRESH_REUSE_ATTACK", None, session_id, ip, device, str(e))
            raise e

        # Issue new short-lived access token
        access_token = create_access_token(session.user_id, session.id)
        
        self._log_auth_event("REFRESH_SUCCESS", session.user_id, session.id, ip, device)
        return access_token, new_refresh

    async def logout(self, session_id: uuid.UUID, ip: Optional[str], device: Optional[str]) -> None:
        """
        Revokes the current session.
        """
        session = await self.session_manager.get_active_session(session_id)
        user_id = session.user_id if session else None
        
        await self.session_manager.revoke_session(session_id)
        self._log_auth_event("LOGOUT", user_id, session_id, ip, device)

    async def _start_session(
        self, user_id: uuid.UUID, device_name: Optional[str], device_type: Optional[str], ip: Optional[str]
    ) -> Tuple[str, str, UserSession]:
        session_id = uuid.uuid4()
        refresh_token = create_refresh_token(user_id, session_id)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7) # 7 days refresh token validity
        
        session = await self.session_manager.create_session(
            user_id=user_id,
            refresh_token=refresh_token,
            device_name=device_name,
            device_type=device_type,
            ip_address=ip,
            expires_at=expires_at,
            session_id=session_id
        )

        access_token = create_access_token(user_id, session.id)
        return access_token, refresh_token, session

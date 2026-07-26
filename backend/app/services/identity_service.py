from datetime import datetime, timedelta, timezone
import logging
from typing import Optional, Tuple, Dict, Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token
)
from app.interfaces.otp_store import OTPStore
from app.interfaces.session_manager import SessionManager
from app.models.enums import PresenceStatus
from app.models.user import User
from app.models.user_session import UserSession
from app.models.user_settings import UserSettings
from app.schemas.auth import UserRegister, UserLogin
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

    async def register(self, register_in: UserRegister, ip: Optional[str], device: Optional[str]) -> str:
        """
        Initiates user registration. Validates phone/username uniqueness and caches request.
        Always registers mock OTP code '123456' for 5 minutes.
        """
        # Validate uniqueness
        phone_user = await self.user_service.get_by_phone(register_in.phone)
        if phone_user:
            self._log_auth_event("REGISTER_FAIL_DUPLICATE_PHONE", None, None, ip, device, f"Phone: {register_in.phone}")
            raise ValueError("Phone number already registered")

        username_user = await self.user_service.get_by_username(register_in.username)
        if username_user:
            self._log_auth_event("REGISTER_FAIL_DUPLICATE_USERNAME", None, None, ip, device, f"Username: {register_in.username}")
            raise ValueError("Username already registered")

        # Cache payload with mock OTP
        mock_otp = "123456"
        payload = {
            "phone": register_in.phone,
            "username": register_in.username,
            "password": register_in.password,
            "display_name": register_in.display_name
        }
        await self.otp_store.create(register_in.phone, payload, mock_otp, ttl_seconds=300)
        
        self._log_auth_event("REGISTER_OTP_GENERATED", None, None, ip, device, f"Phone: {register_in.phone}")
        return mock_otp

    async def verify_otp(self, phone: str, otp: str, ip: Optional[str], device_name: Optional[str], device_type: Optional[str]) -> Tuple[User, UserSession, str, str]:
        """
        Verifies the registration OTP, hashes password, saves the user record,
        creates settings, and spawns an active session.
        """
        payload = await self.otp_store.verify(phone, otp)
        if not payload:
            self._log_auth_event("OTP_VERIFICATION_FAILURE", None, None, ip, device_name, f"Phone: {phone}")
            raise ValueError("Invalid or expired OTP code")

        # Commit User creation
        hashed_pw = get_password_hash(payload["password"])
        new_user = User(
            id=uuid.uuid4(),
            phone=payload["phone"],
            username=payload["username"],
            display_name=payload["display_name"],
            hashed_password=hashed_pw,
            presence_status=PresenceStatus.ONLINE,
            is_verified=True
        )
        self.db.add(new_user)
        await self.db.flush()

        # Commit User settings
        settings = UserSettings(user_id=new_user.id)
        new_user.settings = settings
        self.db.add(settings)
        await self.db.flush()

        # Delete cached registration
        await self.otp_store.delete(phone)

        # Generate tokens and Session
        access_token, refresh_token, session = await self._start_session(
            new_user.id, device_name, device_type, ip
        )
        
        self._log_auth_event("OTP_VERIFICATION_SUCCESS", new_user.id, session.id, ip, device_name)
        return new_user, session, access_token, refresh_token

    async def login(self, login_in: UserLogin, ip: Optional[str], device_name: Optional[str], device_type: Optional[str]) -> Tuple[User, UserSession, str, str]:
        """
        Validates login identifiers against phone or username, verifies password, and spawns session.
        """
        # Lookup either phone or username
        user = None
        if login_in.login_id.startswith("+") or login_in.login_id.isdigit():
            user = await self.user_service.get_by_phone(login_in.login_id)
        if not user:
            user = await self.user_service.get_by_username(login_in.login_id)

        if not user or not verify_password(login_in.password, user.hashed_password):
            self._log_auth_event("LOGIN_FAILURE", None, None, ip, device_name, f"Identifier: {login_in.login_id}")
            raise ValueError("Invalid credentials")

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

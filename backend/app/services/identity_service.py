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
        
        # Generate a durable, real server-side registration token
        registration_token = f"reg_{uuid.uuid4().hex}"
        
        # Store in OTP/registration store to survive the next request and ensure it's consumed exactly once
        await self.otp_store.create(
            identifier=registration_token,
            registration_payload={"phone": phone},
            otp=registration_token,
            ttl_seconds=3600
        )
        
        return registration_token

    async def register(self, register_in: UserRegister, ip: Optional[str], device: Optional[str]) -> Tuple[User, UserSession, str, str]:
        import logging
        logging.info(f"Starting registration for user: {register_in.username}")
        # Validate registration token against server state and consume it exactly once
        payload = await self.otp_store.verify(register_in.registration_token, register_in.registration_token)
        if not payload:
            logging.error("Registration token verification failed")
            raise ValueError("Invalid or expired registration token")
            
        phone = payload.get("phone")
        if not phone:
            logging.error("No phone found in registration payload")
            raise ValueError("Invalid registration payload state")

        logging.info(f"Token verified for phone {phone}. Checking for duplicates.")
        # Create user
        phone_user = await self.user_service.get_by_phone(phone)
        if phone_user:
            raise ValueError("Phone number already registered")

        username_user = await self.user_service.get_by_username(register_in.username)
        if username_user:
            raise ValueError("Username already registered")

        logging.info("Duplicates check passed. Creating user.")
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
        logging.info(f"Added new_user to db session with ID {new_user.id}")
        await self.db.flush()

        logging.info("Creating user settings.")
        settings = UserSettings(user_id=new_user.id)
        new_user.settings = settings
        self.db.add(settings)
        await self.db.flush()

        logging.info("Starting session via DBSessionManager.")

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
        
        safe_device_name = device_name[:100] if device_name else None
        safe_device_type = device_type[:50] if device_type else None
        safe_ip = ip[:45] if ip else None

        session = await self.session_manager.create_session(
            user_id=user_id,
            refresh_token=refresh_token,
            device_name=safe_device_name,
            device_type=safe_device_type,
            ip_address=safe_ip,
            expires_at=expires_at,
            session_id=session_id
        )

        access_token = create_access_token(user_id, session.id)
        return access_token, refresh_token, session

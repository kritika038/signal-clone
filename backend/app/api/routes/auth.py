import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_async_db,
    get_session_manager,
    get_current_user,
    get_current_user_and_session,
    rate_limit_register,
    rate_limit_login,
    rate_limit_verify_otp,
    rate_limit_refresh,
    get_client_ip
)
from app.core.exceptions import APIException
from app.implementations.db_session_manager import DBSessionManager
from app.models.user import User
from app.models.user_session import UserSession

from app.services.identity_service import IdentityService
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])

from app.implementations.db_otp_store import DatabaseOTPStore

def get_identity_service(
    db: AsyncSession = Depends(get_async_db),
    session_manager: DBSessionManager = Depends(get_session_manager)
) -> IdentityService:
    otp_store = DatabaseOTPStore(db)
    return IdentityService(db, otp_store, session_manager)

# Helper to format User model representation safely
def format_user_data(user: User) -> dict:
    from sqlalchemy import inspect
    state = inspect(user)
    settings_data = None
    if "settings" not in state.unloaded and user.settings is not None:
        settings_data = {
            "theme": user.settings.theme,
            "language": user.settings.language,
            "privacy_last_seen": user.settings.privacy_last_seen,
            "privacy_profile_photo": user.settings.privacy_profile_photo,
            "privacy_read_receipts": user.settings.privacy_read_receipts,
            "privacy_typing_indicator": user.settings.privacy_typing_indicator,
            "notifications_enabled": user.settings.notifications_enabled,
            "auto_download_media": user.settings.auto_download_media,
            "default_disappearing_timer": user.settings.default_disappearing_timer,
            "font_size": user.settings.font_size,
        }
    
    return {
        "id": str(user.id),
        "phone": user.phone,
        "username": user.username,
        "display_name": user.display_name,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "presence_status": user.presence_status.value if user.presence_status else None,
        "last_seen": user.last_seen.isoformat() if user.last_seen else None,
        "is_verified": user.is_verified,
        "settings": settings_data
    }

from app.schemas.auth import (
    UserRegister,
    RegisterVerifyOTP,
    RegisterSendOTP,
    LoginVerifyOTP,
    LoginSendOTP,
    TokenRefreshRequest,
    TokenResponse
)


@router.post("/register/send-otp", status_code=status.HTTP_200_OK, dependencies=[Depends(rate_limit_register)])
async def send_register_otp(
    send_in: RegisterSendOTP,
    request: Request,
    service: IdentityService = Depends(get_identity_service)
):
    ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")
    try:
        await service.send_register_otp(send_in.phone, send_in.email, ip, user_agent)
        return {
            "success": True,
            "data": {
                "message": "OTP code sent to your email successfully."
            }
        }
    except ValueError as e:
        raise APIException(status.HTTP_400_BAD_REQUEST, "OTP_SEND_FAILED", str(e))

@router.post("/register/verify", status_code=status.HTTP_200_OK, dependencies=[Depends(rate_limit_verify_otp)])
async def verify_register_otp(
    verify_in: RegisterVerifyOTP,
    request: Request,
    service: IdentityService = Depends(get_identity_service)
):
    ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")
    try:
        registration_token = await service.verify_register_otp(
            verify_in.phone, verify_in.otp, ip, user_agent
        )
        return {
            "success": True,
            "data": {
                "registration_token": registration_token,
                "message": "OTP verified successfully. Proceed to profile setup."
            }
        }
    except ValueError as e:
        raise APIException(status.HTTP_400_BAD_REQUEST, "OTP_VERIFICATION_FAILED", str(e))

@router.post("/register", status_code=status.HTTP_200_OK, dependencies=[Depends(rate_limit_register)])
async def register(
    register_in: UserRegister,
    request: Request,
    service: IdentityService = Depends(get_identity_service)
):
    ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")
    try:
        user, session, access_token, refresh_token = await service.register(register_in, ip, user_agent)
        return {
            "success": True,
            "data": {
                "user": format_user_data(user),
                "session_id": str(session.id),
                "tokens": {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "bearer"
                }
            }
        }
    except ValueError as e:
        raise APIException(status.HTTP_400_BAD_REQUEST, "REGISTRATION_FAILED", str(e))




@router.post("/login/send-otp", status_code=status.HTTP_200_OK, dependencies=[Depends(rate_limit_login)])
async def send_login_otp(
    send_in: LoginSendOTP,
    request: Request,
    service: IdentityService = Depends(get_identity_service)
):
    ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")
    try:
        await service.send_login_otp(send_in.login_id, ip, user_agent)
        return {
            "success": True,
            "data": {
                "message": "OTP code sent to your email successfully."
            }
        }
    except ValueError as e:
        raise APIException(status.HTTP_400_BAD_REQUEST, "LOGIN_OTP_SEND_FAILED", str(e))

@router.post("/login/verify", status_code=status.HTTP_200_OK, dependencies=[Depends(rate_limit_login)])
async def verify_login_otp(
    login_in: LoginVerifyOTP,
    request: Request,
    service: IdentityService = Depends(get_identity_service)
):
    ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")
    try:
        user, session, access_token, refresh_token = await service.verify_login_otp(
            login_in.login_id, login_in.otp, ip, user_agent, "DESKTOP"
        )
        return {
            "success": True,
            "data": {
                "user": format_user_data(user),
                "session_id": str(session.id),
                "tokens": {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "bearer"
                }
            }
        }
    except ValueError as e:
        raise APIException(status.HTTP_401_UNAUTHORIZED, "INVALID_CREDENTIALS", str(e))

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    user_and_session: tuple[User, UserSession] = Depends(get_current_user_and_session),
    service: IdentityService = Depends(get_identity_service)
):
    _, session = user_and_session
    ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")
    await service.logout(session.id, ip, user_agent)
    return {
        "success": True,
        "data": {
            "message": "Successfully logged out from active session."
        }
    }

@router.post("/refresh", status_code=status.HTTP_200_OK, dependencies=[Depends(rate_limit_refresh)])
async def refresh(
    refresh_in: TokenRefreshRequest,
    request: Request,
    service: IdentityService = Depends(get_identity_service)
):
    ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")
    
    # Pre-parse token to extract session_id claim without signature validation first
    # This is safe because verify_session does cryptographic verification on the db token hash
    try:
        from jose import jwt
        from app.core.config import settings
        # We decode unverified to extract session_id
        unverified_claims = jwt.get_unverified_claims(refresh_in.refresh_token)
        session_id_str = unverified_claims.get("session_id")
        if not session_id_str:
            raise ValueError()
        session_id = uuid.UUID(session_id_str)
    except Exception:
        raise APIException(status.HTTP_401_UNAUTHORIZED, "INVALID_REFRESH_TOKEN", "Malformed or invalid refresh token")

    try:
        access_token, new_refresh_token = await service.refresh_tokens(
            session_id, refresh_in.refresh_token, ip, user_agent
        )
        return {
            "success": True,
            "data": {
                "access_token": access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer"
            }
        }
    except ValueError as e:
        # Raises 401 on expired session or token reuse violation
        raise APIException(status.HTTP_401_UNAUTHORIZED, "INVALID_REFRESH_TOKEN", str(e))

@router.get("/me", status_code=status.HTTP_200_OK)
async def me(user: User = Depends(get_current_user)):
    return {
        "success": True,
        "data": format_user_data(user)
    }



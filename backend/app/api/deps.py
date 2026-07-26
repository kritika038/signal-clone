from __future__ import annotations

import uuid
from typing import Optional

from fastapi import Depends, Request, status
from fastapi.security import APIKeyHeader
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import APIException
from app.db.session import get_async_db
from app.implementations.db_session_manager import DBSessionManager
from app.models.user import User
from app.models.user_session import UserSession
from app.services.runtime import runtime_services
from app.services.user_service import UserService

token_header = APIKeyHeader(name="Authorization", auto_error=False)

global_rate_limiter = runtime_services.rate_limiter


async def get_session_manager(db: AsyncSession = Depends(get_async_db)) -> DBSessionManager:
    return DBSessionManager(db)


async def get_current_user_and_session(
    authorization: Optional[str] = Depends(token_header),
    db: AsyncSession = Depends(get_async_db),
    session_manager: DBSessionManager = Depends(get_session_manager),
) -> tuple[User, UserSession]:
    if not authorization:
        raise APIException(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", "Authorization token is missing")

    token = authorization[7:] if authorization.lower().startswith("bearer ") else authorization
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = uuid.UUID(payload["sub"])
        session_id = uuid.UUID(payload["session_id"])
    except (JWTError, KeyError, ValueError):
        raise APIException(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", "Invalid authentication token")

    session = await session_manager.get_active_session(session_id)
    if not session:
        raise APIException(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", "Session has expired or been logged out")

    user = await UserService(db).get_by_id(user_id)
    if not user or user.deleted_at is not None:
        raise APIException(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", "User account not found")

    return user, session


async def get_current_user(
    user_and_session: tuple[User, UserSession] = Depends(get_current_user_and_session),
) -> User:
    return user_and_session[0]


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown-ip"


async def _rate_limit(request: Request, suffix: str, limit: int, window_seconds: int, message: str) -> None:
    ip = get_client_ip(request)
    key = f"{ip}:{suffix}"
    if await global_rate_limiter.is_rate_limited(key, limit=limit, window_seconds=window_seconds):
        raise APIException(status.HTTP_429_TOO_MANY_REQUESTS, "RATE_LIMIT_EXCEEDED", message)


async def rate_limit_register(request: Request) -> None:
    await _rate_limit(
        request,
        "register",
        settings.AUTH_RATE_LIMIT_REGISTER,
        900,
        "Register attempt limit exceeded. Retry in 15 minutes.",
    )


async def rate_limit_login(request: Request) -> None:
    await _rate_limit(
        request,
        "login",
        settings.AUTH_RATE_LIMIT_LOGIN,
        900,
        "Login attempt limit exceeded. Retry in 15 minutes.",
    )


async def rate_limit_verify_otp(request: Request) -> None:
    await _rate_limit(
        request,
        "verify-otp",
        settings.AUTH_RATE_LIMIT_VERIFY_OTP,
        300,
        "OTP verification limit exceeded. Retry in 5 minutes.",
    )


async def rate_limit_refresh(request: Request) -> None:
    await _rate_limit(
        request,
        "refresh",
        settings.AUTH_RATE_LIMIT_REFRESH,
        3600,
        "Token refresh limit exceeded. Retry in 1 hour.",
    )

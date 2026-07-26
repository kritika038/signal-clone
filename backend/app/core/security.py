from datetime import datetime, timedelta, timezone
from typing import Any, Union
import hashlib
import hmac
import uuid
from jose import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from app.core.config import settings

ph = PasswordHasher()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify plain password against stored Argon2 hash using constant-time verification.
    """
    try:
        return ph.verify(hashed_password, plain_password)
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """
    Generate Argon2 password hash.
    """
    return ph.hash(password)

def hash_token(token: str) -> str:
    """
    Generates SHA-256 hash of high-entropy tokens (like refresh tokens).
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def verify_token_hash(token: str, token_hash: str) -> bool:
    """
    Constant-time comparison verifying refresh tokens.
    """
    target = hash_token(token)
    return hmac.compare_digest(target, token_hash)

def create_access_token(
    subject: Union[str, Any], session_id: Union[str, Any], expires_delta: Union[timedelta, None] = None
) -> str:
    """
    Generates JWT access token with expiration and session context.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)  # 15 minutes standard expiry
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "session_id": str(session_id),
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4())
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(subject: Any, session_id: Any) -> str:
    """
    Generates a 7-day JWT refresh token with session context.
    """
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "session_id": str(session_id),
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4())
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

import time
from typing import Dict, Any, Optional
from app.interfaces.otp_store import OTPStore

class InMemoryOTPStore(OTPStore):
    """
    In-memory self-evicting OTP store.
    Matches phone numbers to temporary registration payloads with expiration.
    """
    def __init__(self):
        # Maps phone -> {"payload": dict, "otp": str, "expire_at": float}
        self._store: Dict[str, Dict[str, Any]] = {}

    async def create(self, phone: str, registration_payload: Dict[str, Any], otp: str, ttl_seconds: int = 300) -> None:
        self._store[phone] = {
            "payload": registration_payload,
            "otp": otp,
            "expire_at": time.time() + ttl_seconds
        }

    async def verify(self, phone: str, otp: str) -> Optional[Dict[str, Any]]:
        record = self._store.get(phone)
        if not record:
            return None
        
        # Check expiry
        if time.time() > record["expire_at"]:
            self._store.pop(phone, None)
            return None

        # Check code
        if record["otp"] == otp:
            return record["payload"]
        
        return None

    async def delete(self, phone: str) -> None:
        self._store.pop(phone, None)

    async def cleanup_expired(self) -> None:
        now = time.time()
        expired_keys = [k for k, v in self._store.items() if now > v["expire_at"]]
        for k in expired_keys:
            self._store.pop(k, None)

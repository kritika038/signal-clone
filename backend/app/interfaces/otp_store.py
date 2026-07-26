from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class OTPStore(ABC):
    """
    Interface for transient OTP code storage.
    Allows swappable implementations (InMemory, Redis) without changing service layers.
    """
    @abstractmethod
    async def create(self, phone: str, registration_payload: Dict[str, Any], otp: str, ttl_seconds: int = 300) -> None:
        """
        Store a pending registration payload under a phone number with an OTP and TTL.
        """
        pass

    @abstractmethod
    async def verify(self, phone: str, otp: str) -> Optional[Dict[str, Any]]:
        """
        Verify the OTP for a phone number. Returns the stored payload if verified, else None.
        """
        pass

    @abstractmethod
    async def delete(self, phone: str) -> None:
        """
        Delete the OTP and associated payload.
        """
        pass

    @abstractmethod
    async def cleanup_expired(self) -> None:
        """
        Garbage collect all expired OTP requests.
        """
        pass

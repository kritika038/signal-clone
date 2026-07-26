from abc import ABC, abstractmethod

class RateLimiter(ABC):
    """
    Interface for rate limiting controls.
    Supports in-memory sliding window or Redis replacement.
    """
    @abstractmethod
    async def is_rate_limited(self, key: str, limit: int, window_seconds: int) -> bool:
        """
        Check if the key has exceeded the request limit within the window.
        Returns True if rate limited (blocked), otherwise False.
        """
        pass

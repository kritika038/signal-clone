import time
from typing import Dict, List
from app.interfaces.rate_limiter import RateLimiter

class InMemorySlidingWindowRateLimiter(RateLimiter):
    """
    Sliding window in-memory rate limiter.
    Easily swappable with a Redis implementation.
    """
    def __init__(self):
        # Maps key -> list of request timestamps
        self._requests: Dict[str, List[float]] = {}

    async def is_rate_limited(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.time()
        cutoff = now - window_seconds
        
        # Initialize or retrieve timestamps
        timestamps = self._requests.setdefault(key, [])
        
        # Evict outdated timestamps (outside the window)
        timestamps = [t for t in timestamps if t > cutoff]
        self._requests[key] = timestamps
        
        # Check limit
        if len(timestamps) >= limit:
            return True
            
        # Register current request
        timestamps.append(now)
        return False

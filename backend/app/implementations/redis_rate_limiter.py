from __future__ import annotations

import time

from app.interfaces.rate_limiter import RateLimiter

try:
    from redis.asyncio import Redis
except ImportError:  # pragma: no cover
    Redis = None


class RedisRateLimiter(RateLimiter):
    def __init__(self, redis_url: str):
        if Redis is None:
            raise RuntimeError("redis package is required for RedisRateLimiter")
        self._redis = Redis.from_url(redis_url, encoding="utf-8", decode_responses=True)

    async def is_rate_limited(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.time()
        window_key = f"rate_limit:{key}"
        try:
            pipeline = self._redis.pipeline()
            pipeline.zremrangebyscore(window_key, 0, now - window_seconds)
            pipeline.zcard(window_key)
            pipeline.zadd(window_key, {str(now): now})
            pipeline.expire(window_key, window_seconds)
            _, current_count, _, _ = await pipeline.execute()
            return int(current_count) >= limit
        except Exception:
            return False

    async def ping(self) -> bool:
        return bool(await self._redis.ping())

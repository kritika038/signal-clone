from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.core.config import NotificationBackend, RedisBackend, SchedulerBackend, StorageBackend, settings
from app.implementations.in_memory_rate_limiter import InMemorySlidingWindowRateLimiter
from app.implementations.redis_rate_limiter import RedisRateLimiter
from app.services.notification_provider import (
    APNsProvider,
    FirebaseProvider,
    MockNotificationProvider,
    NotificationProvider,
)
from app.services.scheduler import AsyncScheduler, CeleryScheduler, DramatiqScheduler, Scheduler
from app.services.storage_provider import (
    CloudflareR2StorageProvider,
    LocalStorageProvider,
    MinIOStorageProvider,
    S3StorageProvider,
    StorageProvider,
)

logger = logging.getLogger(__name__)


@dataclass
class RuntimeServices:
    rate_limiter: Any
    storage_provider: StorageProvider
    scheduler: Scheduler
    notification_provider: NotificationProvider

    async def check_redis(self) -> dict[str, object]:
        if settings.REDIS_BACKEND == RedisBackend.MEMORY:
            return {"ok": True, "backend": "memory"}
        checker = getattr(self.rate_limiter, "ping", None)
        if checker is None:
            return {"ok": False, "backend": "redis", "error": "ping unavailable"}
        try:
            ok = await checker()
            return {"ok": ok, "backend": "redis"}
        except Exception as exc:
            return {"ok": False, "backend": "redis", "error": str(exc)}


def build_storage_provider() -> StorageProvider:
    if settings.STORAGE_BACKEND == StorageBackend.MINIO:
        return MinIOStorageProvider()
    if settings.STORAGE_BACKEND == StorageBackend.S3:
        return S3StorageProvider()
    if settings.STORAGE_BACKEND == StorageBackend.CLOUDFLARE_R2:
        return CloudflareR2StorageProvider()
    return LocalStorageProvider()


def build_scheduler() -> Scheduler:
    if settings.SCHEDULER_BACKEND == SchedulerBackend.CELERY:
        return CeleryScheduler()
    if settings.SCHEDULER_BACKEND == SchedulerBackend.DRAMATIQ:
        return DramatiqScheduler()
    return AsyncScheduler()


def build_notification_provider() -> NotificationProvider:
    if settings.NOTIFICATION_BACKEND == NotificationBackend.FIREBASE:
        return FirebaseProvider()
    if settings.NOTIFICATION_BACKEND == NotificationBackend.APNS:
        return APNsProvider()
    return MockNotificationProvider()


def build_rate_limiter() -> Any:
    if settings.REDIS_BACKEND == RedisBackend.REDIS:
        return RedisRateLimiter(settings.REDIS_URL)
    return InMemorySlidingWindowRateLimiter()


runtime_services = RuntimeServices(
    rate_limiter=build_rate_limiter(),
    storage_provider=build_storage_provider(),
    scheduler=build_scheduler(),
    notification_provider=build_notification_provider(),
)

from __future__ import annotations

from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.runtime import runtime_services


class HealthService:
    async def live(self) -> dict[str, str]:
        return {"status": "alive", "environment": settings.ENVIRONMENT.value}

    async def ready(self) -> dict[str, object]:
        database = await self._check_database()
        redis = await runtime_services.check_redis()
        storage = runtime_services.storage_provider.healthcheck()
        scheduler = runtime_services.scheduler.__class__.__name__
        ready = database["ok"] and redis["ok"] and storage["ok"]
        return {
            "status": "ready" if ready else "degraded",
            "checks": {
                "database": database,
                "redis": redis,
                "storage": storage,
                "scheduler": {"ok": True, "backend": scheduler},
            },
        }

    async def health(self) -> dict[str, object]:
        readiness = await self.ready()
        return {
            "project": settings.PROJECT_NAME,
            "environment": settings.ENVIRONMENT.value,
            **readiness,
        }

    async def _check_database(self) -> dict[str, object]:
        try:
            async with SessionLocal() as session:
                await session.execute(text("SELECT 1"))
            return {"ok": True, "backend": "sqlite" if settings.is_sqlite else "postgresql"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


health_service = HealthService()

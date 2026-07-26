from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from app.services.metrics_service import metrics_service

logger = logging.getLogger(__name__)

JobHandler = Callable[[], Awaitable[None]]


class Scheduler(ABC):
    @abstractmethod
    def add_recurring_job(self, name: str, interval_seconds: float, handler: JobHandler) -> None:
        raise NotImplementedError

    @abstractmethod
    async def start(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def stop(self) -> None:
        raise NotImplementedError


class AsyncScheduler(Scheduler):
    def __init__(self) -> None:
        self._job_specs: list[tuple[str, float, JobHandler]] = []
        self._tasks: list[asyncio.Task[None]] = []

    def add_recurring_job(self, name: str, interval_seconds: float, handler: JobHandler) -> None:
        self._job_specs.append((name, interval_seconds, handler))

    async def start(self) -> None:
        for name, interval_seconds, handler in self._job_specs:
            self._tasks.append(asyncio.create_task(self._run_job(name, interval_seconds, handler)))

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def _run_job(self, name: str, interval_seconds: float, handler: JobHandler) -> None:
        while True:
            started_at = time.perf_counter()
            try:
                await asyncio.sleep(interval_seconds)
                await handler()
            except asyncio.CancelledError:
                logger.info("scheduler.cancelled", extra={"job": name})
                raise
            except Exception:
                logger.exception("scheduler.failed", extra={"job": name})
            finally:
                metrics_service.record_scheduler_execution(
                    (time.perf_counter() - started_at) * 1000
                )


class CeleryScheduler(Scheduler):
    def add_recurring_job(self, name: str, interval_seconds: float, handler: JobHandler) -> None:
        logger.info("scheduler.celery.stub", extra={"job": name, "interval_seconds": interval_seconds})

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None


class DramatiqScheduler(Scheduler):
    def add_recurring_job(self, name: str, interval_seconds: float, handler: JobHandler) -> None:
        logger.info(
            "scheduler.dramatiq.stub",
            extra={"job": name, "interval_seconds": interval_seconds},
        )

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from statistics import mean


class MetricsService:
    def __init__(self) -> None:
        self._counters: dict[str, int] = defaultdict(int)
        self._active_users: set[str] = set()
        self._active_sockets = 0
        self._delivery_latencies_ms: deque[float] = deque(maxlen=500)
        self._scheduler_execution_ms: deque[float] = deque(maxlen=500)
        self._message_timestamps: deque[datetime] = deque(maxlen=2000)

    def set_active_users(self, users: list[str]) -> None:
        self._active_users = set(users)

    def set_active_sockets(self, count: int) -> None:
        self._active_sockets = count

    def increment(self, key: str, value: int = 1) -> None:
        self._counters[key] += value

    def record_message(self) -> None:
        self.increment("messages_total")
        self._message_timestamps.append(datetime.now(timezone.utc))

    def record_upload(self) -> None:
        self.increment("uploads_total")

    def record_failed_login(self) -> None:
        self.increment("failed_logins_total")

    def record_delivery_latency(self, milliseconds: float) -> None:
        self._delivery_latencies_ms.append(milliseconds)

    def record_scheduler_execution(self, milliseconds: float) -> None:
        self._scheduler_execution_ms.append(milliseconds)

    def snapshot(self) -> dict[str, float | int]:
        minute_ago = datetime.now(timezone.utc) - timedelta(minutes=1)
        messages_per_minute = sum(1 for stamp in self._message_timestamps if stamp >= minute_ago)
        return {
            "active_users": len(self._active_users),
            "active_sockets": self._active_sockets,
            "messages_per_minute": messages_per_minute,
            "uploads_total": self._counters["uploads_total"],
            "failed_logins_total": self._counters["failed_logins_total"],
            "average_delivery_latency_ms": round(mean(self._delivery_latencies_ms), 2)
            if self._delivery_latencies_ms
            else 0.0,
            "average_scheduler_execution_ms": round(mean(self._scheduler_execution_ms), 2)
            if self._scheduler_execution_ms
            else 0.0,
        }


metrics_service = MetricsService()

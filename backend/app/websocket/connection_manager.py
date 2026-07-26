from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self._socket_to_user: dict[str, str] = {}
        self._user_to_sockets: dict[str, set[str]] = {}
        self._socket_rooms: dict[str, set[str]] = {}
        self._last_activity: dict[str, datetime] = {}

    def connect(self, socket_id: str, user_id: str) -> None:
        user_str = str(user_id)
        self._socket_to_user[socket_id] = user_str
        self._user_to_sockets.setdefault(user_str, set()).add(socket_id)
        self._socket_rooms[socket_id] = set()
        self.record_activity(socket_id)

    def disconnect(self, socket_id: str) -> Optional[str]:
        user_str = self._socket_to_user.pop(socket_id, None)
        self._socket_rooms.pop(socket_id, None)
        self._last_activity.pop(socket_id, None)
        if user_str and user_str in self._user_to_sockets:
            self._user_to_sockets[user_str].discard(socket_id)
            if not self._user_to_sockets[user_str]:
                self._user_to_sockets.pop(user_str)
                return user_str
        return None

    def get_user_id(self, socket_id: str) -> Optional[str]:
        return self._socket_to_user.get(socket_id)

    def get_sockets_for_user(self, user_id: str) -> list[str]:
        return list(self._user_to_sockets.get(str(user_id), set()))

    def get_all_active_users(self) -> list[str]:
        return list(self._user_to_sockets.keys())

    def get_active_socket_count(self) -> int:
        return len(self._socket_to_user)

    def is_user_online(self, user_id: str) -> bool:
        return str(user_id) in self._user_to_sockets

    def join_room(self, socket_id: str, room: str) -> None:
        if socket_id in self._socket_rooms:
            self._socket_rooms[socket_id].add(room)

    def leave_room(self, socket_id: str, room: str) -> None:
        if socket_id in self._socket_rooms:
            self._socket_rooms[socket_id].discard(room)

    def get_rooms_for_socket(self, socket_id: str) -> set[str]:
        return self._socket_rooms.get(socket_id, set())

    def record_activity(self, socket_id: str) -> None:
        self._last_activity[socket_id] = datetime.now(timezone.utc)

    def get_last_activity(self, socket_id: str) -> Optional[datetime]:
        return self._last_activity.get(socket_id)

    def get_stale_sockets(self, timeout_seconds: float = 45.0) -> list[str]:
        now = datetime.now(timezone.utc)
        stale: list[str] = []
        for sid, last_active in list(self._last_activity.items()):
            if (now - last_active).total_seconds() > timeout_seconds:
                stale.append(sid)
        return stale

    def reset(self) -> None:
        self._socket_to_user.clear()
        self._user_to_sockets.clear()
        self._socket_rooms.clear()
        self._last_activity.clear()


connection_manager = ConnectionManager()

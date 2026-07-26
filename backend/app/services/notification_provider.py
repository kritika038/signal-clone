from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, List, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class NotificationEvent(str, Enum):
    NEW_MESSAGE = "new_message"
    GROUP_MESSAGE = "group_message"
    MENTION = "mention"
    REPLY = "reply"
    GROUP_INVITE = "group_invite"
    REACTION = "reaction"


@dataclass(slots=True)
class NotificationPayload:
    event: NotificationEvent
    recipient_id: str
    title: str
    body: str
    data: dict[str, Any]


class NotificationProvider(ABC):
    @abstractmethod
    async def send(self, payload: NotificationPayload, tokens: Optional[List[str]] = None) -> List[str]:
        """
        Sends push notification.
        Returns a list of invalid/expired FCM tokens that failed delivery.
        """
        raise NotImplementedError


class MockNotificationProvider(NotificationProvider):
    async def send(self, payload: NotificationPayload, tokens: Optional[List[str]] = None) -> List[str]:
        logger.info(
            "notification.mock.dispatch",
            extra={
                "event": payload.event.value,
                "recipient_id": payload.recipient_id,
                "token_count": len(tokens) if tokens else 0,
            },
        )
        return []


class FirebaseNotificationProvider(NotificationProvider):
    _MAX_MULTICAST_TOKENS = 500
    def __init__(self) -> None:
        self._initialized = False
        self._init_firebase()

    def _init_firebase(self) -> None:
        try:
            import firebase_admin
            from firebase_admin import credentials

            if not firebase_admin._apps:
                if settings.FIREBASE_CREDENTIALS_PATH:
                    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                    firebase_admin.initialize_app(cred)
                    self._initialized = True
                elif settings.FIREBASE_CREDENTIALS_JSON:
                    import json
                    cred_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
                    cred = credentials.Certificate(cred_dict)
                    firebase_admin.initialize_app(cred)
                    self._initialized = True
                elif settings.FIREBASE_PROJECT_ID:
                    firebase_admin.initialize_app(options={"projectId": settings.FIREBASE_PROJECT_ID})
                    self._initialized = True
                else:
                    logger.warning("Firebase credentials not configured. Firebase notification provider operating in stub mode.")
            else:
                self._initialized = True
        except Exception as exc:
            logger.warning(f"Failed to initialize Firebase Admin SDK: {exc}. Operating in stub mode.")
            self._initialized = False

    @staticmethod
    def _batches(tokens: List[str]) -> Iterable[List[str]]:
        for start in range(0, len(tokens), FirebaseNotificationProvider._MAX_MULTICAST_TOKENS):
            yield tokens[start : start + FirebaseNotificationProvider._MAX_MULTICAST_TOKENS]

    def _send_batch(self, payload: NotificationPayload, tokens: List[str]) -> List[str]:
        """Send one FCM multicast synchronously (the Admin SDK is blocking)."""
        from firebase_admin import messaging

        string_data = {str(k): str(v) for k, v in payload.data.items()}
        string_data["event"] = payload.event.value
        string_data["recipient_id"] = payload.recipient_id
        message = messaging.MulticastMessage(
            tokens=tokens,
            notification=messaging.Notification(title=payload.title, body=payload.body),
            data=string_data,
        )
        response = messaging.send_each_for_multicast(message)
        invalid_tokens: List[str] = []
        for index, result in enumerate(response.responses):
            if result.success:
                continue
            exc = result.exception
            code = str(getattr(exc, "code", "")).lower()
            if (
                isinstance(exc, (messaging.UnregisteredError, messaging.InvalidArgumentError))
                or "registration-token-not-registered" in code
                or "invalid-registration-token" in code
            ):
                invalid_tokens.append(tokens[index])
        logger.info(
            "firebase.dispatch.success",
            extra={
                "recipient_id": payload.recipient_id,
                "success_count": response.success_count,
                "failure_count": response.failure_count,
            },
        )
        return invalid_tokens

    async def send(self, payload: NotificationPayload, tokens: Optional[List[str]] = None) -> List[str]:
        if not tokens:
            logger.info("firebase.dispatch.no_tokens", extra={"recipient_id": payload.recipient_id})
            return []

        if not self._initialized:
            logger.info(
                "firebase.dispatch.stub",
                extra={
                    "recipient_id": payload.recipient_id,
                    "event": payload.event.value,
                    "tokens_count": len(tokens),
                },
            )
            return []

        invalid_tokens: List[str] = []
        try:
            for token_batch in self._batches(tokens):
                invalid_tokens.extend(await asyncio.to_thread(self._send_batch, payload, token_batch))

        except Exception as exc:
            logger.exception("firebase.dispatch.failed", extra={"recipient_id": payload.recipient_id})

        return invalid_tokens


# Alias for backward compatibility
FirebaseProvider = FirebaseNotificationProvider


class APNsProvider(NotificationProvider):
    async def send(self, payload: NotificationPayload, tokens: Optional[List[str]] = None) -> List[str]:
        logger.info("apns.dispatch.stub", extra={"recipient_id": payload.recipient_id})
        return []

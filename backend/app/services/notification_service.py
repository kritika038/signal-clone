import uuid
import logging
from typing import List, Optional, Dict, Any, Set
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.message import Message
from app.models.conversation import Conversation
from app.models.user import User
from app.services.notification_provider import (
    NotificationEvent,
    NotificationPayload,
    NotificationProvider,
)
from app.services.device_token_service import DeviceTokenService
from app.services.runtime import runtime_services

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, db: AsyncSession, provider: Optional[NotificationProvider] = None):
        self.db = db
        self.provider = provider or runtime_services.notification_provider
        self.device_service = DeviceTokenService(db)

    async def _send_to_user(
        self,
        recipient_id: uuid.UUID,
        event: NotificationEvent,
        title: str,
        body: str,
        data: Dict[str, Any]
    ) -> None:
        """
        Retrieves device tokens for a recipient and dispatches push notification payload.
        Cleans up any invalid/expired tokens returned by provider.
        """
        device_tokens = await self.device_service.get_user_devices(recipient_id)
        if not device_tokens:
            return

        token_strings = [dt.fcm_token for dt in device_tokens]
        payload = NotificationPayload(
            event=event,
            recipient_id=str(recipient_id),
            title=title,
            body=body,
            data=data
        )

        invalid_tokens = await self.provider.send(payload, tokens=token_strings)
        if invalid_tokens:
            logger.info(f"Removing {len(invalid_tokens)} invalid/expired FCM tokens for user {recipient_id}")
            await self.device_service.remove_invalid_tokens(invalid_tokens)

    async def notify_new_message(
        self,
        message: Message,
        conversation: Conversation,
        sender: User,
        recipient_ids: List[uuid.UUID],
        mentioned_user_ids: Optional[List[uuid.UUID]] = None,
        reply_to_author_id: Optional[uuid.UUID] = None
    ) -> None:
        """
        Sends notifications for a new message:
        - Direct message
        - Group message
        - Mention (override for mentioned users)
        - Reply (override for replied user)
        Guarantees sender is never notified.
        """
        # Ensure sender is excluded
        sender_id = sender.id
        effective_recipients: Set[uuid.UUID] = {r_id for r_id in recipient_ids if r_id != sender_id}

        if not effective_recipients:
            return

        sender_name = sender.display_name or sender.username or "Someone"
        body_text = message.content or "Sent a media attachment"

        mentioned_set: Set[uuid.UUID] = set(mentioned_user_ids or []) - {sender_id}
        reply_target: Optional[uuid.UUID] = reply_to_author_id if reply_to_author_id != sender_id else None

        for recipient_id in effective_recipients:
            # 1. Mention Notification
            if recipient_id in mentioned_set:
                title = f"{sender_name} mentioned you"
                body = body_text
                event = NotificationEvent.MENTION
            # 2. Reply Notification
            elif recipient_id == reply_target:
                title = f"{sender_name} replied to your message"
                body = body_text
                event = NotificationEvent.REPLY
            # 3. Direct Message / Group Message Notification
            else:
                if conversation.type.value == "group":
                    group_name = conversation.name or "Group Chat"
                    title = f"{group_name}"
                    body = f"{sender_name}: {body_text}"
                    event = NotificationEvent.GROUP_MESSAGE
                else:
                    title = sender_name
                    body = body_text
                    event = NotificationEvent.NEW_MESSAGE

            data = {
                "conversation_id": str(conversation.id),
                "message_id": str(message.id),
                "sender_id": str(sender_id),
                "type": conversation.type.value,
            }

            await self._send_to_user(
                recipient_id=recipient_id,
                event=event,
                title=title,
                body=body,
                data=data
            )

    async def notify_group_invite(
        self,
        conversation: Conversation,
        inviter: User,
        invited_user_ids: List[uuid.UUID]
    ) -> None:
        """
        Sends push notifications to users invited to a group.
        Guarantees inviter is never notified.
        """
        inviter_id = inviter.id
        effective_targets = [u_id for u_id in invited_user_ids if u_id != inviter_id]

        if not effective_targets:
            return

        inviter_name = inviter.display_name or inviter.username or "Someone"
        group_name = conversation.name or "a group"
        title = "Group Invite"
        body = f"{inviter_name} added you to {group_name}"

        data = {
            "conversation_id": str(conversation.id),
            "inviter_id": str(inviter_id),
            "type": "group_invite"
        }

        for target_id in effective_targets:
            await self._send_to_user(
                recipient_id=target_id,
                event=NotificationEvent.GROUP_INVITE,
                title=title,
                body=body,
                data=data
            )

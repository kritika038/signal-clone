import uuid
import html
import re
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_, delete, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.models.conversation import Conversation
from app.models.conversation_member import ConversationMember
from app.models.conversation_preference import ConversationPreference
from app.models.contact import Contact
from app.models.blocked_user import BlockedUser
from app.models.starred_message import StarredMessage
from app.models.message_deleted_for_me import MessageDeletedForMe
from app.models.enums import MessageType, ConversationType, ReceiptStatus
from app.repositories.message_repository import MessageRepository
from app.services.attachment_service import AttachmentService

logger = logging.getLogger(__name__)

class MessageService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.msg_repo = MessageRepository(db)
        self.attach_service = AttachmentService()

    async def _validate_membership_and_blocks(self, conversation_id: uuid.UUID, sender_id: uuid.UUID) -> Conversation:
        """
        Validates that the sender is an active member of the conversation,
        the conversation is active, and no block relationships exist.
        """
        conv_query = select(Conversation).where(
            and_(Conversation.id == conversation_id, Conversation.deleted_at.is_(None))
        )
        res_conv = await self.db.execute(conv_query)
        conv = res_conv.scalar_one_or_none()
        if not conv:
            raise ValueError("Conversation not found or deleted")

        member_query = select(ConversationMember).where(
            and_(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.user_id == sender_id,
                ConversationMember.left_at.is_(None)
            )
        )
        res_member = await self.db.execute(member_query)
        member = res_member.scalar_one_or_none()
        if not member:
            raise ValueError("User is not an active member of this conversation")

        if conv.type == ConversationType.DIRECT:
            other_query = select(ConversationMember).where(
                and_(
                    ConversationMember.conversation_id == conversation_id,
                    ConversationMember.user_id != sender_id
                )
            )
            res_other = await self.db.execute(other_query)
            other_member = res_other.scalar_one_or_none()
            if other_member:
                block_query = select(BlockedUser).where(
                    or_(
                        and_(BlockedUser.user_id == sender_id, BlockedUser.blocked_user_id == other_member.user_id),
                        and_(BlockedUser.user_id == other_member.user_id, BlockedUser.blocked_user_id == sender_id)
                    )
                )
                res_block = await self.db.execute(block_query)
                if res_block.scalar_one_or_none():
                    raise ValueError("Cannot send message: Block relationship exists")
        
        return conv

    def _extract_link_preview(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Extracts URLs and generates rich preview mock metadata.
        """
        if not content:
            return None
        url_match = re.search(r'(https?://[^\s]+)', content)
        if url_match:
            url = url_match.group(1)
            # Mock rich preview generation
            domain = url.split("//")[1].split("/")[0]
            return {
                "url": url,
                "title": f"Preview: {domain}",
                "description": f"Shared link from {domain}. Click to view details.",
                "image_url": f"https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150"
            }
        return None

    async def send_new_message(
        self,
        conversation_id: uuid.UUID,
        sender_id: uuid.UUID,
        content: Optional[str],
        message_type: MessageType = MessageType.TEXT,
        reply_to_id: Optional[uuid.UUID] = None,
        attachments_in: Optional[List[Dict[str, Any]]] = None,
        client_message_id: Optional[str] = None,
        scheduled_at: Optional[datetime] = None
    ) -> Message:
        """
        Orchestrates sending a message: validates permissions, enforces idempotency,
        calculates disappearing timers, generates link previews, and persists message.
        """
        # 1. Idempotency Check: Prevent duplicate sends
        if client_message_id:
            dup_query = select(Message).where(Message.client_message_id == client_message_id)
            res_dup = await self.db.execute(dup_query)
            dup = res_dup.scalar_one_or_none()
            if dup:
                logger.info(f"[MessageService] Duplicate send intercepted for client_message_id {client_message_id}")
                return dup

        # 2. Validate membership & blocks
        await self._validate_membership_and_blocks(conversation_id, sender_id)

        # 3. Sanitize HTML content
        sanitized_content = html.escape(content) if content else None

        # 4. Extract link preview if text contains URLs
        link_preview = None
        if sanitized_content and message_type == MessageType.TEXT:
            link_preview = self._extract_link_preview(sanitized_content)

        # 5. Process attachments
        processed_attachments = []
        if attachments_in:
            for attach in attachments_in:
                self.attach_service.validate_attachment(attach)
                processed_attachments.append(self.attach_service.process_metadata(attach))

        # 6. Validate reply target
        if reply_to_id:
            parent_msg = await self.msg_repo.get(reply_to_id)
            if not parent_msg or parent_msg.conversation_id != conversation_id:
                raise ValueError("Invalid reply target message")

        # 7. Check disappearing message preference
        expires_at = None
        pref_query = select(ConversationPreference).where(
            and_(
                ConversationPreference.conversation_id == conversation_id,
                ConversationPreference.user_id == sender_id
            )
        )
        res_pref = await self.db.execute(pref_query)
        pref = res_pref.scalar_one_or_none()
        if pref and pref.disappearing_timer > 0 and not scheduled_at:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=pref.disappearing_timer)

        # 8. Save message
        msg = Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            content=sanitized_content,
            message_type=message_type,
            reply_to_id=reply_to_id,
            client_message_id=client_message_id,
            scheduled_at=scheduled_at,
            expires_at=expires_at
        )
        self.db.add(msg)
        await self.db.flush()

        # Add attachments
        if processed_attachments:
            from app.models.attachment import Attachment
            for attach in processed_attachments:
                db_attach = Attachment(
                    message_id=msg.id,
                    storage_key=attach["storage_key"],
                    original_filename=attach["original_filename"],
                    mime_type=attach["mime_type"],
                    size=attach["size"],
                    width=attach.get("width"),
                    height=attach.get("height"),
                    duration=attach.get("duration"),
                    thumbnail_url=attach.get("thumbnail_url"),
                    checksum=attach.get("checksum")
                )
                self.db.add(db_attach)

        # Register message receipts (only if NOT scheduled/drafts)
        if not scheduled_at:
            members_query = select(ConversationMember).where(
                and_(
                    ConversationMember.conversation_id == conversation_id,
                    ConversationMember.left_at.is_(None)
                )
            )
            res_members = await self.db.execute(members_query)
            members = res_members.scalars().all()
            
            from app.models.message_receipt import MessageReceipt
            for member in members:
                status = ReceiptStatus.READ if member.user_id == sender_id else ReceiptStatus.SENT
                receipt = MessageReceipt(
                    message_id=msg.id,
                    user_id=member.user_id,
                    status=status
                )
                self.db.add(receipt)

            # Update parent conversation activity
            from app.models.conversation import Conversation
            conv_update_query = (
                update(Conversation)
                .where(Conversation.id == conversation_id)
                .values(last_message_id=msg.id, last_activity_at=datetime.now(timezone.utc))
            )
            await self.db.execute(conv_update_query)

        await self.db.commit()
        await self.db.refresh(msg)

        if not scheduled_at:
            try:
                from app.services.notification_service import NotificationService
                from app.models.user import User
                res_sender = await self.db.execute(select(User).where(User.id == sender_id))
                sender_user = res_sender.scalar_one_or_none()

                recipient_user_ids = [m.user_id for m in members if m.user_id != sender_id]

                mentioned_user_ids = []
                if sanitized_content:
                    mentions = re.findall(r'@(\w+)', sanitized_content)
                    if mentions:
                        res_mentioned = await self.db.execute(
                            select(User.id).where(User.username.in_(mentions))
                        )
                        mentioned_user_ids = list(res_mentioned.scalars().all())

                reply_author_id = None
                if reply_to_id:
                    parent_msg = await self.msg_repo.get(reply_to_id)
                    if parent_msg:
                        reply_author_id = parent_msg.sender_id

                if sender_user and recipient_user_ids:
                    await NotificationService(self.db).notify_new_message(
                        message=msg,
                        conversation=conv,
                        sender=sender_user,
                        recipient_ids=recipient_user_ids,
                        mentioned_user_ids=mentioned_user_ids,
                        reply_to_author_id=reply_author_id,
                    )
            except Exception as exc:
                logger.error(f"[MessageService] Error dispatching push notification: {exc}")

        return msg


    async def edit_user_message(self, message_id: uuid.UUID, sender_id: uuid.UUID, content: str) -> Message:
        msg = await self.msg_repo.get(message_id)
        if not msg or msg.deleted_at is not None:
            raise ValueError("Message not found or deleted")
        if msg.sender_id != sender_id:
            raise PermissionError("User does not own this message")
        if msg.message_type != MessageType.TEXT:
            raise ValueError("Only text messages can be edited")

        sanitized = html.escape(content)
        updated = await self.msg_repo.edit_message(message_id, sanitized)
        if not updated:
            raise ValueError("Failed to edit message")
        return updated

    async def delete_for_everyone(self, message_id: uuid.UUID, sender_id: uuid.UUID) -> Message:
        """
        Soft-deletes a message for all participants (Delete For Everyone).
        """
        msg = await self.msg_repo.get(message_id)
        if not msg or msg.deleted_at is not None:
            raise ValueError("Message not found or already deleted")
        if msg.sender_id != sender_id:
            raise PermissionError("User does not own this message")

        # Soft delete by setting deleted_at
        msg.deleted_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    async def delete_for_me(self, message_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """
        Registers a delete-for-me record, hiding the message from user_id's logs.
        """
        msg = await self.msg_repo.get(message_id)
        if not msg:
            raise ValueError("Message not found")

        # Check if already deleted for me
        query = select(MessageDeletedForMe).where(
            and_(
                MessageDeletedForMe.message_id == message_id,
                MessageDeletedForMe.user_id == user_id
            )
        )
        res = await self.db.execute(query)
        if res.scalar_one_or_none():
            return  # Already deleted

        deleted_me = MessageDeletedForMe(message_id=message_id, user_id=user_id)
        self.db.add(deleted_me)
        await self.db.commit()

    async def toggle_star_message(self, message_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """
        Stars or unstars a message. Returns True if starred, False if unstarred.
        """
        query = select(StarredMessage).where(
            and_(
                StarredMessage.message_id == message_id,
                StarredMessage.user_id == user_id
            )
        )
        res = await self.db.execute(query)
        starred = res.scalar_one_or_none()
        
        if starred:
            await self.db.delete(starred)
            await self.db.commit()
            return False
        else:
            new_star = StarredMessage(message_id=message_id, user_id=user_id)
            self.db.add(new_star)
            await self.db.commit()
            return True

    async def get_starred_messages(self, user_id: uuid.UUID) -> List[Message]:
        query = (
            select(Message)
            .join(StarredMessage, StarredMessage.message_id == Message.id)
            .where(
                and_(
                    StarredMessage.user_id == user_id,
                    Message.deleted_at.is_(None)
                )
            )
            .options(
                selectinload(Message.attachments),
                selectinload(Message.reactions)
            )
        )
        res = await self.db.execute(query)
        return list(res.scalars().all())

    async def toggle_pin_message(self, message_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """
        Pins or unpins a message inside its conversation.
        """
        msg = await self.msg_repo.get(message_id)
        if not msg:
            raise ValueError("Message not found")

        # Validate that user is a member of the conversation
        await self._validate_membership_and_blocks(msg.conversation_id, user_id)

        msg.is_pinned = not msg.is_pinned
        await self.db.commit()
        await self.db.refresh(msg)
        return msg.is_pinned

    async def forward_message(
        self, target_conversation_id: uuid.UUID, sender_id: uuid.UUID, message_id: uuid.UUID
    ) -> Message:
        source_msg = await self.msg_repo.get(message_id)
        if not source_msg or source_msg.deleted_at is not None:
            raise ValueError("Source message not found or deleted")

        await self._validate_membership_and_blocks(target_conversation_id, sender_id)

        forwarded = Message(
            conversation_id=target_conversation_id,
            sender_id=sender_id,
            content=source_msg.content,
            message_type=source_msg.message_type,
            forwarded_from_id=source_msg.sender_id
        )
        self.db.add(forwarded)
        await self.db.flush()

        # Generate receipts
        members_query = select(ConversationMember).where(
            and_(
                ConversationMember.conversation_id == target_conversation_id,
                ConversationMember.left_at.is_(None)
            )
        )
        res_members = await self.db.execute(members_query)
        members = res_members.scalars().all()
        
        from app.models.message_receipt import MessageReceipt
        for member in members:
            status = ReceiptStatus.READ if member.user_id == sender_id else ReceiptStatus.SENT
            receipt = MessageReceipt(
                message_id=forwarded.id,
                user_id=member.user_id,
                status=status
            )
            self.db.add(receipt)

        # Update target conversation activity
        from app.models.conversation import Conversation
        conv_update_query = (
            update(Conversation)
            .where(Conversation.id == target_conversation_id)
            .values(last_message_id=forwarded.id, last_activity_at=datetime.now(timezone.utc))
        )
        await self.db.execute(conv_update_query)

        await self.db.commit()
        await self.db.refresh(forwarded)
        return forwarded

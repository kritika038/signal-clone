from datetime import datetime, timezone
from typing import List, Optional
import uuid
from sqlalchemy import select, and_, or_, update, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.message import Message
from app.models.message_receipt import MessageReceipt
from app.models.message_reaction import MessageReaction
from app.models.attachment import Attachment
from app.models.conversation import Conversation
from app.models.conversation_member import ConversationMember
from app.models.enums import MessageType, ReceiptStatus
from app.repositories.base import BaseRepository

class MessageRepository(BaseRepository[Message]):
    def __init__(self, db: AsyncSession):
        super().__init__(Message, db)

    async def get_messages_by_conversation(
        self, conversation_id: uuid.UUID, limit: int = 50, skip: int = 0
    ) -> List[Message]:
        query = (
            select(Message)
            .where(
                and_(
                    Message.conversation_id == conversation_id,
                    Message.deleted_at.is_(None)
                )
            )
            .order_by(desc(Message.created_at))
            .offset(skip)
            .limit(limit)
            .options(
                selectinload(Message.attachments),
                selectinload(Message.reactions),
                selectinload(Message.receipts)
            )
        )
        result = await self.db.execute(query)
        # Reverse to return chronological order
        messages = list(result.scalars().all())
        messages.reverse()
        return messages

    async def search_messages(self, conversation_id: uuid.UUID, search_term: str) -> List[Message]:
        query = (
            select(Message)
            .where(
                and_(
                    Message.conversation_id == conversation_id,
                    Message.content.ilike(f"%{search_term}%"),
                    Message.deleted_at.is_(None)
                )
            )
            .order_by(Message.created_at.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def send_message(
        self,
        conversation_id: uuid.UUID,
        sender_id: uuid.UUID,
        content: Optional[str],
        message_type: MessageType = MessageType.TEXT,
        reply_to_id: Optional[uuid.UUID] = None,
        attachments_in: Optional[List[dict]] = None
    ) -> Message:
        """
        Creates a message, builds attachments, pushes receipts for all conversation members,
        and updates the parent conversation's last_activity_at timestamp.
        """
        msg = Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            content=content,
            message_type=message_type,
            reply_to_id=reply_to_id
        )
        self.db.add(msg)
        await self.db.flush()

        # Add attachments if any
        if attachments_in:
            for attach in attachments_in:
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

        # Retrieve active conversation members
        members_query = select(ConversationMember).where(
            and_(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.left_at.is_(None)
            )
        )
        res = await self.db.execute(members_query)
        members = res.scalars().all()

        # Create Receipts for all other members
        for member in members:
            # Sender receipt is marked as READ instantly
            status = ReceiptStatus.READ if member.user_id == sender_id else ReceiptStatus.SENT
            receipt = MessageReceipt(
                message_id=msg.id,
                user_id=member.user_id,
                status=status
            )
            self.db.add(receipt)

        # Update Conversation stats
        update_conv_query = (
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(last_message_id=msg.id, last_activity_at=datetime.now(timezone.utc))
        )
        await self.db.execute(update_conv_query)

        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    async def reply_to_message(
        self, conversation_id: uuid.UUID, sender_id: uuid.UUID, parent_id: uuid.UUID, content: str
    ) -> Message:
        return await self.send_message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            content=content,
            reply_to_id=parent_id
        )

    async def mark_read(self, message_id: uuid.UUID, user_id: uuid.UUID) -> Optional[MessageReceipt]:
        """
        Marks a specific message as READ for a user.
        Updates the user's last_read_message_id inside the ConversationMember table.
        """
        # Fetch receipt
        query = select(MessageReceipt).where(
            and_(
                MessageReceipt.message_id == message_id,
                MessageReceipt.user_id == user_id
            )
        )
        res = await self.db.execute(query)
        receipt = res.scalar_one_or_none()

        if receipt:
            if receipt.status != ReceiptStatus.READ:
                receipt.status = ReceiptStatus.READ
                receipt.updated_at = datetime.now(timezone.utc)
                
                # Fetch message to update ConversationMember last_read_message_id
                msg = await self.get(message_id)
                if msg:
                    member_query = select(ConversationMember).where(
                        and_(
                            ConversationMember.conversation_id == msg.conversation_id,
                            ConversationMember.user_id == user_id
                        )
                    )
                    member_res = await self.db.execute(member_query)
                    member = member_res.scalar_one_or_none()
                    if member:
                        member.last_read_message_id = message_id

                await self.db.commit()
                await self.db.refresh(receipt)
        return receipt

    async def add_reaction(self, message_id: uuid.UUID, user_id: uuid.UUID, emoji: str, unicode_char: str) -> MessageReaction:
        # Check if user already reacted with this emoji
        query = select(MessageReaction).where(
            and_(
                MessageReaction.message_id == message_id,
                MessageReaction.user_id == user_id,
                MessageReaction.reaction == emoji
            )
        )
        res = await self.db.execute(query)
        reaction = res.scalar_one_or_none()

        if not reaction:
            reaction = MessageReaction(
                message_id=message_id,
                user_id=user_id,
                reaction=emoji,
                unicode=unicode_char
            )
            self.db.add(reaction)
            await self.db.commit()
            await self.db.refresh(reaction)
        return reaction

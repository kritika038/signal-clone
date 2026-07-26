import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select, and_, or_, update, desc
from sqlalchemy.orm import selectinload

from app.models.message import Message
from app.models.message_receipt import MessageReceipt
from app.models.conversation_member import ConversationMember
from app.models.enums import ReceiptStatus
from app.repositories.message import MessageRepository as CoreMessageRepository

class MessageRepository(CoreMessageRepository):
    """
    Extends CoreMessageRepository to handle real-time delivery pipeline updates,
    soft deletion, editing, and offline synchronization.
    """
    async def get_message_detail(self, message_id: uuid.UUID) -> Optional[Message]:
        query = (
            select(Message)
            .where(Message.id == message_id)
            .options(
                selectinload(Message.attachments),
                selectinload(Message.reactions),
                selectinload(Message.receipts)
            )
        )
        res = await self.db.execute(query)
        return res.scalar_one_or_none()

    async def soft_delete_message(self, message_id: uuid.UUID) -> Optional[Message]:
        msg = await self.get(message_id)
        if msg:
            msg.deleted_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(msg)
        return msg

    async def edit_message(self, message_id: uuid.UUID, content: str) -> Optional[Message]:
        msg = await self.get(message_id)
        if msg:
            msg.content = content
            msg.edited_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(msg)
        return msg

    async def update_receipt_status(
        self, message_id: uuid.UUID, user_id: uuid.UUID, new_status: ReceiptStatus
    ) -> Optional[MessageReceipt]:
        """
        Updates the receipt status for a message recipient.
        Enforces state hierarchy (e.g. cannot downgrade READ -> DELIVERED).
        Also updates conversation's last_read_message_id if status is READ.
        """
        query = select(MessageReceipt).where(
            and_(
                MessageReceipt.message_id == message_id,
                MessageReceipt.user_id == user_id
            )
        ).options(selectinload(MessageReceipt.message))
        res = await self.db.execute(query)
        receipt = res.scalar_one_or_none()
        
        if receipt:
            priorities = {
                ReceiptStatus.SENDING: 0,
                ReceiptStatus.SENT: 1,
                ReceiptStatus.DELIVERED: 2,
                ReceiptStatus.READ: 3
            }
            current_priority = priorities.get(receipt.status, 0)
            new_priority = priorities.get(new_status, 0)
            
            if new_priority > current_priority:
                receipt.status = new_status
                receipt.updated_at = datetime.now(timezone.utc)
                
                if new_status == ReceiptStatus.READ:
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

    async def get_undelivered_receipts(self, user_id: uuid.UUID) -> List[MessageReceipt]:
        """
        Queries all message receipts for a user that are currently in 'SENT' state.
        Allows synchronizing offline messages upon user reconnection.
        """
        query = (
            select(MessageReceipt)
            .where(
                and_(
                    MessageReceipt.user_id == user_id,
                    MessageReceipt.status == ReceiptStatus.SENT
                )
            )
            .options(selectinload(MessageReceipt.message))
        )
        res = await self.db.execute(query)
        return list(res.scalars().all())

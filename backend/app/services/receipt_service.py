import uuid
import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ReceiptStatus
from app.models.message import Message
from app.models.message_receipt import MessageReceipt
from app.repositories.message_repository import MessageRepository

logger = logging.getLogger(__name__)

class ReceiptService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.msg_repo = MessageRepository(db)

    async def update_receipt(
        self, message_id: uuid.UUID, user_id: uuid.UUID, status: ReceiptStatus
    ) -> Optional[MessageReceipt]:
        """
        Updates a specific message receipt status for a user.
        """
        return await self.msg_repo.update_receipt_status(message_id, user_id, status)

    async def sync_offline_messages(self, user_id: uuid.UUID) -> List[Message]:
        """
        Retrieves all undelivered (SENT) message receipts for the user,
        updates their status to DELIVERED, and returns the corresponding messages.
        """
        receipts = await self.msg_repo.get_undelivered_receipts(user_id)
        if not receipts:
            return []

        logger.info(f"[ReceiptService] Synchronizing {len(receipts)} offline message(s) for user {user_id}")
        
        messages: List[Message] = []
        for receipt in receipts:
            # Transition receipt status from SENT to DELIVERED
            await self.msg_repo.update_receipt_status(receipt.message_id, user_id, ReceiptStatus.DELIVERED)
            if receipt.message:
                messages.append(receipt.message)
                
        return messages

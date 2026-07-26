import uuid
import logging
from typing import Optional, List
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.conversation_draft import ConversationDraft

logger = logging.getLogger(__name__)

class DraftService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_draft(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> Optional[ConversationDraft]:
        query = select(ConversationDraft).where(
            and_(
                ConversationDraft.conversation_id == conversation_id,
                ConversationDraft.user_id == user_id
            )
        )
        res = await self.db.execute(query)
        return res.scalar_one_or_none()

    async def save_draft(self, conversation_id: uuid.UUID, user_id: uuid.UUID, content: str) -> ConversationDraft:
        draft = await self.get_draft(conversation_id, user_id)
        if draft:
            draft.content = content
        else:
            draft = ConversationDraft(
                conversation_id=conversation_id,
                user_id=user_id,
                content=content
            )
            self.db.add(draft)
            
        await self.db.commit()
        await self.db.refresh(draft)
        logger.info(f"[DraftService] Saved draft for user {user_id} in conversation {conversation_id}")
        return draft

    async def clear_draft(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        query = delete(ConversationDraft).where(
            and_(
                ConversationDraft.conversation_id == conversation_id,
                ConversationDraft.user_id == user_id
            )
        )
        res = await self.db.execute(query)
        await self.db.commit()
        return res.rowcount > 0

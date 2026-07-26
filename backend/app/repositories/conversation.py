from datetime import datetime, timedelta, timezone
from typing import List, Optional
import uuid
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.conversation import Conversation
from app.models.conversation_member import ConversationMember
from app.models.conversation_preference import ConversationPreference
from app.models.enums import ConversationType, ConversationRole
from app.repositories.base import BaseRepository

class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self, db: AsyncSession):
        super().__init__(Conversation, db)

    async def get_recent_conversations(
        self, user_id: uuid.UUID, limit: int = 20, skip: int = 0
    ) -> List[Conversation]:
        """
        Retrieves conversations for a user, sorted by last_activity_at desc.
        Loads members and last_message relationships.
        """
        # Find conversation IDs where the user is a member
        member_subquery = (
            select(ConversationMember.conversation_id)
            .where(
                and_(
                    ConversationMember.user_id == user_id,
                    ConversationMember.left_at.is_(None)
                )
            )
        )
        
        query = (
            select(Conversation)
            .where(
                and_(
                    Conversation.id.in_(member_subquery),
                    Conversation.deleted_at.is_(None)
                )
            )
            .order_by(desc(Conversation.last_activity_at))
            .offset(skip)
            .limit(limit)
            .options(
                selectinload(Conversation.members).selectinload(ConversationMember.user),
                selectinload(Conversation.last_message)
            )
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def search_conversations(self, user_id: uuid.UUID, query_string: str) -> List[Conversation]:
        """
        Searches conversations by name, description, or nicknames of members.
        """
        member_subquery = (
            select(ConversationMember.conversation_id)
            .where(
                and_(
                    ConversationMember.user_id == user_id,
                    ConversationMember.left_at.is_(None)
                )
            )
        )

        query = (
            select(Conversation)
            .where(
                and_(
                    Conversation.id.in_(member_subquery),
                    Conversation.deleted_at.is_(None),
                    or_(
                        Conversation.name.ilike(f"%{query_string}%"),
                        Conversation.description.ilike(f"%{query_string}%")
                    )
                )
            )
            .order_by(desc(Conversation.last_activity_at))
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_direct_chat(self, user_id_1: uuid.UUID, user_id_2: uuid.UUID) -> Conversation:
        """
        Creates a direct conversation between two users if it doesn't already exist.
        """
        # Check if direct chat already exists between these users
        check_query = (
            select(Conversation)
            .where(
                and_(
                    Conversation.type == ConversationType.DIRECT,
                    Conversation.deleted_at.is_(None)
                )
            )
            .options(selectinload(Conversation.members))
        )
        res = await self.db.execute(check_query)
        conversations = res.scalars().all()
        
        for conv in conversations:
            member_ids = {m.user_id for m in conv.members if m.left_at is None}
            if member_ids == {user_id_1, user_id_2}:
                return conv

        # Create new conversation
        conv = Conversation(type=ConversationType.DIRECT)
        self.db.add(conv)
        await self.db.flush()  # Generate ID

        # Create member entries
        member1 = ConversationMember(
            conversation_id=conv.id,
            user_id=user_id_1,
            role=ConversationRole.MEMBER
        )
        member2 = ConversationMember(
            conversation_id=conv.id,
            user_id=user_id_2,
            role=ConversationRole.MEMBER
        )
        self.db.add_all([member1, member2])

        # Create default preference slots
        pref1 = ConversationPreference(conversation_id=conv.id, user_id=user_id_1)
        pref2 = ConversationPreference(conversation_id=conv.id, user_id=user_id_2)
        self.db.add_all([pref1, pref2])

        await self.db.commit()
        await self.db.refresh(conv)
        return conv

    async def archive_conversation(self, conversation_id: uuid.UUID, is_archived: bool = True) -> Optional[Conversation]:
        conv = await self.get(conversation_id)
        if conv:
            conv.is_archived = is_archived
            await self.db.commit()
            await self.db.refresh(conv)
        return conv

    async def get_preference(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> Optional[ConversationPreference]:
        query = select(ConversationPreference).where(
            and_(
                ConversationPreference.conversation_id == conversation_id,
                ConversationPreference.user_id == user_id
            )
        )
        res = await self.db.execute(query)
        return res.scalar_one_or_none()

    async def pin_conversation(self, conversation_id: uuid.UUID, user_id: uuid.UUID, is_pinned: bool) -> bool:
        pref = await self.get_preference(conversation_id, user_id)
        if not pref:
            pref = ConversationPreference(conversation_id=conversation_id, user_id=user_id, is_pinned=is_pinned)
            self.db.add(pref)
        else:
            pref.is_pinned = is_pinned
        await self.db.commit()
        return True

    async def mute_conversation(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID, is_muted: bool, duration_hours: Optional[int] = None
    ) -> bool:
        pref = await self.get_preference(conversation_id, user_id)
        mute_until = None
        if is_muted and duration_hours:
            mute_until = datetime.now(timezone.utc) + timedelta(hours=duration_hours)
        
        if not pref:
            pref = ConversationPreference(
                conversation_id=conversation_id,
                user_id=user_id,
                is_muted=is_muted,
                mute_until=mute_until
            )
            self.db.add(pref)
        else:
            pref.is_muted = is_muted
            pref.mute_until = mute_until
        await self.db.commit()
        return True

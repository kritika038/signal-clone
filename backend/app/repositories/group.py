from datetime import datetime, timezone
from typing import List, Optional
import uuid
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.conversation import Conversation
from app.models.conversation_member import ConversationMember
from app.models.conversation_preference import ConversationPreference
from app.models.enums import ConversationType, ConversationRole, MessageType
from app.models.message import Message
from app.repositories.base import BaseRepository

class GroupRepository(BaseRepository[Conversation]):
    def __init__(self, db: AsyncSession):
        super().__init__(Conversation, db)

    async def create_group(
        self, name: str, description: Optional[str], creator_id: uuid.UUID, member_ids: List[uuid.UUID]
    ) -> Conversation:
        """
        Creates a new group conversation, assigns the creator as OWNER,
        adds members, and logs a system initialization message.
        """
        group = Conversation(
            type=ConversationType.GROUP,
            name=name,
            description=description,
            created_by=creator_id
        )
        self.db.add(group)
        await self.db.flush()

        # Add creator as OWNER
        owner_member = ConversationMember(
            conversation_id=group.id,
            user_id=creator_id,
            role=ConversationRole.OWNER
        )
        self.db.add(owner_member)
        self.db.add(ConversationPreference(conversation_id=group.id, user_id=creator_id))

        # Add remaining members
        for member_id in member_ids:
            if member_id != creator_id:
                member = ConversationMember(
                    conversation_id=group.id,
                    user_id=member_id,
                    role=ConversationRole.MEMBER
                )
                self.db.add(member)
                self.db.add(ConversationPreference(conversation_id=group.id, user_id=member_id))

        # Log system initialization message
        system_msg = Message(
            conversation_id=group.id,
            sender_id=creator_id,
            content=f"Group '{name}' created by creator.",
            message_type=MessageType.SYSTEM,
            is_system=True
        )
        self.db.add(system_msg)
        await self.db.flush()

        # Update last message reference
        group.last_message_id = system_msg.id
        group.last_activity_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(group)
        return group

    async def add_member(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID, role: ConversationRole = ConversationRole.MEMBER
    ) -> ConversationMember:
        """
        Adds a new member to an existing group. Re-activates if previously left.
        """
        query = select(ConversationMember).where(
            and_(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.user_id == user_id
            )
        )
        res = await self.db.execute(query)
        member = res.scalar_one_or_none()

        if member:
            member.left_at = None
            member.role = role
        else:
            member = ConversationMember(
                conversation_id=conversation_id,
                user_id=user_id,
                role=role
            )
            self.db.add(member)
            
            # Ensure preference exists
            pref_query = select(ConversationPreference).where(
                and_(
                    ConversationPreference.conversation_id == conversation_id,
                    ConversationPreference.user_id == user_id
                )
            )
            pref_res = await self.db.execute(pref_query)
            if not pref_res.scalar_one_or_none():
                self.db.add(ConversationPreference(conversation_id=conversation_id, user_id=user_id))

        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def remove_member(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """
        Marks member as left by setting left_at timestamp.
        """
        query = select(ConversationMember).where(
            and_(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.user_id == user_id,
                ConversationMember.left_at.is_(None)
            )
        )
        res = await self.db.execute(query)
        member = res.scalar_one_or_none()

        if member:
            member.left_at = datetime.now(timezone.utc)
            await self.db.commit()
            return True
        return False

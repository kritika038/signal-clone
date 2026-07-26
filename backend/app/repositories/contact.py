from typing import List, Optional
import uuid
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.contact import Contact
from app.models.blocked_user import BlockedUser
from app.repositories.base import BaseRepository

class ContactRepository(BaseRepository[Contact]):
    def __init__(self, db: AsyncSession):
        super().__init__(Contact, db)

    async def get_contacts_by_owner(self, owner_id: uuid.UUID) -> List[Contact]:
        query = select(Contact).where(Contact.owner_id == owner_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_contact_by_users(self, owner_id: uuid.UUID, contact_user_id: uuid.UUID) -> Optional[Contact]:
        query = select(Contact).where(
            and_(Contact.owner_id == owner_id, Contact.contact_user_id == contact_user_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def add_contact(self, owner_id: uuid.UUID, contact_user_id: uuid.UUID, nickname: Optional[str] = None) -> Contact:
        existing = await self.get_contact_by_users(owner_id, contact_user_id)
        if existing:
            if nickname:
                existing.nickname = nickname
                await self.db.commit()
            return existing

        contact = Contact(owner_id=owner_id, contact_user_id=contact_user_id, nickname=nickname)
        return await self.create(obj_in=contact)

    # Blocked Users methods inside ContactRepository
    async def is_blocked(self, user_id: uuid.UUID, blocked_user_id: uuid.UUID) -> bool:
        query = select(BlockedUser).where(
            and_(BlockedUser.user_id == user_id, BlockedUser.blocked_user_id == blocked_user_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    async def block_user(self, user_id: uuid.UUID, blocked_user_id: uuid.UUID) -> BlockedUser:
        existing = await self.db.execute(
            select(BlockedUser).where(
                and_(BlockedUser.user_id == user_id, BlockedUser.blocked_user_id == blocked_user_id)
            )
        )
        existing_val = existing.scalar_one_or_none()
        if existing_val:
            return existing_val

        block = BlockedUser(user_id=user_id, blocked_user_id=blocked_user_id)
        self.db.add(block)
        await self.db.commit()
        await self.db.refresh(block)
        return block

    async def unblock_user(self, user_id: uuid.UUID, blocked_user_id: uuid.UUID) -> bool:
        query = select(BlockedUser).where(
            and_(BlockedUser.user_id == user_id, BlockedUser.blocked_user_id == blocked_user_id)
        )
        result = await self.db.execute(query)
        block = result.scalar_one_or_none()
        if block:
            await self.db.delete(block)
            await self.db.commit()
            return True
        return False

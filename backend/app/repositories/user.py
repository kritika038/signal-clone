from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.repositories.base import BaseRepository

class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_phone_number(self, phone_number: str) -> Optional[User]:
        query = select(User).where(User.phone == phone_number)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

from typing import Any, Generic, List, Optional, Type, TypeVar
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base_class import Base

ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        """
        Base CRUD Repository.
        Provides boilerplate methods for entity querying and manipulation.
        """
        self.model = model
        self.db = db

    async def get(self, id: Any) -> Optional[ModelType]:
        return await self.db.get(self.model, id)

    async def get_multi(self, *, skip: int = 0, limit: int = 100) -> List[ModelType]:
        query = select(self.model).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, *, obj_in: Any) -> ModelType:
        self.db.add(obj_in)
        await self.db.commit()
        await self.db.refresh(obj_in)
        return obj_in

    async def remove(self, *, id: Any) -> Optional[ModelType]:
        obj = await self.get(id)
        if obj:
            await self.db.delete(obj)
            await self.db.commit()
        return obj

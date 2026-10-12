import uuid
from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar('ModelType', bound=Base)


class BaseRepository(Generic[ModelType]):
    """Базовый репозиторий."""

    def __init__(self, model: type[ModelType]):
        self.model = model

    async def add(self, session: AsyncSession, obj: ModelType) -> ModelType:
        session.add(obj)
        await session.flush()
        return obj

    async def get_by_id(
        self,
        session: AsyncSession,
        obj_id: uuid.UUID
    ) -> ModelType | None:
        return await session.get(self.model, obj_id)

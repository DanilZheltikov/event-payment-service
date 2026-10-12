from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Outbox
from app.db.repository import BaseRepository


class OutboxRepository(BaseRepository[Outbox]):
    """Репозиторий Outbox."""

    def __init__(self):
        super().__init__(Outbox)

    async def get_unpublished(
        self,
        session: AsyncSession,
        limit: int = 100
    ) -> list[Outbox]:
        result = await session.execute(
            select(self.model)
            .where(self.model.published_at.is_(None))
            .order_by(self.model.created_at, self.model.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(result.scalars().all())


outbox_repository = OutboxRepository()

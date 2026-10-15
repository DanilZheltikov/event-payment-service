import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Payment
from app.db.repository import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    """Репозиторий платежа."""

    def __init__(self):
        super().__init__(Payment)

    async def get_by_idempotency_key(
        self,
        session: AsyncSession,
        key: str
    ) -> Payment | None:
        result = await session.execute(
            select(self.model)
            .where(self.model.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_update(
        self,
        session: AsyncSession,
        payment_id: uuid.UUID,
    ) -> Payment | None:
        result = await session.execute(
            select(Payment)
            .where(Payment.id == payment_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()


payment_repository = PaymentRepository()

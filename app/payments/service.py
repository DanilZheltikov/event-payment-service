import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .enums import PaymentStatus
from .models import Payment
from .repository import payment_repository
from .schemas import PaymentCreate
from app.core.constants import (
    NAME_IDEMPOTENCY_KEY_CONSTRAINT,
    UNIQUE_VIOLATION_CODE
)
from app.outbox.models import Outbox
from app.outbox.repository import outbox_repository


class PaymentService:

    @staticmethod
    def validate_idempotency(
        data: PaymentCreate,
        payment: Payment
    ) -> None:
        if (
            payment.amount != data.amount
            or payment.currency != data.currency
            or payment.description != data.description
            or payment.metadata_info != data.metadata_info
            or payment.webhook_url != str(data.webhook_url)
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Idempotency key already used with different parameters'
            )

    @staticmethod
    def is_idempotency_conflict(exc: IntegrityError) -> bool:
        driver_error = getattr(exc.orig, '__cause__', None)
        return (
            getattr(exc.orig, 'sqlstate', None) == UNIQUE_VIOLATION_CODE
            and (
                getattr(driver_error, 'constraint_name', None)
                == NAME_IDEMPOTENCY_KEY_CONSTRAINT
            )
        )

    async def create_payment(
        self,
        session: AsyncSession,
        data: PaymentCreate,
        idempotency_key: str
    ) -> Payment:

        try:
            async with session.begin():
                payment_by_key = (
                    await payment_repository.get_by_idempotency_key(
                        session,
                        idempotency_key
                    )
                )

                if payment_by_key:
                    self.validate_idempotency(data, payment_by_key)
                    return payment_by_key

                payment = await payment_repository.add(
                    session=session,
                    obj=Payment(
                        **data.model_dump(exclude={'webhook_url'}),
                        webhook_url=str(data.webhook_url),
                        idempotency_key=idempotency_key,
                        status=PaymentStatus.PENDING,
                    )
                )
                await outbox_repository.add(
                    session=session,
                    obj=Outbox(
                        event_type='payment.created',
                        routing_key='payments.new',
                        payload={
                            'payment_id': str(payment.id)
                        }
                    )
                )
            return payment

        except IntegrityError as exc:
            if not self.is_idempotency_conflict(exc):
                raise
            payment_by_key = await payment_repository.get_by_idempotency_key(
                session,
                idempotency_key
            )
            if payment_by_key is None:
                raise
            self.validate_idempotency(data, payment_by_key)
            return payment_by_key

    async def get_payment_or_404(
        self,
        session: AsyncSession,
        payment_id: uuid.UUID
    ) -> Payment:
        payment = await payment_repository.get_by_id(session, payment_id)
        if payment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Payment is not found'
            )
        return payment


payment_service = PaymentService()

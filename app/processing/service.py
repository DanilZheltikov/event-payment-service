import asyncio
import random
import uuid
from datetime import datetime, timezone
from http import HTTPStatus

import httpx
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from .exceptions import (
    PaymentNotFoundError,
    PermanentProcessingError,
    RetryableProcessingError
)
from .schemas import PaymentResult
from app.payments.enums import PaymentStatus
from app.payments.models import Payment
from app.payments.repository import payment_repository


class ProcessingService:

    async def _get_payment_or_raise(
        self,
        session: AsyncSession,
        payment_id: uuid.UUID,
        for_update: bool = False
    ) -> Payment:
        if for_update:
            payment = await payment_repository.get_by_id_for_update(
                session,
                payment_id
            )
        else:
            payment = await payment_repository.get_by_id(session, payment_id)

        if payment is None:
            raise PaymentNotFoundError(payment_id=payment_id)

        return payment

    async def process_payment(
        self,
        session: AsyncSession,
        payment_id: uuid.UUID
    ) -> PaymentResult:
        try:
            async with session.begin():
                payment = await self._get_payment_or_raise(session, payment_id)
                if payment.status != PaymentStatus.PENDING:
                    return PaymentResult.model_validate(payment)

            await asyncio.sleep(random.uniform(2, 5))

            async with session.begin():
                payment = await self._get_payment_or_raise(
                    session=session,
                    payment_id=payment_id,
                    for_update=True
                )
                if payment.status == PaymentStatus.PENDING:
                    payment.status = (
                        PaymentStatus.SUCCEEDED
                        if random.random() < 0.9
                        else PaymentStatus.FAILED
                    )
                    payment.processed_at = datetime.now(timezone.utc)

                payment_result = PaymentResult.model_validate(payment)

            return payment_result
        except OperationalError:
            raise RetryableProcessingError(
                f'Ошибка PostgreSQL при обработке платежа {payment_id}'
            )

    async def send_webhook_notification(
        self,
        client: httpx.AsyncClient,
        payment_result: PaymentResult
    ) -> None:
        try:
            response = await client.post(
                payment_result.webhook_url,
                json={
                    'payment_id': str(payment_result.id),
                    'payment_status': payment_result.status
                }
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            status_code = error.response.status_code
            timeout_errors = (
                HTTPStatus.TOO_MANY_REQUESTS,
                HTTPStatus.REQUEST_TIMEOUT
            )

            if (
                status_code in timeout_errors
                or status_code >= HTTPStatus.INTERNAL_SERVER_ERROR
            ):
                raise RetryableProcessingError(
                    f'Ошибка отправки вебхука: {error}'
                )
            raise PermanentProcessingError(f'Ошибка отправки вебхука {error}')

        except httpx.RequestError as error:
            raise RetryableProcessingError(f'Ошибка отправки вебхука {error}')


processing_service = ProcessingService()

import logging

from faststream import ExceptionMiddleware
from faststream.rabbit import RabbitMessage
from pydantic import ValidationError

from .exceptions import (
    PaymentNotFoundError,
    PermanentProcessingError,
    RetryableProcessingError
)
from app.core.broker import broker, retry_2s_queue, retry_4s_queue

logger = logging.getLogger(__name__)

error_middleware = ExceptionMiddleware()


@error_middleware.add_handler(ValidationError)
async def handle_validation_error(
    exc: ValidationError,
    msg: RabbitMessage
) -> None:
    logger.error('Ошибка валидации сообщения: %s', exc)
    await msg.reject(requeue=False)


@error_middleware.add_handler(PaymentNotFoundError)
async def handle_payment_not_found(
    exc: PaymentNotFoundError,
    msg: RabbitMessage
):
    logger.error('Платеж %s не найден:', exc.payment_id)
    await msg.reject(requeue=False)


@error_middleware.add_handler(PermanentProcessingError)
async def handle_permanent_processing_error(
    exc: PermanentProcessingError,
    msg: RabbitMessage
):
    logger.error('Ошибка обработки. Сообщение добавлено DLQ')
    await msg.reject(requeue=False)


@error_middleware.add_handler(RetryableProcessingError)
async def handle_retryable_processing_error(
    exc: RetryableProcessingError,
    msg: RabbitMessage
):
    headers = dict(msg.headers or {})
    attempt = int(headers.get('x-attempt', 0))

    if attempt >= 2:
        logger.error(
            'Исчерпано количество попыток. Отправляем в DLQ'
        )
        await msg.reject(requeue=False)
        return

    retry_queue = retry_2s_queue if attempt == 0 else retry_4s_queue

    try:
        await broker.publish(
            message=msg.body,
            queue=retry_queue.name,
            headers={'x-attempt': attempt + 1},
            content_type=msg.content_type,
            persist=True,
            mandatory=True,
        )
    except Exception:
        logger.error('Не удалось отправить сообщение в retry')
        await msg.nack(requeue=True)
        return

    await msg.ack()

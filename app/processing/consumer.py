import logging

import httpx
from faststream import AckPolicy
from faststream.rabbit.annotations import RabbitMessage

from .schemas import PaymentPayload
from .service import processing_service
from app.core.broker import broker, main_queue
from app.db.session import AsyncSessionLocal


logger = logging.getLogger(__name__)


@broker.subscriber(
    main_queue,
    ack_policy=AckPolicy.MANUAL,
)
async def handle_payment(
    body: PaymentPayload,
    msg: RabbitMessage,
) -> None:

    payment_id = body.payment_id

    async with AsyncSessionLocal() as session:
        payment_result = await processing_service.process_payment(
            session=session,
            payment_id=payment_id
        )

    async with httpx.AsyncClient(
        timeout=10.0,
        follow_redirects=False,
        trust_env=False,
    ) as client:
        await processing_service.send_webhook_notification(
            client=client,
            payment_result=payment_result
        )

    await msg.ack()

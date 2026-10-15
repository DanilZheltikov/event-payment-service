from datetime import datetime, timezone

from faststream.rabbit import RabbitBroker
from sqlalchemy.ext.asyncio import AsyncSession

from app.outbox.repository import outbox_repository


class Publisher:

    def __init__(self, broker: RabbitBroker):
        self.broker = broker

    async def publish_batch(self, session: AsyncSession) -> int:
        async with session.begin():
            events = await outbox_repository.get_unpublished(session)

            for event in events:
                await self.broker.publish(
                    message=event.payload,
                    queue=event.routing_key,
                    persist=True,
                    mandatory=True,
                )
                event.published_at = datetime.now(timezone.utc)
        return len(events)

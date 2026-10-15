import asyncio
import logging

from app.core.broker import broker, setup_queues
from app.db.session import AsyncSessionLocal
from app.outbox.publisher import Publisher


logger = logging.getLogger(__name__)


async def main():
    publisher = Publisher(broker)

    async with broker:
        await setup_queues()

        while True:
            try:
                async with AsyncSessionLocal() as session:
                    count = await publisher.publish_batch(session)

                if count == 0:
                    await asyncio.sleep(1)

            except Exception:
                logger.exception('Ошибка публикации событий Outbox')
                await asyncio.sleep(5)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

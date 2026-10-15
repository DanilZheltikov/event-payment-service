from faststream.rabbit import (
    ExchangeType,
    RabbitBroker,
    RabbitExchange,
    RabbitQueue
)

from .config import settings

broker = RabbitBroker(settings.rabbitmq_url)

dlx = RabbitExchange(
    name='payments.dlx',
    type=ExchangeType.DIRECT,
    durable=True,
)

dlq = RabbitQueue(
    name='payments.dlq',
    routing_key='dead',
    durable=True,
)

retry_2s_queue = RabbitQueue(
    name="payments.retry.2s",
    durable=True,
    arguments={
        "x-message-ttl": 2000,
        "x-dead-letter-exchange": "",
        "x-dead-letter-routing-key": "payments.new",
    },
)

retry_4s_queue = RabbitQueue(
    name="payments.retry.4s",
    durable=True,
    arguments={
        "x-message-ttl": 4000,
        "x-dead-letter-exchange": "",
        "x-dead-letter-routing-key": "payments.new",
    },
)

main_queue = RabbitQueue(
    name='payments.new',
    durable=True,
    arguments={
        'x-dead-letter-exchange': dlx.name,
        'x-dead-letter-routing-key': 'dead',
    },
)


async def setup_queues() -> None:
    exchange = await broker.declare_exchange(dlx)
    dead_queue = await broker.declare_queue(dlq)
    await broker.declare_queue(retry_2s_queue)
    await broker.declare_queue(retry_4s_queue)

    await dead_queue.bind(
        exchange=exchange,
        routing_key='dead',
    )

    await broker.declare_queue(main_queue)

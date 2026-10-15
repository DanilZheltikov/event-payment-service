from faststream import FastStream

from .handlers import error_middleware
from app.core.broker import broker, setup_queues
from app.processing import consumer # noqa

broker.add_middleware(error_middleware)

app = FastStream(broker)


@app.after_startup
async def declare_queues() -> None:
    await setup_queues()

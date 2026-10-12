from .models import Outbox
from app.db.repository import BaseRepository


class OutboxRepository(BaseRepository[Outbox]):
    """Репозиторий Outbox."""

    def __init__(self):
        super().__init__(Outbox)


outbox_repository = OutboxRepository()

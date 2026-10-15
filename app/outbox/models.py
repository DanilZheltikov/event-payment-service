from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class Outbox(UUIDMixin, TimestampMixin, Base):

    __tablename__ = 'outbox'

    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    routing_key: Mapped[str] = mapped_column(String(128), nullable=False)

    __table_args__ = (
        Index(
            'ix_outbox_unpublished',
            'created_at',
            postgresql_where=text('published_at IS NULL'),
        ),
        CheckConstraint(
            'attempts >= 0',
            name='check_outbox_attempts_non_negative'
        )
    )

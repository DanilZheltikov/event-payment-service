from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Numeric,
    String,
    text,
    UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .enums import Currency, PaymentStatus
from app.core.constants import (
    NAME_IDEMPOTENCY_KEY_CONSTRAINT,
    NAME_CHECK_AMOUNT_POSITIVE
)
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class Payment(UUIDMixin, TimestampMixin, Base):

    __tablename__ = 'payments'

    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2),
        nullable=False
    )
    currency: Mapped[Currency] = mapped_column(
        Enum(Currency, name='currency_enum'),
        nullable=False
    )
    description: Mapped[str] = mapped_column(String(140))
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(
            PaymentStatus,
            name='payment_status_enum',
            values_callable=lambda enum: [item.value for item in enum]
        ),
        nullable=False,
    )
    metadata_info: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        server_default=text("'{}'::jsonb"),
        nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(nullable=False)
    webhook_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            'idempotency_key',
            name=NAME_IDEMPOTENCY_KEY_CONSTRAINT,
        ),
        CheckConstraint(
            'amount > 0',
            name=NAME_CHECK_AMOUNT_POSITIVE
        )
    )

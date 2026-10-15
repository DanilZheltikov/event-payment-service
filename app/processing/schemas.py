from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.payments.enums import PaymentStatus


class PaymentPayload(BaseModel):
    payment_id: UUID


class PaymentResult(BaseModel):
    id: UUID
    status: PaymentStatus
    webhook_url: str

    model_config = ConfigDict(from_attributes=True)

import uuid

from fastapi import APIRouter, status

from .schemas import PaymentCreate, PaymentCreated, PaymentRead
from .service import payment_service
from app.dependencies import IdempotencyKeyDep, SessionDep

router = APIRouter()


@router.post(
    '',
    status_code=status.HTTP_202_ACCEPTED,
    response_model=PaymentCreated
)
async def create_payment(
    idempotency_key: IdempotencyKeyDep,
    session: SessionDep,
    payment: PaymentCreate
):
    created_payment = await payment_service.create_payment(
        session,
        payment,
        idempotency_key
    )
    return PaymentCreated(
        payment_id=created_payment.id,
        status=created_payment.status,
        created_at=created_payment.created_at
    )


@router.get('/{payment_id}', response_model=PaymentRead)
async def get_payment(session: SessionDep, payment_id: uuid.UUID):
    return PaymentRead.model_validate(
        await payment_service.get_payment_or_404(session, payment_id)
    )

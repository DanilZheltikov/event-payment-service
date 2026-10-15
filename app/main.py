from fastapi import Depends, FastAPI

from app.dependencies import verify_api_key
from app.payments.router import router as payment_router

app = FastAPI(title='Event Payment Service')

app.include_router(
    router=payment_router,
    prefix='/api/v1/payments',
    dependencies=[Depends(verify_api_key)],
    tags=['Payments']
)

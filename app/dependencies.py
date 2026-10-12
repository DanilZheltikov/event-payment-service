from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_async_session

api_key_header = APIKeyHeader(name='X-API-Key', auto_error=False)

SessionDep = Annotated[AsyncSession, Depends(get_async_session)]


def verify_api_key(api_key: str = Depends(api_key_header)) -> str:

    if not api_key or api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Invalid or missing API Key'
        )
    return api_key


def require_idempotency_key(
    idempotency_key: str | None = Header(None, alias='Idempotency-Key')
) -> str:

    if not idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Missing Idempotency-Key header'
        )
    return idempotency_key


IdempotencyKeyDep = Annotated[str, Depends(require_idempotency_key)]

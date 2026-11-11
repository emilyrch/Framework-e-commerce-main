import asyncio
from datetime import timezone

from fastapi import APIRouter, Depends, Request, Response
from pydantic import UUID4

from domain.errors import DomainError
from foundation.auth import internal_access
from foundation.storage import StorageError
from services.payments.models import AuthorizationRequest, AuthorizationResponse

router = APIRouter(prefix='/internal/v1/payments', tags=['simulated payments'], dependencies=[Depends(internal_access('orders'))])


@router.put('/by-order/{order_id}', response_model=AuthorizationResponse)
async def authorize(order_id: UUID4, body: AuthorizationRequest, request: Request, response: Response):
    if order_id != body.order_id:
        raise DomainError('PAYMENT_CONFLICT')
    try:
        result, created = await asyncio.to_thread(request.app.state.repository.authorize, body, request.app.state.clock().astimezone(timezone.utc))
    except StorageError:
        raise DomainError('PAYMENT_STORAGE_UNAVAILABLE') from None
    response.status_code = 201 if created else 200
    return result


@router.get('/by-order/{order_id}', response_model=AuthorizationResponse)
async def lookup(order_id: UUID4, request: Request):
    try:
        result = await asyncio.to_thread(request.app.state.repository.lookup, order_id)
    except StorageError:
        raise DomainError('PAYMENT_STORAGE_UNAVAILABLE') from None
    if result is None:
        raise DomainError('PAYMENT_NOT_FOUND')
    return result

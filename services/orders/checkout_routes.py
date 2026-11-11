from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from pydantic import UUID4

from foundation.errors import ApiError
from services.orders.checkout_models import AttemptResponse, OrderCommand, OrderResponse
from services.orders.routes import trusted_session

router = APIRouter(prefix='/internal/v1', tags=['orders'])


def key_value(value):
    if value is None: raise ApiError(400, 'IDEMPOTENCY_KEY_REQUIRED')
    try:
        parsed = UUID(value)
        if parsed.version != 4 or str(parsed) != value.lower(): raise ValueError
        return str(parsed)
    except (ValueError, AttributeError): raise ApiError(400, 'IDEMPOTENCY_KEY_INVALID') from None


@router.post('/orders', response_model=OrderResponse | AttemptResponse,
             openapi_extra={'parameters': [
                 {'name': 'Idempotency-Key', 'in': 'header', 'required': True, 'schema': {'type': 'string', 'format': 'uuid4'}},
                 {'name': 'X-Session-Owner', 'in': 'header', 'required': True, 'schema': {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}}]})
async def create_order(body: OrderCommand, request: Request, response: Response, owner=Depends(trusted_session)):
    keys = request.headers.getlist('idempotency-key')
    if len(keys) > 1: raise ApiError(400, 'IDEMPOTENCY_KEY_INVALID')
    key = key_value(keys[0] if keys else None)
    result, status = await request.app.state.checkout.submit(owner, key, body)
    response.status_code = status
    if status == 202: response.headers['Retry-After'] = '2'
    if isinstance(result, OrderResponse): response.headers['Location'] = '/internal/v1/orders/'+str(result.order_id)
    return result


@router.get('/orders/{order_id}', response_model=OrderResponse)
async def get_order(order_id: UUID4, request: Request, owner=Depends(trusted_session)):
    return await request.app.state.checkout.get_order(owner, order_id)


@router.get('/order-attempts/{key}', response_model=AttemptResponse)
async def get_attempt(key: str, request: Request, owner=Depends(trusted_session)):
    return await request.app.state.checkout.get_attempt(owner, key_value(key))

import re

from fastapi import APIRouter, Depends, Request

from foundation.auth import internal_access
from foundation.errors import ApiError
from services.orders.models import DeliverySlotsResponse, ReviewRequest, ReviewResponse, SESSION_OWNER_PATTERN

router = APIRouter(prefix='/internal/v1', tags=['reviews'])


async def trusted_session(request: Request, _access=Depends(internal_access('web'))):
    owners = request.headers.getlist('x-session-owner')
    if len(owners) != 1 or not re.fullmatch(SESSION_OWNER_PATTERN, owners[0]):
        raise ApiError(401, 'SESSION_REQUIRED')
    return owners[0]


@router.get('/delivery-slots', response_model=DeliverySlotsResponse, dependencies=[Depends(internal_access('web'))])
async def delivery_slots(request: Request):
    return request.app.state.reviews.delivery_slots()


@router.post('/reviews', response_model=ReviewResponse, status_code=201,
             openapi_extra={'parameters': [{'name': 'X-Session-Owner', 'in': 'header', 'required': True,
                                            'schema': {'type': 'string', 'pattern': SESSION_OWNER_PATTERN}}]})
async def create_review(body: ReviewRequest, request: Request, owner: str = Depends(trusted_session)):
    return await request.app.state.reviews.create_review(body, owner)

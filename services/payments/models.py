from typing import Literal

from pydantic import AwareDatetime, Field, UUID4

from domain.models import FrozenModel, Identifier, TrueFlag
from domain.pricing import MAX_TOTAL_CENTS


class AuthorizationRequest(FrozenModel):
    store_id: Identifier
    order_id: UUID4 = Field(strict=False)
    method: Literal['simulated_pix']
    currency: Literal['BRL']
    amount_cents: int = Field(strict=True, ge=1, le=MAX_TOTAL_CENTS)


class AuthorizationResponse(AuthorizationRequest):
    payment_id: UUID4 = Field(strict=False)
    simulated: TrueFlag
    status: Literal['approved']
    created_at: AwareDatetime

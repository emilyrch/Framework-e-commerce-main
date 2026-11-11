from typing import Literal

from pydantic import AwareDatetime, Field, UUID4

from domain.models import FrozenModel, Identifier, TrueFlag
from services.orders.models import ReviewedItem, ReviewTotals, ScheduledSnapshot, UnscheduledSnapshot


class OrderCommand(FrozenModel):
    store_id: Identifier
    review_id: UUID4 = Field(strict=False)


class Recovery(FrozenModel):
    action: Literal['none', 'wait', 'retry_same_key', 'investigate']
    next_retry_at: AwareDatetime | None = None


class OrderPayment(FrozenModel):
    payment_id: UUID4 | None = None
    method: Literal['simulated_pix'] = 'simulated_pix'
    simulated: TrueFlag = True
    status: Literal['approved', 'not_observed']
    amount_cents: int


class OrderResponse(FrozenModel):
    store_id: Identifier
    order_id: UUID4
    review_id: UUID4
    status: Literal['payment_pending', 'payment_unknown', 'confirmed', 'payment_conflict']
    created_at: AwareDatetime
    updated_at: AwareDatetime
    items: tuple[ReviewedItem, ...]
    delivery: ScheduledSnapshot | UnscheduledSnapshot
    totals: ReviewTotals
    payment: OrderPayment
    recovery: Recovery


class AttemptError(FrozenModel):
    code: str
    fields: tuple[dict[str, str], ...] = ()
    details: dict[str, str] | None = None


class AttemptResponse(FrozenModel):
    store_id: Identifier
    attempt_id: UUID4
    status: Literal['validating', 'accepted', 'rejected']
    order_id: UUID4 | None = None
    order_status: str | None = None
    recovery: Recovery
    error: AttemptError | None = None

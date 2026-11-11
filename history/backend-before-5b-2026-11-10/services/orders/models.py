from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, UUID4

from domain.delivery import Address, DeliveryWindow
from domain.models import (
    ClothingSelection, FoodSelection, FrozenModel, Identifier, ResolvedClothing,
    ResolvedFood, ResolvedItem, ResolvedList,
)
from domain.pricing import MAX_TOTAL_CENTS

SESSION_OWNER_PATTERN = r'^[a-f0-9]{64}$'
ConfigHash = Annotated[str, Field(pattern=SESSION_OWNER_PATTERN)]
CatalogRevision = Annotated[str, Field(pattern=r'^sha256:[a-f0-9]{64}$')]


class UnscheduledInput(FrozenModel):
    address: Address


class ScheduledInput(UnscheduledInput):
    slot_id: Annotated[str, Field(strict=True, min_length=1, max_length=200)]


class ClothingReviewRequest(FrozenModel):
    store_id: Identifier
    items: tuple[ClothingSelection, ...] = Field(strict=False, min_length=1, max_length=50)
    delivery: UnscheduledInput
    payment_method: Literal['simulated_pix']


class FoodReviewRequest(FrozenModel):
    store_id: Identifier
    items: tuple[FoodSelection, ...] = Field(strict=False, min_length=1, max_length=50)
    delivery: ScheduledInput
    payment_method: Literal['simulated_pix']


ReviewRequest = ClothingReviewRequest | FoodReviewRequest
REQUEST_TYPES = {'clothing': ClothingReviewRequest, 'food': FoodReviewRequest}


class CatalogResolution(ResolvedList):
    catalog_revision: CatalogRevision
    items: tuple[ResolvedItem, ...] = Field(strict=False, min_length=1, max_length=50)


class ReviewedClothing(ResolvedClothing):
    line_total_cents: int = Field(gt=0, le=1_000_000_000)


class ReviewedFood(ResolvedFood):
    line_total_cents: int = Field(gt=0, le=1_000_000_000)


ReviewedItem = Annotated[ReviewedClothing | ReviewedFood, Field(discriminator='kind')]
LINE_TYPES = {'clothing': ReviewedClothing, 'food': ReviewedFood}


class UnscheduledSnapshot(UnscheduledInput):
    shipping_cents: Literal[0]


class ScheduledSnapshot(UnscheduledSnapshot):
    slot: DeliveryWindow


class ReviewTotals(FrozenModel):
    currency: Literal['BRL']
    subtotal_cents: int = Field(gt=0, le=MAX_TOTAL_CENTS)
    shipping_cents: Literal[0]
    discount_cents: Literal[0]
    total_cents: int = Field(gt=0, le=MAX_TOTAL_CENTS)


class ReviewResponse(FrozenModel):
    store_id: Identifier
    review_id: UUID4
    config_hash: ConfigHash
    catalog_revision: CatalogRevision
    created_at: AwareDatetime
    expires_at: AwareDatetime
    items: tuple[ReviewedItem, ...]
    delivery: ScheduledSnapshot | UnscheduledSnapshot
    payment_method: Literal['simulated_pix']
    totals: ReviewTotals


class DeliverySlotsResponse(FrozenModel):
    store_id: Identifier
    timezone: Literal['America/Sao_Paulo']
    server_now: AwareDatetime
    items: tuple[DeliveryWindow, ...]

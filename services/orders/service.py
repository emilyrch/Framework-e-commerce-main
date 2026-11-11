import asyncio
from datetime import timedelta, timezone
from uuid import uuid4

from domain.composition import DomainComponents, compose
from domain.contracts import Clock
from domain.delivery import ABSENT, utc_now
from domain.errors import DomainError
from domain.models import ResolveRequest
from foundation.storage import StorageError
from foundation.config import StoreConfig
from services.orders.catalog_client import CatalogResolver
from services.orders.repository import OrdersRepository
from services.orders.models import DeliverySlotsResponse, LINE_TYPES, REQUEST_TYPES, ReviewRequest, ReviewResponse


class ReviewService:
    def __init__(self, config: StoreConfig, repository: OrdersRepository, catalog_client: CatalogResolver,
                 components: DomainComponents, clock: Clock = utc_now):
        self.config, self.repository, self.catalog_client, self.components, self.clock = config, repository, catalog_client, components, clock

    def _now(self):
        now = self.clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError('Clock must be aware')
        return now.astimezone(timezone.utc)

    def delivery_slots(self) -> DeliverySlotsResponse:
        now = self._now()
        delivery = compose(self.config, clock=lambda: now).delivery
        return DeliverySlotsResponse(store_id=self.config.store_id, timezone='America/Sao_Paulo', server_now=now, items=delivery.list_slots())

    async def create_review(self, body: ReviewRequest, session_owner: str) -> ReviewResponse:
        normalized, review = await self.build_review(body)
        try:
            await asyncio.to_thread(self.repository.save_review, session_owner, normalized, review)
        except StorageError:
            raise DomainError('ORDER_STORAGE_UNAVAILABLE') from None
        return review

    async def build_review(self, body: ReviewRequest):
        if body.store_id != self.config.store_id:
            raise DomainError('CONFIG_MISMATCH')
        if type(body) is not REQUEST_TYPES[self.config.domain]:
            raise DomainError('INPUT_INVALID')
        selected = tuple(sorted(body.items, key=lambda s: (s.product_id, getattr(s, 'combination_id', ''))))
        identities = [(s.product_id, getattr(s, 'combination_id', None)) for s in selected]
        if len(set(identities)) != len(identities):
            raise DomainError('DUPLICATE_LINE')
        resolved = await self.catalog_client.resolve(ResolveRequest(store_id=body.store_id, items=selected))
        now = self._now()  # Expiration and delivery are evaluated after HTTP, at snapshot creation.
        delivery = compose(self.config, clock=lambda: now).delivery.validate(body.delivery.address, getattr(body.delivery, 'slot_id', ABSENT))
        totals = self.components.totals.calculate(resolved.items)
        review = ReviewResponse(
            store_id=self.config.store_id, review_id=uuid4(), config_hash=self.config.config_hash,
            catalog_revision=resolved.catalog_revision, created_at=now, expires_at=now + timedelta(minutes=10),
            items=tuple(LINE_TYPES[line.item.kind](**line.item.model_dump(), line_total_cents=line.line_total_cents) for line in totals.lines),
            delivery=delivery.model_dump(exclude_none=True), payment_method=body.payment_method,
            totals=totals.model_dump(exclude={'lines'}),
        )
        normalized = body.model_copy(update={'items': selected})
        return normalized, review

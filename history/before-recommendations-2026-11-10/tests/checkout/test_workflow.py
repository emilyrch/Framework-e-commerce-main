import asyncio
import copy
import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from domain.composition import compose
from domain.errors import DomainError
from foundation.config import ROOT, load
from foundation.errors import ApiError
from foundation.storage import StorageError
from services.catalog.service import CatalogService
from services.orders.catalog_client import CatalogResolution
from services.orders.checkout import Checkout
from services.orders.checkout_models import OrderCommand
from services.orders.models import REQUEST_TYPES
from services.orders.repository import OrdersRepository
from services.orders.service import ReviewService
from services.payments.models import AuthorizationRequest
from services.payments.repository import PaymentsRepository
from tests.reviews.fixtures import NOW, OWNER, review_body


class Clock:
    def __init__(self): self.value = NOW
    def __call__(self): return self.value
    def advance(self, seconds): self.value += timedelta(seconds=seconds)


class Resolver:
    def __init__(self, catalog): self.catalog = catalog
    async def resolve(self, body):
        await asyncio.sleep(0)
        return CatalogResolution.model_validate_json(self.catalog.resolve(body).model_dump_json())


class Gateway:
    def __init__(self, repository, clock):
        self.repository, self.clock, self.puts, self.unavailable, self.lose_response = repository, clock, 0, False, False
    async def lookup(self, order_id, amount):
        if self.unavailable: raise DomainError('DEPENDENCY_UNAVAILABLE')
        response = self.repository.lookup(order_id)
        if response and response.amount_cents != amount: raise DomainError('PAYMENT_CONFLICT')
        return response
    async def authorize(self, order_id, amount):
        self.puts += 1
        body = AuthorizationRequest(store_id=self.repository.config.store_id, order_id=order_id, currency='BRL', method='simulated_pix', amount_cents=amount)
        result, _ = self.repository.authorize(body, self.clock())
        if self.lose_response:
            self.lose_response = False
            raise DomainError('DEPENDENCY_UNAVAILABLE')
        return result


class CheckoutTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.clock = Clock()

    async def setup_variant(self, variant='clothing'):
        self.config = load(ROOT/f'configurations/{variant}.json')
        components = compose(self.config, self.clock)
        self.repo = OrdersRepository(Path(self.temp.name)/variant/'orders', self.config); self.repo.initialize()
        self.pay = PaymentsRepository(Path(self.temp.name)/variant/'payments', self.config); self.pay.initialize()
        self.resolver = Resolver(CatalogService(components.catalog_loader.load(self.config), components.selection))
        self.reviews = ReviewService(self.config, self.repo, self.resolver, components, self.clock)
        self.gateway = Gateway(self.pay, self.clock)
        self.checkout = Checkout(self.config, self.repo, self.reviews, self.gateway, self.clock)
        review = await self.reviews.create_review(REQUEST_TYPES[variant].model_validate(review_body(variant)), OWNER)
        return OrderCommand(store_id=self.config.store_id, review_id=review.review_id)

    def count(self, repository, table):
        with repository.connection() as db: return db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]

    async def test_both_variants_confirm_replay_and_owner_isolation(self):
        for variant, total in [('clothing', 26970), ('food', 4970)]:
            command = await self.setup_variant(variant); key = str(uuid4())
            result, status = await self.checkout.submit(OWNER, key, command)
            self.assertEqual(status, 201); self.assertEqual(result.status, 'confirmed')
            self.assertEqual(result.totals.total_cents, total)
            self.clock.advance(900)  # Admitted replay must not expire/revalidate.
            replay, status = await self.checkout.submit(OWNER, key, command)
            self.assertEqual(status, 200); self.assertEqual(replay, result)
            with self.assertRaises(DomainError) as error: await self.checkout.get_order('b'*64, result.order_id)
            self.assertEqual(error.exception.code, 'ORDER_NOT_FOUND')
            with self.assertRaises(DomainError): await self.checkout.get_attempt('b'*64, key)
            self.assertEqual(self.count(self.pay, 'authorizations'), 1)
            self.assertEqual(self.count(self.repo, 'orders'), 1)
            self.assertEqual(self.count(self.repo, 'reviews'), 1)

    async def test_same_key_different_content_and_review_consumed_once(self):
        command = await self.setup_variant(); key = str(uuid4())
        order, _ = await self.checkout.submit(OWNER, key, command)
        with self.assertRaises(DomainError) as error:
            await self.checkout.submit(OWNER, key, OrderCommand(store_id=self.config.store_id, review_id=uuid4()))
        self.assertEqual(error.exception.code, 'IDEMPOTENCY_KEY_REUSED')
        with self.assertRaises(ApiError) as error: await self.checkout.submit(OWNER, str(uuid4()), command)
        self.assertEqual(error.exception.code, 'REVIEW_ALREADY_USED')
        self.assertEqual(error.exception.details['order_id'], str(order.order_id))
        self.assertEqual(self.count(self.repo, 'orders'), 1)

    async def test_concurrent_same_key_and_different_keys(self):
        command = await self.setup_variant(); key = str(uuid4())
        results = await asyncio.gather(*(self.checkout.submit(OWNER, key, command) for _ in range(8)))
        self.assertEqual(self.count(self.repo, 'attempts'), 1)
        self.assertEqual(self.count(self.repo, 'orders'), 1)
        self.assertEqual(self.count(self.pay, 'authorizations'), 1)
        ids = {str(r.order_id) for r, _ in results if getattr(r, 'order_id', None)}
        self.assertEqual(len(ids), 1)
        command = OrderCommand(store_id=self.config.store_id, review_id=(await self.reviews.create_review(REQUEST_TYPES['clothing'].model_validate(review_body('clothing')), OWNER)).review_id)
        results = await asyncio.gather(*(self.checkout.submit(OWNER, str(uuid4()), command) for _ in range(4)), return_exceptions=True)
        self.assertEqual(self.count(self.repo, 'orders'), 2)
        self.assertEqual(self.count(self.pay, 'authorizations'), 2)

    async def test_expired_changed_price_and_rejections_are_durable(self):
        command = await self.setup_variant(); key = str(uuid4()); self.clock.advance(600)
        for _ in range(2):
            with self.assertRaises(ApiError) as error: await self.checkout.submit(OWNER, key, command)
            self.assertEqual(error.exception.code, 'REVIEW_EXPIRED')
        self.assertEqual(self.count(self.repo, 'attempts'), 1)
        review = await self.reviews.create_review(REQUEST_TYPES['clothing'].model_validate(review_body('clothing')), OWNER)
        raw = self.resolver.catalog.snapshot.data.model_dump(mode='json'); raw['products'][0]['price_cents'] += 10
        cp = compose(self.config, self.clock)
        self.resolver.catalog = CatalogService(cp.catalog_loader.validate(raw, self.config), cp.selection)
        with self.assertRaises(ApiError) as error:
            await self.checkout.submit(OWNER, str(uuid4()), OrderCommand(store_id=self.config.store_id, review_id=review.review_id))
        self.assertEqual(error.exception.code, 'REVIEW_CHANGED')
        self.assertEqual(self.count(self.repo, 'orders'), 0); self.assertEqual(self.count(self.pay, 'authorizations'), 0)

    async def test_window_expires_before_admission_but_not_after(self):
        self.clock.value = NOW.replace(hour=8, minute=59)
        command = await self.setup_variant('food'); self.clock.advance(60)
        with self.assertRaises(ApiError) as error: await self.checkout.submit(OWNER, str(uuid4()), command)
        self.assertEqual(error.exception.code, 'DELIVERY_SLOT_EXPIRED')

    async def test_lost_authorization_reply_and_restart_recover_same_payment(self):
        command = await self.setup_variant('food'); key = str(uuid4()); self.gateway.lose_response = True
        pending, status = await self.checkout.submit(OWNER, key, command)
        self.assertEqual(status, 202); self.assertEqual(pending.status, 'payment_unknown')
        self.assertEqual(self.count(self.pay, 'authorizations'), 1)
        self.clock.advance(86400)  # Old review/window do not invalidate an admitted order.
        self.repo.initialize(); self.pay.initialize()
        restarted = Checkout(self.config, self.repo, self.reviews, self.gateway, self.clock)
        await restarted.recover_batch()
        recovered = await restarted.get_order(OWNER, pending.order_id)
        self.assertEqual(recovered.status, 'confirmed')
        self.assertEqual(self.gateway.puts, 1)

    async def test_failure_before_admission_or_confirmation_never_duplicates(self):
        command = await self.setup_variant(); key = str(uuid4())
        original = self.repo.admit
        self.repo.admit = lambda *args: (_ for _ in ()).throw(StorageError('test'))
        with self.assertRaises(DomainError): await self.checkout.submit(OWNER, key, command)
        self.assertEqual(self.count(self.repo, 'orders'), 0); self.assertEqual(self.gateway.puts, 0)
        self.repo.admit = original; self.clock.advance(16)
        finish = self.repo.finish_payment
        self.repo.finish_payment = lambda *args, **kwargs: (_ for _ in ()).throw(StorageError('test'))
        with self.assertRaises(DomainError): await self.checkout.recover_batch()
        self.assertEqual(self.count(self.repo, 'orders'), 1); self.assertEqual(self.count(self.pay, 'authorizations'), 1)
        self.repo.finish_payment = finish; self.clock.advance(16)
        await self.checkout.recover_batch()
        attempt = await self.checkout.get_attempt(OWNER, key)
        self.assertEqual((await self.checkout.get_order(OWNER, attempt.order_id)).status, 'confirmed')
        self.assertEqual(self.gateway.puts, 1)

    async def test_five_attempts_cooldown_manual_resume_and_get_has_no_effect(self):
        command = await self.setup_variant(); key = str(uuid4()); self.gateway.unavailable = True
        order, _ = await self.checkout.submit(OWNER, key, command)
        for seconds in [2, 4, 8, 16]: self.clock.advance(seconds); await self.checkout.recover_batch()
        self.assertEqual(self.repo.record('orders', str(order.order_id))['retry_count'], 5)
        self.clock.advance(31); await self.checkout.recover_batch()
        await self.checkout.get_order(OWNER, order.order_id); await self.checkout.get_attempt(OWNER, key)
        self.assertEqual(self.repo.record('orders', str(order.order_id))['retry_count'], 5)
        self.gateway.unavailable = False
        result, _ = await self.checkout.submit(OWNER, key, command)
        self.assertEqual(result.status, 'confirmed'); self.assertEqual(self.count(self.repo, 'orders'), 1)

    async def test_lease_fencing_and_payment_conflict(self):
        command = await self.setup_variant(); key = str(uuid4())
        attempt, _ = self.repo.reserve(OWNER, key, command, self.checkout.now())
        old = self.repo.claim('attempts', attempt['attempt_id'], self.checkout.now())
        self.clock.advance(16)
        current = self.repo.claim('attempts', attempt['attempt_id'], self.checkout.now())
        source = self.repo.review(OWNER, command.review_id)
        from services.orders.models import ReviewResponse
        review = ReviewResponse.model_validate_json(source['snapshot_json'])
        self.assertIsNone(self.repo.admit(old, review, self.checkout.now()))
        order = self.repo.admit(current, review, self.checkout.now())
        self.pay.authorize(AuthorizationRequest(store_id=self.config.store_id, order_id=order['order_id'], method='simulated_pix', currency='BRL', amount_cents=1), self.clock())
        await self.checkout.drive_order(order['order_id'])
        result = await self.checkout.get_order(OWNER, order['order_id'])
        self.assertEqual(result.status, 'payment_conflict'); self.assertEqual(result.recovery.action, 'investigate')

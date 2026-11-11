import json
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from domain.composition import compose
from domain.errors import DomainError
from domain.models import ResolveRequest
from foundation.config import ROOT, load
from services.catalog.service import CatalogService
from services.orders.models import CatalogResolution, REQUEST_TYPES, ReviewResponse
from services.orders.repository import OrdersRepository
from services.orders.service import ReviewService
from tests.reviews.fixtures import NOW, OWNER, review_body


class ReviewServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def service(self, variant):
        config = load(ROOT/f'configurations/{variant}.json')
        components = compose(config, clock=lambda: NOW)
        repository = OrdersRepository(Path(self.temp.name)/variant, config); repository.initialize()
        catalog = CatalogService(components.catalog_loader.load(config), components.selection)
        class Resolver:
            async def resolve(self, request):
                # A second writer can acquire a lock during HTTP's slot in the flow.
                with repository.connection() as db:
                    db.execute('BEGIN IMMEDIATE'); db.rollback()
                return CatalogResolution.model_validate_json(catalog.resolve(request).model_dump_json())
        service = ReviewService(config, repository, Resolver(), components, clock=lambda: NOW)
        return service, repository

    async def test_snapshot_expiration_immutability_and_restart(self):
        for variant, total in [('clothing', 26970), ('food', 4970)]:
            with self.subTest(variant=variant):
                service, repo = self.service(variant)
                request = REQUEST_TYPES[variant].model_validate(review_body(variant))
                response = await service.create_review(request, OWNER)
                self.assertEqual(response.totals.total_cents, total)
                self.assertEqual(response.expires_at - response.created_at, timedelta(minutes=10))
                self.assertEqual(response.review_id.version, 4)
                with self.assertRaises(ValidationError): response.totals.total_cents = 1
                repo.initialize()
                with repo.connection() as db:
                    stored = db.execute('SELECT session_owner,snapshot_json,input_json FROM reviews').fetchone()
                    self.assertEqual(stored[0], OWNER)
                    self.assertEqual(ReviewResponse.model_validate_json(stored[1]), response)
                    self.assertNotIn('session_owner', json.loads(stored[2]))
                    self.assertEqual(db.execute('SELECT count(*) FROM orders').fetchone()[0], 0)
                    self.assertEqual(db.execute('SELECT count(*) FROM attempts').fetchone()[0], 0)
                if variant == 'food':
                    raw = response.model_dump(mode='json')
                    granola = next(i for i in raw['items'] if i['product_id'] == 'granola')
                    self.assertIsNone(granola['food_information']['allergens']['contains'])
                    self.assertEqual(response.delivery.slot.id, review_body('food')['delivery']['slot_id'])

    async def test_storage_commit_failure_rolls_back_and_never_succeeds(self):
        service, repo = self.service('clothing')
        original = repo.connection
        class BrokenCommit:
            def __init__(self, connection): self.connection = connection
            def execute(self, *args): return self.connection.execute(*args)
            def commit(self): raise sqlite3.OperationalError('private storage detail')
        @contextmanager
        def failure():
            with original() as db: yield BrokenCommit(db)
        # Resolve first against a typed fixture; the injected commit error occurs only at persistence.
        resolved = await service.catalog_client.resolve(ResolveRequest.model_validate({
            'store_id': 'roupas-demo', 'items': review_body('clothing')['items']}))
        class Resolver:
            async def resolve(self, request): return resolved
        service.catalog_client = Resolver()
        with patch.object(repo, 'connection', failure):
            with self.assertRaises(DomainError) as error:
                await service.create_review(REQUEST_TYPES['clothing'].model_validate(review_body('clothing')), OWNER)
        self.assertEqual(error.exception.code, 'ORDER_STORAGE_UNAVAILABLE')
        with repo.connection() as db: self.assertEqual(db.execute('SELECT count(*) FROM reviews').fetchone()[0], 0)

    async def test_slot_failure_and_duplicates_do_not_persist(self):
        service, repo = self.service('food')
        for slot in ['food-windows-v1:2026-11-08:morning', 'food-windows-v1:2026-11-09:missing']:
            body = review_body('food'); body['delivery']['slot_id'] = slot
            with self.assertRaises(DomainError): await service.create_review(REQUEST_TYPES['food'].model_validate(body), OWNER)
        body = review_body('food'); body['items'].append(body['items'][0])
        with self.assertRaises(DomainError): await service.create_review(REQUEST_TYPES['food'].model_validate(body), OWNER)
        with repo.connection() as db: self.assertEqual(db.execute('SELECT count(*) FROM reviews').fetchone()[0], 0)

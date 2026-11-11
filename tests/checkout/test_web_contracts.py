"""Real Python DTOs -> Node validator. No sockets or browser rendering."""
import json
import shutil
import subprocess
import unittest
from uuid import uuid4

from foundation.config import ROOT
from tests.checkout import test_offline as offline
from tests.reviews.fixtures import OWNER


class WebContractTests(unittest.TestCase):
    def test_real_dtos_for_both_variants(self):
        node = shutil.which('node')
        if node is None:
            self.skipTest('Node unavailable: cross-language contract check not executed')
        harness = offline.OfflineBusinessTests()
        harness.setUp()
        self.addCleanup(harness.doCleanups)
        spec, cases = harness.spec, []
        for variant in ['clothing', 'food']:
            command = offline.run_inline(spec.setup_variant(variant))
            catalog = spec.resolver.catalog
            def add(route, model):
                cases.append({'route': route, 'body': model.model_dump(mode='json'), 'store': spec.config.store_id, 'domain': variant})
            add('products', catalog.list_products())
            for product in catalog.snapshot.products:
                add('products/'+product, catalog.detail(product))
            review = spec.repo.review(OWNER, command.review_id)
            from services.orders.models import ReviewResponse
            add('reviews', ReviewResponse.model_validate_json(review['snapshot_json']))
            key = str(uuid4())
            result, _ = offline.run_inline(spec.checkout.submit(OWNER, key, command))
            add('orders', result)
            add('order-attempts/'+key, offline.run_inline(spec.checkout.get_attempt(OWNER, key)))
            from domain.models import CatalogCandidates
            from services.recommendations.models import ProfileResponse,Preferences,EventResponse,ResetResponse
            from services.recommendations.service import RecommendationService
            from services.recommendations.ranking import rank
            candidates=CatalogCandidates(store_id=spec.config.store_id,catalog_revision=catalog.snapshot.catalog_revision,items=tuple(catalog.snapshot.products.values()))
            add('preferences',ProfileResponse(store_id=spec.config.store_id,profile=Preferences(),options=RecommendationService.options(candidates),history_count=0))
            add('recommendations',rank(candidates,Preferences(),[]))
            add('recommendation-events',EventResponse(store_id=spec.config.store_id,event_id=uuid4(),saved=True))
            add('recommendation-reset',ResetResponse(store_id=spec.config.store_id))
            if variant == 'food':
                add('delivery-slots', spec.reviews.delivery_slots())
        result = subprocess.run([node, '--experimental-strip-types', 'apps/store-ropa/scripts/check-wire.ts'],
                                cwd=ROOT, input=json.dumps(cases), capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

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
            if variant == 'food':
                add('delivery-slots', spec.reviews.delivery_slots())
        result = subprocess.run([node, '--experimental-strip-types', 'apps/store-ropa/scripts/check-wire.ts'],
                                cwd=ROOT, input=json.dumps(cases), capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

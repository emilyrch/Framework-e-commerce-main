import json
import unittest
from uuid import uuid4

from domain.errors import DomainError
from foundation.config import ROOT, load
from services.orders.catalog_client import HttpResult
from services.orders.payment_client import SimulatedPaymentGateway
from tests.checkout.test_offline import run_inline
from tests.reviews.fixtures import NOW


class PaymentWireOfflineTests(unittest.TestCase):
    def setUp(self):
        self.config=load(ROOT/'configurations/clothing.json');self.order_id=str(uuid4())
        self.headers={'x-store-id':self.config.store_id,'x-config-hash':self.config.config_hash,'content-type':'application/json'}
        self.payload={'store_id':self.config.store_id,'order_id':self.order_id,'payment_id':str(uuid4()),'method':'simulated_pix',
                      'currency':'BRL','amount_cents':100,'simulated':True,'status':'approved','created_at':NOW.isoformat()}

    def gateway(self, payload, status=200):
        outer=self
        class Transport:
            calls=[]
            async def request(self, method, url, headers, body, timeout):
                self.calls.append((method,body,timeout))
                return HttpResult(status,outer.headers,json.dumps(payload).encode())
        return SimulatedPaymentGateway(self.config,'http://127.0.0.1','fake-token',Transport())

    def test_required_approval_fields_and_amount_identity(self):
        # Timeout wrappers execute inline here; this tests decoding, not network/deadlines.
        from unittest.mock import patch
        from tests.checkout.test_offline import inline_wait
        with patch('asyncio.wait_for',inline_wait):
            approved=run_inline(self.gateway(self.payload).lookup(self.order_id,100))
            self.assertEqual(approved.amount_cents,100)
            for key in ['status','simulated','payment_id']:
                payload=dict(self.payload);payload.pop(key)
                with self.subTest(missing=key),self.assertRaises(DomainError) as error:
                    run_inline(self.gateway(payload).lookup(self.order_id,100))
                self.assertEqual(error.exception.code,'PAYMENT_RESPONSE_INVALID')
            payload=dict(self.payload);payload['amount_cents']=101
            with self.assertRaises(DomainError) as error:run_inline(self.gateway(payload).lookup(self.order_id,100))
            self.assertEqual(error.exception.code,'PAYMENT_CONFLICT')

    def test_only_explicit_not_found_allows_absence(self):
        from unittest.mock import patch
        from tests.checkout.test_offline import inline_wait
        with patch('asyncio.wait_for',inline_wait):
            self.assertIsNone(run_inline(self.gateway({'error':{'code':'PAYMENT_NOT_FOUND'}},404).lookup(self.order_id,100)))
            with self.assertRaises(DomainError):run_inline(self.gateway({'error':{'code':'OTHER'}},404).lookup(self.order_id,100))

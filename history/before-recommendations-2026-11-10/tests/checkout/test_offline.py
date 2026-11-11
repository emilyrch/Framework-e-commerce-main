"""Testes sem sockets. Adaptadores de execução inline NÃO validam asyncio/HTTP/worker.

Reutilizam as especificações de negócio com bancos SQLite reais, relógio controlado
e portas de catálogo/pagamento locais. A suíte assíncrona continua separada.
"""
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from uuid import uuid4

from services.orders.models import ReviewResponse
from services.payments.models import AuthorizationRequest
from tests.checkout import test_workflow as specs


async def inline_thread(function, *args, **kwargs):
    return function(*args, **kwargs)


async def inline_wait(awaitable, timeout):
    return await awaitable


async def no_sleep(delay):
    return None


def run_inline(awaitable):
    """Only immediate/mocked awaits; fail if a real I/O awaitable is encountered."""
    try:
        while True:
            value = awaitable.send(None)
            if value is not None:
                raise AssertionError('Real asynchronous I/O is not supported by this offline harness')
    except StopIteration as result:
        return result.value
    finally:
        awaitable.close()


class OfflineBusinessTests(unittest.TestCase):
    def setUp(self):
        self.spec = specs.CheckoutTests()
        self.spec.setUp()
        self.addCleanup(self.spec.temp.cleanup)
        for name, value in [('to_thread', inline_thread), ('wait_for', inline_wait), ('sleep', no_sleep)]:
            context = patch('asyncio.'+name, value); context.start(); self.addCleanup(context.stop)

    def test_business_specs_with_real_sqlite_and_inline_adapters(self):
        for name in [
            'test_both_variants_confirm_replay_and_owner_isolation',
            'test_same_key_different_content_and_review_consumed_once',
            'test_expired_changed_price_and_rejections_are_durable',
            'test_window_expires_before_admission_but_not_after',
            'test_lost_authorization_reply_and_restart_recover_same_payment',
            'test_failure_before_admission_or_confirmation_never_duplicates',
            'test_five_attempts_cooldown_manual_resume_and_get_has_no_effect',
            'test_lease_fencing_and_payment_conflict',
        ]:
            with self.subTest(spec=name):
                spec = specs.CheckoutTests(); spec.setUp()
                try: run_inline(getattr(spec, name)())
                finally: spec.temp.cleanup()

    def test_real_sqlite_concurrent_payment_and_attempt_uniqueness(self):
        command = run_inline(self.spec.setup_variant())
        request = AuthorizationRequest(store_id=self.spec.config.store_id, order_id=uuid4(), method='simulated_pix', currency='BRL', amount_cents=100)
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(lambda _: self.spec.pay.authorize(request, self.spec.clock()), range(12)))
        self.assertEqual(len({str(result.payment_id) for result, _ in results}), 1)
        self.assertEqual(sum(created for _, created in results), 1)
        key = str(uuid4())
        from tests.reviews.fixtures import OWNER
        with ThreadPoolExecutor(max_workers=6) as pool:
            attempts = list(pool.map(lambda _: self.spec.repo.reserve(OWNER, key, command, self.spec.checkout.now()), range(12)))
        self.assertEqual(len({row['attempt_id'] for row, _ in attempts}), 1)
        self.assertEqual(sum(created for _, created in attempts), 1)
        attempt_id = attempts[0][0]['attempt_id']
        with ThreadPoolExecutor(max_workers=6) as pool:
            claims = list(pool.map(lambda _: self.spec.repo.claim('attempts', attempt_id, self.spec.checkout.now()), range(12)))
        self.assertEqual(sum(claim is not None for claim in claims), 1)

    def test_two_keys_racing_for_same_review_are_atomic(self):
        command = run_inline(self.spec.setup_variant())
        from tests.reviews.fixtures import OWNER
        claims = []
        for _ in range(2):
            row, _ = self.spec.repo.reserve(OWNER, str(uuid4()), command, self.spec.checkout.now())
            claims.append(self.spec.repo.claim('attempts', row['attempt_id'], self.spec.checkout.now()))
        snapshot = ReviewResponse.model_validate_json(self.spec.repo.review(OWNER, command.review_id)['snapshot_json'])
        with ThreadPoolExecutor(max_workers=2) as pool:
            orders = list(pool.map(lambda claim: self.spec.repo.admit(claim, snapshot, self.spec.checkout.now()), claims))
        self.assertEqual(sum(order is not None for order in orders), 1)
        self.assertEqual(self.spec.count(self.spec.repo, 'orders'), 1)
        self.assertEqual(self.spec.count(self.spec.repo, 'attempts'), 2)

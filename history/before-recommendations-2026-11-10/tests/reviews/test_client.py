import asyncio
import copy
import json
import unittest

from domain.composition import compose
from domain.errors import DomainError
from domain.models import ResolveRequest
from foundation.config import ROOT, load
from services.catalog.service import CatalogService
from services.orders.catalog_client import CatalogClient, HttpResult


class Transport:
    def __init__(self, results):
        self.results, self.calls = list(results), []

    async def post(self, url, headers, body, timeout):
        self.calls.append((url, headers, json.loads(body), timeout))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class CatalogClientTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.config = load(ROOT/'configurations/clothing.json')
        components = compose(self.config)
        self.request = ResolveRequest.model_validate({'store_id': self.config.store_id, 'items': [
            {'product_id': 'camiseta', 'quantity': 1, 'combination_id': 'camiseta-m-preta'}]})
        self.body = CatalogService(components.catalog_loader.load(self.config), components.selection).resolve(self.request).model_dump(mode='json')
        self.headers = {'x-store-id': self.config.store_id, 'x-config-hash': self.config.config_hash, 'content-type': 'application/json'}

    def response(self, body=None, status=200, headers=None):
        return HttpResult(status, headers or self.headers, json.dumps(self.body if body is None else body).encode())

    def client(self, responses):
        transport = Transport(responses)
        return CatalogClient(self.config, 'http://127.0.0.1:8001', 'fake-test-token', transport, retry_delay=0), transport

    async def test_typed_response_and_outgoing_contract(self):
        client, transport = self.client([self.response()])
        result = await client.resolve(self.request)
        self.assertEqual(result.items[0].quantity, 1)
        url, headers, body, timeout = transport.calls[0]
        self.assertTrue(url.endswith('/internal/v1/selections/resolve'))
        self.assertEqual(headers['X-Config-Hash'], self.config.config_hash)
        self.assertEqual(headers['Authorization'], 'Bearer fake-test-token')
        self.assertNotIn('X-Session-Owner', headers)
        self.assertEqual(set(body), {'store_id', 'items'})
        self.assertEqual(timeout, 1.5)

    async def test_bounded_retries_and_non_retryable_failures(self):
        for first in [OSError(), self.response({}, 503)]:
            client, transport = self.client([first, self.response()])
            await client.resolve(self.request)
            self.assertEqual(len(transport.calls), 2)
        client, transport = self.client([OSError(), OSError(), self.response()])
        with self.assertRaises(DomainError) as error:
            await client.resolve(self.request)
        self.assertEqual(error.exception.code, 'DEPENDENCY_UNAVAILABLE')
        self.assertEqual(len(transport.calls), 2)
        for status in [401, 403, 302, 404]:
            client, transport = self.client([self.response({}, status)])
            with self.assertRaises(DomainError): await client.resolve(self.request)
            self.assertEqual(len(transport.calls), 1)

    async def test_timeout_budget_without_long_wait(self):
        class Hanging:
            calls = 0
            async def post(self, *args):
                self.calls += 1
                await asyncio.Event().wait()
        transport = Hanging()
        client = CatalogClient(self.config, 'http://127.0.0.1', 'test', transport, timeout=0.01, retry_delay=0)
        with self.assertRaises(DomainError): await client.resolve(self.request)
        self.assertEqual(transport.calls, 2)

    async def test_invalid_responses_identity_shape_and_selection(self):
        mutated = []
        for mutate in [lambda b: b.update(items=[]), lambda b: b['items'][0].update(quantity=2),
                       lambda b: b['items'][0].update(unit_price_cents=True),
                       lambda b: b['items'][0].update(unit_price_cents=1.5),
                       lambda b: b['items'][0].update(product_id='other'),
                       lambda b: b['items'][0]['combination'].update(id='other-combination'),
                       lambda b: b.update(items=b['items'] * 2), lambda b: b.update(catalog_revision='bad'),
                       lambda b: b.update(extra='private-content')]:
            body = copy.deepcopy(self.body); mutate(body); mutated.append(self.response(body))
        mutated += [HttpResult(200, self.headers, b'{bad'), self.response(headers={**self.headers, 'content-type': 'text/plain'})]
        mutated.append(HttpResult(200, {'content-type': 'application/json'}, json.dumps(self.body).encode()))
        for response in mutated:
            with self.subTest(response=response.status):
                client, transport = self.client([response])
                with self.assertRaises(DomainError) as error: await client.resolve(self.request)
                self.assertEqual(error.exception.code, 'CATALOG_RESPONSE_INVALID')
                self.assertEqual(len(transport.calls), 1)
        body = copy.deepcopy(self.body); body['store_id'] = 'other-store'
        for response in [self.response(body), self.response(headers={**self.headers, 'x-config-hash': '0'*64})]:
            client, _ = self.client([response])
            with self.assertRaises(DomainError) as error: await client.resolve(self.request)
            self.assertEqual(error.exception.code, 'CONFIG_MISMATCH')

    async def test_sanitized_catalog_errors(self):
        error = {'error': {'code': 'SELECTION_INVALID', 'message': 'untrusted private text',
                           'fields': [{'path': 'items.0.combination_id', 'code': 'invalid_combination'}]}}
        client, _ = self.client([self.response(error, 422)])
        with self.assertRaises(DomainError) as caught: await client.resolve(self.request)
        self.assertEqual(caught.exception.code, 'SELECTION_INVALID')
        self.assertNotIn('untrusted', str(caught.exception))
        error['error']['fields'][0]['path'] = 'private/address'
        client, _ = self.client([self.response(error, 422)])
        with self.assertRaises(DomainError) as caught: await client.resolve(self.request)
        self.assertEqual(caught.exception.code, 'CATALOG_RESPONSE_INVALID')

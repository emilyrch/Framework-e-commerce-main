import copy
import json
import os
import secrets
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import closing
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from foundation.config import ROOT, load
from tests.reviews.fixtures import NOW, OWNER, review_body


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def stop(process):
    if process.poll() is None:
        if os.name == 'nt':
            try: process.send_signal(signal.CTRL_BREAK_EVENT)
            except OSError: pass
        else: process.terminate()
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            if os.name == 'nt': subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True, timeout=5)
            else: process.kill()
            process.wait(timeout=5)


class FaultServer:
    """Infraestrutura negativa de teste, não substitui o catálogo real nos cenários válidos."""
    def __init__(self, config):
        self.config, self.mode, self.calls, self.targets = config, 'malformed', 0, 0
        parent = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                parent.targets += 1
                self.send_response(500); self.end_headers()
            def do_POST(self):
                parent.calls += 1
                self.rfile.read(int(self.headers.get('Content-Length', '0')))
                if parent.mode == 'redirect':
                    self.send_response(302); self.send_header('Location', '/redirect-target'); self.end_headers(); return
                self.send_response(503 if parent.mode == 'unavailable' else 200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('X-Store-Id', parent.config.store_id)
                self.send_header('X-Config-Hash', '0'*64 if parent.mode == 'identity' else parent.config.config_hash)
                self.end_headers(); self.wfile.write(b'{malformed response')
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()

    @property
    def url(self): return f'http://127.0.0.1:{self.server.server_port}'

    def close(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=2)


class ReviewHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.temporary.cleanup)
        cls.directory = Path(cls.temporary.name); cls.stores = {}
        for variant in ['clothing', 'food']:
            raw = json.loads((ROOT/f'configurations/{variant}.json').read_text())
            if variant == 'food': raw['delivery']['schedule']['daily_windows'][1]['enabled'] = False
            manifest = cls.directory/(variant+'.json'); manifest.write_text(json.dumps(raw), encoding='utf-8')
            config = load(manifest)
            catalog_port, orders_port = free_port(), free_port()
            env = os.environ.copy()
            env.update(PRODUCT_CONFIG=str(manifest), CATALOG_URL=f'http://127.0.0.1:{catalog_port}',
                       DATA_DIR=str(cls.directory/variant/'orders'), TEST_CLOCK=NOW.isoformat(),
                       WEB_CATALOG_TOKEN=secrets.token_hex(32), ORDERS_CATALOG_TOKEN=secrets.token_hex(32),
                       WEB_ORDERS_TOKEN=secrets.token_hex(32))
            env.pop('ORDERS_PAYMENTS_TOKEN', None)
            cls.stores[variant] = {'config': config, 'env': env, 'ports': {'catalog': catalog_port, 'orders': orders_port}, 'processes': {}, 'logs': {}}
            cls.addClassCleanup(cls.stop_store, variant)
            cls.start(variant, 'catalog'); cls.start(variant, 'orders')

    @classmethod
    def start(cls, variant, service):
        store = cls.stores[variant]; env = store['env'].copy()
        env['CATALOG_DATA_ROOT'] = str(ROOT/'demo-data') if service == 'catalog' else str(cls.directory/'does-not-exist')
        log = (cls.directory/f'{variant}-{service}.log').open('ab'); store['logs'][service] = log
        target = ['services.catalog.app:app'] if service == 'catalog' else ['tests.reviews.server:create_app', '--factory']
        process = subprocess.Popen([sys.executable, '-m', 'uvicorn', *target, '--host', '127.0.0.1', '--port', str(store['ports'][service])],
            cwd=ROOT, env=env, stdout=log, stderr=log, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0)
        store['processes'][service] = process
        for _ in range(100):
            if process.poll() is not None: raise AssertionError('Test service failed startup: '+service)
            try:
                if cls.call(variant, '/health/live', service=service)[0] == 200: return
            except OSError: pass
            time.sleep(0.05)
        raise AssertionError('Service not live')

    @classmethod
    def stop_service(cls, variant, service):
        store = cls.stores[variant]
        if service in store['processes']:
            stop(store['processes'].pop(service)); store['logs'].pop(service).close()

    @classmethod
    def stop_store(cls, variant):
        for service in list(cls.stores[variant]['processes']): cls.stop_service(variant, service)

    @classmethod
    def call(cls, variant, path, body=None, owner=OWNER, headers=None, method=None, service='orders', raw=None):
        store = cls.stores[variant]
        request_headers = {'Authorization': 'Bearer '+store['env']['WEB_'+service.upper()+'_TOKEN'],
                           'X-Store-Id': store['config'].store_id, 'X-Config-Hash': store['config'].config_hash}
        if owner is not None: request_headers['X-Session-Owner'] = owner
        if body is not None: raw = json.dumps(body).encode(); request_headers['Content-Type'] = 'application/json'
        if headers:
            for key, value in headers.items():
                if value is None: request_headers.pop(key, None)
                else: request_headers[key] = value
        request = Request(f'http://127.0.0.1:{store["ports"][service]}'+path, data=raw, headers=request_headers, method=method)
        try: response = build_opener(ProxyHandler({})).open(request, timeout=6)
        except HTTPError as exc: response = exc
        with response: return response.status, json.load(response), {k.lower(): v for k, v in response.headers.items()}

    def rows(self, variant):
        with closing(sqlite3.connect(self.stores[variant]['env']['DATA_DIR']+'/orders.sqlite')) as db:
            return db.execute('SELECT review_id,session_owner,snapshot_json,input_json,config_hash FROM reviews ORDER BY review_id').fetchall()

    def test_valid_reviews_both_domains_snapshot_and_no_other_effects(self):
        for variant, total in [('clothing', 26970), ('food', 4970)]:
            status, review, headers = self.call(variant, '/internal/v1/reviews', review_body(variant))
            self.assertEqual(status, 201, review)
            self.assertEqual(review['totals']['total_cents'], total)
            self.assertEqual(headers['cache-control'], 'no-store')
            self.assertNotIn('session_owner', review)
            self.assertEqual(datetime.fromisoformat(review['expires_at'].replace('Z', '+00:00'))-datetime.fromisoformat(review['created_at'].replace('Z', '+00:00')), timedelta(minutes=10))
            self.assertEqual(datetime.fromisoformat(review['created_at'].replace('Z', '+00:00')), NOW)
            stored = next(r for r in self.rows(variant) if r[0] == review['review_id'])
            self.assertEqual(stored[1], OWNER); self.assertEqual(json.loads(stored[2]), review)
            self.assertEqual(stored[4], self.stores[variant]['config'].config_hash)
            if variant == 'clothing': self.assertNotIn('slot', review['delivery'])
            else:
                granola = next(i for i in review['items'] if i['product_id'] == 'granola')
                self.assertIsNone(granola['food_information']['allergens']['contains'])
                self.assertEqual(review['delivery']['slot']['timezone'], 'America/Sao_Paulo')
            with closing(sqlite3.connect(self.stores[variant]['env']['DATA_DIR']+'/orders.sqlite')) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM orders').fetchone()[0], 0)
                self.assertEqual(db.execute('SELECT count(*) FROM attempts').fetchone()[0], 0)
            self.assertFalse((self.directory/variant/'payments').exists())

    def test_delivery_slots_permissions_and_no_review_query(self):
        status, slots, _ = self.call('food', '/internal/v1/delivery-slots', owner=None)
        self.assertEqual(status, 200)
        self.assertEqual(len(slots['items']), 7)
        self.assertTrue(all(s['id'].endswith(':morning') for s in slots['items']))
        self.assertEqual(datetime.fromisoformat(slots['server_now'].replace('Z', '+00:00')), NOW)
        self.assertEqual(self.call('clothing', '/internal/v1/delivery-slots')[0], 409)
        for path in ['/internal/v1/orders', '/internal/v1/payments', '/internal/v1/reviews/unknown', '/api/v1/reviews']:
            self.assertEqual(self.call('food', path)[0], 404)
        schema = self.call('food', '/openapi.json')[1]
        self.assertEqual(set(schema['paths']), {'/health/live', '/health/ready', '/internal/v1/reviews', '/internal/v1/delivery-slots'})
        self.assertNotIn(OWNER, json.dumps(schema))

    def test_auth_session_and_identity_rejections(self):
        before = self.rows('clothing')
        for owner in [None, '', 'short', 'A'*64, 'g'*64, 'person@example.invalid']:
            self.assertEqual(self.call('clothing', '/internal/v1/reviews', review_body('clothing'), owner=owner)[0], 401)
        for token in [None, 'Bearer incorrect', 'Bearer '+self.stores['clothing']['env']['ORDERS_CATALOG_TOKEN']]:
            self.assertEqual(self.call('clothing', '/internal/v1/reviews', review_body('clothing'), headers={'Authorization': token})[0], 401)
            self.assertEqual(self.call('clothing', '/internal/v1/delivery-slots', headers={'Authorization': token})[0], 401)
        for headers in [{'X-Store-Id': 'wrong-store'}, {'X-Config-Hash': '0'*64}]:
            self.assertEqual(self.call('clothing', '/internal/v1/reviews', review_body('clothing'), headers=headers)[0], 409)
        body = review_body('clothing'); body['store_id'] = 'other-store'
        self.assertEqual(self.call('clothing', '/internal/v1/reviews', body)[0], 409)
        self.assertEqual(self.rows('clothing'), before)

    def test_invalid_bodies_delivery_and_lists_never_persist(self):
        cases = []
        for variant in ['clothing', 'food']:
            for mutate in [lambda b: b.update(session_owner=OWNER), lambda b: b.update(total_cents=1),
                           lambda b: b['items'][0].update(price_cents=1), lambda b: b['items'][0].update(quantity=True),
                           lambda b: b['items'][0].update(quantity='1'), lambda b: b['items'][0].update(quantity=1.5),
                           lambda b: b['delivery']['address'].update(postal_code='invalid'),
                           lambda b: b['items'].append(b['items'][0]), lambda b: b.update(items=[]),
                           lambda b: b.update(payment_method='card')]:
                body = review_body(variant); mutate(body); cases.append((variant, body, 422))
        for slot in [None, 'unknown', 'food-windows-v1:2026-11-09:afternoon', 'food-windows-v1:2026-11-08:morning']:
            body = review_body('food'); body['delivery']['slot_id'] = slot
            cases.append(('food', body, 409 if slot == 'food-windows-v1:2026-11-08:morning' else 422))
        body = review_body('food'); body['delivery'].pop('slot_id'); cases.append(('food', body, 422))
        body = review_body('food'); body['items'][0]['combination_id'] = None; cases.append(('food', body, 422))
        body = review_body('clothing'); body['delivery']['slot_id'] = None; cases.append(('clothing', body, 422))
        body = review_body('clothing'); body['items'][0]['combination_id'] = 'camiseta-p-branca'; cases.append(('clothing', body, 422))
        before = {variant: self.rows(variant) for variant in self.stores}
        for variant, body, expected in cases:
            status, error, _ = self.call(variant, '/internal/v1/reviews', body)
            self.assertEqual(status, expected, error)
            self.assertIn('error', error)
            self.assertNotIn('Rua Exemplo', json.dumps(error))
            self.assertNotIn(OWNER, json.dumps(error))
        for variant in self.stores: self.assertEqual(self.rows(variant), before[variant])
        raw = self.call('food', '/internal/v1/reviews', method='POST', raw=b'{broken', headers={'Content-Type': 'application/json'})
        self.assertEqual(raw[0], 400)
        self.assertEqual(self.call('food', '/internal/v1/reviews', method='POST', raw=b'x'*65537, headers={'Content-Type': 'application/json'})[0], 413)
        self.assertEqual(self.call('food', '/internal/v1/reviews', method='POST', raw=b'{}', headers={'Content-Type': 'text/plain'})[0], 415)

    def test_snapshot_survives_orders_restart_and_other_owner_is_bound(self):
        response = self.call('clothing', '/internal/v1/reviews', review_body('clothing'), owner='b'*64)
        self.assertEqual(response[0], 201)
        before = self.rows('clothing')
        self.stop_service('clothing', 'orders'); self.start('clothing', 'orders')
        self.assertEqual(before, self.rows('clothing'))
        self.assertEqual(next(r[1] for r in before if r[0] == response[1]['review_id']), 'b'*64)

    def test_storage_lock_never_returns_success(self):
        before = self.rows('clothing')
        with closing(sqlite3.connect(self.stores['clothing']['env']['DATA_DIR']+'/orders.sqlite')) as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                status, error, _ = self.call('clothing', '/internal/v1/reviews', review_body('clothing'))
            finally: db.rollback()
        self.assertEqual(status, 503)
        self.assertEqual(error['error']['code'], 'ORDER_STORAGE_UNAVAILABLE')
        self.assertEqual(self.rows('clothing'), before)

    def test_catalog_faults_and_no_redirect_forwarding(self):
        store = self.stores['clothing']; before = self.rows('clothing')
        server = FaultServer(store['config'])
        self.stop_service('clothing', 'orders')
        original = store['env']['CATALOG_URL']; store['env']['CATALOG_URL'] = server.url
        try:
            self.start('clothing', 'orders')
            for mode, expected, calls in [('malformed', 503, 1), ('identity', 409, 1), ('redirect', 503, 1), ('unavailable', 503, 2)]:
                server.mode, server.calls = mode, 0
                status, body, _ = self.call('clothing', '/internal/v1/reviews', review_body('clothing'))
                self.assertEqual(status, expected, body)
                self.assertEqual(server.calls, calls)
            self.assertEqual(server.targets, 0)
            self.assertEqual(self.rows('clothing'), before)
        finally:
            self.stop_service('clothing', 'orders'); store['env']['CATALOG_URL'] = original
            server.close(); self.start('clothing', 'orders')

    def test_no_payment_or_recovery_readiness_claim(self):
        for variant in self.stores:
            status, ready, _ = self.call(variant, '/health/ready')
            self.assertEqual(status, 200, ready)
            self.assertEqual(ready['checks']['review_repository'], 'ok')
            self.assertNotIn('payments_identity', ready['checks'])
            self.assertNotIn('recovery_worker', ready['checks'])

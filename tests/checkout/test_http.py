import json
import os
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener
from uuid import uuid4

from foundation.config import ROOT, load
from tests.reviews.fixtures import NOW, OWNER, review_body
from tests.reviews.test_http import free_port, stop


class CheckoutHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.temp.cleanup)
        cls.directory, cls.stores = Path(cls.temp.name), {}
        for variant in ['clothing','food']:
            cfg = load(ROOT/f'configurations/{variant}.json')
            ports = {s:free_port() for s in ['catalog','orders','payments']}
            env = os.environ.copy()
            env.update(PRODUCT_CONFIG=str(ROOT/f'configurations/{variant}.json'), TEST_CLOCK=NOW.isoformat(), TEST_WORKER='0',
                       CATALOG_DATA_ROOT=str(ROOT/'demo-data'), CATALOG_URL=f'http://127.0.0.1:{ports["catalog"]}',
                       PAYMENTS_URL=f'http://127.0.0.1:{ports["payments"]}')
            for name in ['WEB_CATALOG_TOKEN','WEB_ORDERS_TOKEN','WEB_PAYMENTS_TOKEN','ORDERS_CATALOG_TOKEN','ORDERS_PAYMENTS_TOKEN','RECOMMENDATIONS_CATALOG_TOKEN']:env[name]=secrets.token_hex(32)
            cls.stores[variant]={'config':cfg,'env':env,'ports':ports,'children':{},'logs':{}}
            cls.addClassCleanup(cls.close_store,variant)
            for service in ['catalog','payments','orders']:cls.start(variant,service)

    @classmethod
    def start(cls,variant,service):
        store=cls.stores[variant];env=store['env'].copy();env['DATA_DIR']=str(cls.directory/variant/service)
        target=['tests.checkout.server:create_app','--factory'] if service=='orders' else [f'services.{service}.app:app']
        log=(cls.directory/f'{variant}-{service}.log').open('ab');store['logs'][service]=log
        child=subprocess.Popen([sys.executable,'-m','uvicorn',*target,'--host','127.0.0.1','--port',str(store['ports'][service])],cwd=ROOT,env=env,stdout=log,stderr=log,
                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name=='nt' else 0)
        store['children'][service]=child
        for _ in range(100):
            if child.poll() is not None:raise AssertionError('Test service startup failed: '+service)
            try:
                if cls.call(variant,service,'/health/live')[0]==200:return
            except OSError:pass
            time.sleep(0.05)
        raise AssertionError('Test service did not start')

    @classmethod
    def close_service(cls,variant,service):
        store=cls.stores[variant]
        if service in store['children']:stop(store['children'].pop(service));store['logs'].pop(service).close()

    @classmethod
    def close_store(cls,variant):
        for service in list(cls.stores[variant]['children']):cls.close_service(variant,service)

    @classmethod
    def call(cls,variant,service,path,body=None,method=None,key=None,owner=OWNER,role='web',overrides=None):
        store=cls.stores[variant]
        headers={'Authorization':'Bearer '+store['env'][f'{role.upper()}_{service.upper()}_TOKEN'],
                 'X-Store-Id':store['config'].store_id,'X-Config-Hash':store['config'].config_hash,'X-Session-Owner':owner}
        if key:headers['Idempotency-Key']=key
        if overrides:headers.update(overrides)
        data=None
        if body is not None:data=json.dumps(body).encode();headers['Content-Type']='application/json'
        request=Request(f'http://127.0.0.1:{store["ports"][service]}'+path,data=data,method=method,headers=headers)
        try:response=build_opener(ProxyHandler({})).open(request,timeout=12)
        except HTTPError as exc:response=exc
        with response:return response.status,json.load(response),dict(response.headers)

    def review(self,variant):
        status,result,_=self.call(variant,'orders','/internal/v1/reviews',review_body(variant))
        self.assertEqual(status,201,result)
        return {'store_id':self.stores[variant]['config'].store_id,'review_id':result['review_id']}

    def confirmed(self,variant,key,command):
        result=self.call(variant,'orders','/internal/v1/orders',command,key=key)
        for _ in range(40):
            if result[0] in {200,201} and result[1].get('status')=='confirmed':return result[1]
            attempt=self.call(variant,'orders','/internal/v1/order-attempts/'+key)[1]
            if attempt.get('order_id'):result=self.call(variant,'orders','/internal/v1/orders/'+attempt['order_id'])
            time.sleep(0.05)
        self.fail('Order did not confirm')

    def test_normal_purchase_both_variants_replay_and_private_queries(self):
        for variant,total in [('clothing',26970),('food',4970)]:
            command=self.review(variant);key=str(uuid4());order=self.confirmed(variant,key,command)
            self.assertEqual(order['totals']['total_cents'],total)
            replay=self.call(variant,'orders','/internal/v1/orders',command,key=key)
            self.assertEqual(replay[0],200);self.assertEqual(replay[1]['order_id'],order['order_id'])
            self.assertEqual(self.call(variant,'orders','/internal/v1/orders/'+order['order_id'],owner='b'*64)[0],404)
            self.assertEqual(self.call(variant,'orders','/internal/v1/order-attempts/'+key,owner='b'*64)[0],404)
            changed={**command,'review_id':str(uuid4())}
            self.assertEqual(self.call(variant,'orders','/internal/v1/orders',changed,key=key)[0],409)
            self.assertEqual(self.call(variant,'orders','/internal/v1/orders',command,key=str(uuid4()))[1]['error']['code'],'REVIEW_ALREADY_USED')

    def test_http_concurrency_and_payment_permissions(self):
        variant='clothing';command=self.review(variant);key=str(uuid4())
        with ThreadPoolExecutor(max_workers=5) as pool:
            results=list(pool.map(lambda _:self.call(variant,'orders','/internal/v1/orders',command,key=key),range(5)))
        self.assertTrue(all(result[0] in {200,201,202} for result in results))
        order=self.confirmed(variant,key,command)
        url='/internal/v1/payments/by-order/'+order['order_id']
        self.assertEqual(self.call(variant,'payments',url)[0],403)
        status,payment,_=self.call(variant,'payments',url,role='orders')
        self.assertEqual(status,200);self.assertEqual(payment['payment_id'],order['payment']['payment_id'])
        request={'store_id':self.stores[variant]['config'].store_id,'order_id':order['order_id'],'method':'simulated_pix','currency':'BRL','amount_cents':order['totals']['total_cents']}
        self.assertEqual(self.call(variant,'payments',url,request,'PUT',role='orders')[1]['payment_id'],payment['payment_id'])
        request['amount_cents']+=1
        self.assertEqual(self.call(variant,'payments',url,request,'PUT',role='orders')[0],409)

    def test_worker_recovers_after_real_restart_and_payment_returns(self):
        variant='food';store=self.stores[variant]
        self.close_service(variant,'payments')
        command=self.review(variant);key=str(uuid4())
        pending=self.call(variant,'orders','/internal/v1/orders',command,key=key)
        self.assertEqual(pending[0],202)
        order_id=pending[1]['order_id']
        self.close_service(variant,'orders')
        # Test clock advances past persisted backoff; no long sleep, no production clock override.
        from datetime import timedelta
        original_clock=store['env']['TEST_CLOCK']
        store['env']['TEST_CLOCK']=(NOW+timedelta(seconds=20)).isoformat();store['env']['TEST_WORKER']='1'
        try:
            self.start(variant,'payments');self.start(variant,'orders')
            for _ in range(80):
                status,result,_=self.call(variant,'orders','/internal/v1/orders/'+order_id)
                if result.get('status')=='confirmed':break
                time.sleep(0.05)
            self.assertEqual(result['status'],'confirmed')
            self.assertEqual(result['order_id'],order_id)
            self.close_service(variant,'payments');self.start(variant,'payments')
            payment=self.call(variant,'payments','/internal/v1/payments/by-order/'+order_id,role='orders')
            self.assertEqual(payment[1]['payment_id'],result['payment']['payment_id'])
        finally:
            self.close_service(variant,'orders');store['env']['TEST_CLOCK']=original_clock;store['env']['TEST_WORKER']='0';self.start(variant,'orders')

    def test_inputs_missing_key_owner_and_unknown_ids(self):
        command=self.review('clothing')
        self.assertEqual(self.call('clothing','orders','/internal/v1/orders',command)[1]['error']['code'],'IDEMPOTENCY_KEY_REQUIRED')
        self.assertEqual(self.call('clothing','orders','/internal/v1/orders',command,key='invalid')[0],400)
        self.assertEqual(self.call('clothing','orders','/internal/v1/orders',command,key=str(uuid4()),overrides={'X-Session-Owner':'invalid'})[0],401)
        self.assertEqual(self.call('clothing','orders','/internal/v1/orders/'+str(uuid4()))[0],404)

"""Smoke real: três servidores separados, bancos temporários, HTTP em loopback."""
import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from foundation.config import ROOT, load


def request(url, headers=None):
    try:
        response=build_opener(ProxyHandler({})).open(Request(url,headers=headers or {}),timeout=3)
    except HTTPError as exc:
        response=exc
    with response:
        return response.status,json.load(response)


def port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        return sock.getsockname()[1]


class ProcessTests(unittest.TestCase):
    def test_variants_auth_readiness_degradation_and_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=[]
            for variant in ['clothing','food']:
                with self.subTest(variant=variant):
                    config=load(ROOT/f'configurations/{variant}.json')
                    ports={s:port() for s in ['catalog','orders','payments']}
                    env=os.environ.copy()
                    env.update(PRODUCT_CONFIG=str(ROOT/f'configurations/{variant}.json'))
                    for name in ['WEB_CATALOG_TOKEN','WEB_ORDERS_TOKEN','WEB_PAYMENTS_TOKEN','ORDERS_CATALOG_TOKEN','ORDERS_PAYMENTS_TOKEN']:
                        env[name]=secrets.token_hex(32)
                    env.update(CATALOG_URL=f'http://127.0.0.1:{ports["catalog"]}',PAYMENTS_URL=f'http://127.0.0.1:{ports["payments"]}',ORDERS_URL=f'http://127.0.0.1:{ports["orders"]}',LPS_ROOT=str(ROOT))
                    processes={};logs=[]

                    def start(service, override=None):
                        child_env=env.copy()
                        child_env['DATA_DIR']=str(Path(directory)/config.store_id/service)
                        if override:child_env['PRODUCT_CONFIG']=str(ROOT/f'configurations/{override}.json')
                        log=open(Path(directory)/f'{variant}-{service}-{len(logs)}.log','wb');logs.append(log)
                        child=subprocess.Popen([sys.executable,'-m','uvicorn',f'services.{service}.app:app','--host','127.0.0.1','--port',str(ports[service])],
                            cwd=ROOT,env=child_env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                        processes[service]=child
                        for _ in range(80):
                            if child.poll() is not None:
                                log.flush()
                                raise AssertionError(Path(log.name).read_text(errors='replace'))
                            try:
                                if request(f'http://127.0.0.1:{ports[service]}/health/live')[0]==200:return
                            except OSError:pass
                            time.sleep(0.05)
                        raise AssertionError('Service did not become live')

                    def stop(service):
                        child=processes.pop(service)
                        child.terminate();child.wait(timeout=5)

                    def ready(service, identity=None):
                        selected=identity or config
                        return request(f'http://127.0.0.1:{ports[service]}/health/ready',{
                            'Authorization':'Bearer '+env[f'WEB_{service.upper()}_TOKEN'],
                            'X-Store-Id':selected.store_id,'X-Config-Hash':selected.config_hash})

                    def web_ready():
                        web_env = env.copy()
                        web_env.update(SESSION_SECRET=secrets.token_hex(32), WEB_ORIGIN='http://127.0.0.1:3000')
                        result=subprocess.run(['node','--experimental-strip-types','apps/store-ropa/scripts/check-readiness.ts'],
                            cwd=ROOT,env=web_env,capture_output=True,text=True,timeout=10)
                        self.assertEqual(result.returncode,0,result.stderr)
                        return json.loads(result.stdout)

                    try:
                        for service in ['catalog','payments','orders']:start(service)
                        self.assertEqual(len({p.pid for p in processes.values()}),3)
                        self.assertTrue(web_ready()['ready'])
                        for service in processes:
                            url=f'http://127.0.0.1:{ports[service]}'
                            status,body=ready(service)
                            self.assertEqual(status,200,body)
                            self.assertEqual(body['scope'],'foundation')
                            if service=='orders':self.assertEqual(body['checks']['recovery_worker'],'ok')
                            self.assertEqual(body['store_id'],config.store_id)
                            self.assertEqual(request(url+'/health/ready')[0],401)
                            other=load(ROOT/f'configurations/{"food" if variant=="clothing" else "clothing"}.json')
                            self.assertEqual(ready(service,other)[0],409)
                            expected={'/health/live','/health/ready'}
                            if service=='catalog':
                                expected.update({'/internal/v1/products','/internal/v1/products/{product_id}','/internal/v1/selections/resolve'})
                                self.assertEqual(body['checks']['catalog_loaded'],'ok')
                                self.assertTrue(body['catalog_revision'].startswith('sha256:'))
                            if service=='orders':
                                expected.update({'/internal/v1/reviews','/internal/v1/delivery-slots'})
                                expected.update({'/internal/v1/orders','/internal/v1/orders/{order_id}','/internal/v1/order-attempts/{key}'})
                                self.assertEqual(body['checks']['payments_identity'],'ok')
                            if service=='payments':expected.add('/internal/v1/payments/by-order/{order_id}')
                            self.assertEqual(set(request(url+'/openapi.json')[1]['paths']),expected)
                            self.assertEqual(request(url+'/products')[0],404)
                        # Restart the same store using the same durable directories.
                        stop('orders');start('orders')
                        self.assertEqual(ready('orders')[0],200)
                        paths.extend([Path(directory)/config.store_id/s/(s+'.sqlite') for s in ['orders','payments']])
                        self.assertTrue(all(p.is_file() for p in paths))
                        # Checkout readiness now includes its real payment dependency.
                        stop('payments')
                        status,body=ready('orders')
                        self.assertEqual(status,503)
                        self.assertEqual(body['checks']['payments_identity'],'unavailable')
                        self.assertEqual(request(f'http://127.0.0.1:{ports["orders"]}/health/live')[0],200)
                        self.assertFalse(web_ready()['ready'])
                        start('payments');self.assertEqual(ready('orders')[0],200)
                        stop('catalog');start('catalog','food' if variant=='clothing' else 'clothing')
                        status,body=ready('orders')
                        self.assertEqual(status,503)
                        self.assertEqual(body['checks']['catalog_identity'],'mismatch')
                    finally:
                        for service in list(processes):stop(service)
                        for log in logs:log.close()
            self.assertEqual(len(set(paths)),4)

    def test_invalid_configuration_fails_startup(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest=Path(directory)/'invalid.json'
            manifest.write_text('{"domain":"both"}')
            env=os.environ.copy();env['PRODUCT_CONFIG']=str(manifest)
            result=subprocess.run([sys.executable,'-m','uvicorn','services.catalog.app:app','--host','127.0.0.1','--port',str(port())],
                cwd=ROOT,env=env,capture_output=True,timeout=15)
            self.assertNotEqual(result.returncode,0)
            self.assertIn(b'CONFIG_INVALID',result.stderr)

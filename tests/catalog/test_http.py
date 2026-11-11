import copy
import json
import os
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from foundation.config import ROOT, load
from tests.foundation.test_processes import port


class CatalogHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.directory=Path(cls.temporary.name)
        cls.data=cls.directory/'demo-data'
        shutil.copytree(ROOT/'demo-data',cls.data)
        cls.stores={}
        for variant in ['clothing','food']:
            config=load(ROOT/f'configurations/{variant}.json')
            env=os.environ.copy()
            env.update(PRODUCT_CONFIG=str(ROOT/f'configurations/{variant}.json'),CATALOG_DATA_ROOT=str(cls.data),
                       WEB_CATALOG_TOKEN=secrets.token_hex(32),ORDERS_CATALOG_TOKEN=secrets.token_hex(32),RECOMMENDATIONS_CATALOG_TOKEN=secrets.token_hex(32))
            address=port()
            log=(cls.directory/(variant+'.log')).open('wb')
            child=subprocess.Popen([sys.executable,'-m','uvicorn','services.catalog.app:app','--host','127.0.0.1','--port',str(address)],
                cwd=ROOT,env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name=='nt' else 0)
            cls.stores[variant]={'config':config,'env':env,'port':address,'child':child,'log':log}
            cls.addClassCleanup(cls.stop,variant)
        import time
        for variant,store in cls.stores.items():
            for _ in range(100):
                if store['child'].poll() is not None:
                    raise AssertionError(store['log'].name+' failed startup')
                try:
                    status,_,_=cls.call(variant,'/health/live',role=None)
                    if status==200:break
                except OSError:pass
                time.sleep(0.05)
            else:raise AssertionError('Catalog did not become live')

    @classmethod
    def stop(cls,variant):
        store=cls.stores[variant]
        child=store['child']
        if child.poll() is None:
            if os.name=='nt':
                try:child.send_signal(signal.CTRL_BREAK_EVENT)
                except OSError:pass
            else:child.terminate()
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if os.name=='nt':
                    subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True,timeout=5)
                else:child.kill()
                child.wait(timeout=5)
        store['log'].close()

    @classmethod
    def call(cls,variant,path,method='GET',body=None,role='web',extra_headers=None,raw=None):
        store=cls.stores[variant]
        headers={'X-Store-Id':store['config'].store_id,'X-Config-Hash':store['config'].config_hash}
        if role:headers['Authorization']='Bearer '+store['env'][f'{role.upper()}_CATALOG_TOKEN']
        if body is not None:
            raw=json.dumps(body).encode();headers['Content-Type']='application/json'
        if extra_headers:headers.update(extra_headers)
        request=Request(f'http://127.0.0.1:{store["port"]}'+path,data=raw,headers=headers,method=method)
        try:response=build_opener(ProxyHandler({})).open(request,timeout=4)
        except HTTPError as error:response=error
        with response:return response.status,json.load(response),{key.lower():value for key,value in response.headers.items()}

    def test_two_independent_stores_listing_detail_and_openapi(self):
        self.assertEqual(len({s['child'].pid for s in self.stores.values()}),2)
        for variant,example in [('clothing','camiseta'),('food','biscoito')]:
            with self.subTest(variant=variant):
                status,listing,headers=self.call(variant,'/internal/v1/products')
                self.assertEqual(status,200)
                self.assertEqual(len(listing['items']),10 if variant=='clothing' else 6)
                self.assertTrue(all(p['kind']==variant and 'category' in p for p in listing['items']))
                self.assertEqual(headers['x-store-id'],self.stores[variant]['config'].store_id)
                status,detail,_=self.call(variant,'/internal/v1/products/'+example)
                self.assertEqual(status,200)
                self.assertEqual(detail['catalog_revision'],listing['catalog_revision'])
                self.assertEqual(detail['product']['id'],example)
                missing=self.call(variant,'/internal/v1/products/does-not-exist')
                self.assertEqual(missing[0],404)
                self.assertEqual(missing[1]['error']['code'],'PRODUCT_NOT_FOUND')
                ready=self.call(variant,'/health/ready')[1]
                self.assertEqual(ready['checks']['catalog_loaded'],'ok')
                self.assertEqual(ready['catalog_revision'],listing['catalog_revision'])
                self.assertNotIn('recovery_worker',ready['checks'])
                schema=self.call(variant,'/openapi.json',role=None)[1]
                self.assertEqual(set(schema['paths']),{'/health/live','/health/ready','/internal/v1/products','/internal/v1/products/{product_id}','/internal/v1/selections/resolve','/internal/v1/recommendation-candidates'})
                for path in ['/api/v1/products','/delivery-slots','/orders','/payments']:
                    self.assertEqual(self.call(variant,path)[0],404)

    def test_resolution_both_domains_and_permission_boundaries(self):
        for variant,items in [('clothing',[
            {'product_id':'camiseta','combination_id':'camiseta-m-preta','quantity':1},
            {'product_id':'camiseta','combination_id':'camiseta-g-azul','quantity':2}]),
            ('food',[{'product_id':'biscoito','quantity':2},{'product_id':'suco','quantity':1}])]:
            body={'store_id':self.stores[variant]['config'].store_id,'items':items}
            status,resolved,_=self.call(variant,'/internal/v1/selections/resolve','POST',body,'orders')
            self.assertEqual(status,200,resolved)
            self.assertEqual(len(resolved['items']),2)
            self.assertTrue(all(i['unit_price_cents']>0 for i in resolved['items']))
            if variant=='clothing':self.assertEqual(resolved['items'][0]['combination']['color'],'preta')
            else:self.assertEqual(resolved['items'][0]['food_information']['allergens']['contains'],['trigo'])
            self.assertEqual(self.call(variant,'/internal/v1/selections/resolve','POST',body,'web')[0],403)
            self.assertEqual(self.call(variant,'/internal/v1/products',role='orders')[0],403)
            self.assertEqual(self.call(variant,'/internal/v1/products',role=None)[0],401)
            self.assertEqual(self.call(variant,'/internal/v1/products',extra_headers={'Authorization':'Bearer incorrect'})[0],401)
            self.assertEqual(self.call(variant,'/internal/v1/products',extra_headers={'X-Config-Hash':'0'*64})[0],409)
            self.assertEqual(self.call(variant,'/internal/v1/products',extra_headers={'X-Store-Id':'wrong-store'})[0],409)

    def test_invalid_selections_all_or_nothing_and_envelope(self):
        valid={'product_id':'camiseta','quantity':1,'combination_id':'camiseta-m-preta'}
        cases=[
            ('clothing',[valid,{'product_id':'missing','quantity':1}],'SELECTION_INVALID'),
            ('clothing',[valid,valid],'DUPLICATE_LINE'),
            ('clothing',[{**valid,'combination_id':'jaqueta-leve-m-verde'}],'SELECTION_INVALID'),
            ('clothing',[{**valid,'combination_id':'camiseta-p-branca'}],'SELECTION_INVALID'),
            ('clothing',[{'product_id':'camiseta','quantity':1}],'SELECTION_INVALID'),
            ('food',[{'product_id':'biscoito','quantity':1}]*2,'DUPLICATE_LINE'),
            ('food',[{'product_id':'biscoito','quantity':1,'combination_id':None}],'INPUT_INVALID'),
            ('food',[{'product_id':'biscoito','quantity':1,'combination_id':'camiseta-m-preta'}],'SELECTION_INVALID'),
            ('food',[{'product_id':'biscoito','quantity':1,'price_cents':1}],'INPUT_INVALID'),
        ]
        cases.extend(('food',[{'product_id':'biscoito','quantity':q}],'INPUT_INVALID') for q in [True,False,'1',1.0,1.2,0,101])
        cases.extend([('food',[],'INPUT_INVALID'),('food',[{'product_id':f'item-{i}','quantity':1} for i in range(51)],'INPUT_INVALID')])
        for variant,items,code in cases:
            with self.subTest(variant=variant,code=code,items=items[:2]):
                status,body,_=self.call(variant,'/internal/v1/selections/resolve','POST',{'store_id':self.stores[variant]['config'].store_id,'items':items},'orders')
                self.assertEqual(status,422,body)
                self.assertEqual(body['error']['code'],code)
                self.assertNotIn('items',body)
                self.assertNotIn('traceback',json.dumps(body).lower())
                self.assertNotIn(str(self.directory),json.dumps(body))
        changed={'store_id':'wrong-store','items':[valid]}
        self.assertEqual(self.call('clothing','/internal/v1/selections/resolve','POST',changed,'orders')[0],409)
        raw=self.call('food','/internal/v1/selections/resolve','POST',role='orders',raw=b'{broken',extra_headers={'Content-Type':'application/json'})
        self.assertEqual(raw[0],400)
        self.assertEqual(raw[1]['error']['code'],'MALFORMED_JSON')
        self.assertEqual(self.call('food','/internal/v1/selections/resolve','POST',role='orders',raw=b'x'*65537,extra_headers={'Content-Type':'application/json'})[0],413)
        self.assertEqual(self.call('food','/internal/v1/selections/resolve','POST',role='orders',raw=b'{}',extra_headers={'Content-Type':'text/plain'})[0],415)

    def test_catalog_remains_immutable_until_restart(self):
        for variant in ['clothing','food']:
            before=self.call(variant,'/internal/v1/products')[1]
            filename=self.data/variant/'products.json'
            original=filename.read_bytes()
            try:
                data=json.loads(original);data['products'][0]['price_cents']+=1
                filename.write_text(json.dumps(data),encoding='utf-8')
                after=self.call(variant,'/internal/v1/products')[1]
                self.assertEqual(before,after)
            finally:filename.write_bytes(original)


class InvalidCatalogStartupTests(unittest.TestCase):
    def test_missing_invalid_and_wrong_store_prevent_startup(self):
        with tempfile.TemporaryDirectory() as directory:
            data=Path(directory);(data/'clothing').mkdir()
            original=json.loads((ROOT/'demo-data/clothing/products.json').read_text(encoding='utf-8'))
            invalid=copy.deepcopy(original);invalid['products'][0]['price_cents']=True
            wrong=copy.deepcopy(original);wrong['store_id']='other-store'
            for name,content in [('missing',None),('invalid',invalid),('wrong-store',wrong)]:
                with self.subTest(name=name):
                    if content is not None:(data/'clothing/products.json').write_text(json.dumps(content),encoding='utf-8')
                    env=os.environ.copy();env.update(PRODUCT_CONFIG=str(ROOT/'configurations/clothing.json'),CATALOG_DATA_ROOT=str(data),
                        WEB_CATALOG_TOKEN=secrets.token_hex(32),ORDERS_CATALOG_TOKEN=secrets.token_hex(32),RECOMMENDATIONS_CATALOG_TOKEN=secrets.token_hex(32))
                    result=subprocess.run([sys.executable,'-m','uvicorn','services.catalog.app:app','--host','127.0.0.1','--port',str(port())],
                        cwd=ROOT,env=env,capture_output=True,timeout=15)
                    self.assertNotEqual(result.returncode,0)
                    self.assertIn(b'CATALOG_INVALID',result.stderr)

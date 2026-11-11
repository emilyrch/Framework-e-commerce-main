"""Real catalog/recommendation processes with temporary ports, secrets and SQLite."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.error import HTTPError
from urllib.request import ProxyHandler,Request,build_opener
from uuid import uuid4

from foundation.config import ROOT,load
from tests.reviews.test_http import free_port,stop


class RecommendationHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup);cls.directory=Path(cls.temp.name);cls.stores={}
        for variant in ['clothing','food']:
            config=load(ROOT/f'configurations/{variant}.json');ports={service:free_port() for service in ['catalog','recommendations']}
            env=os.environ.copy();env.update(PRODUCT_CONFIG=str(ROOT/f'configurations/{variant}.json'),CATALOG_DATA_ROOT=str(ROOT/'demo-data'),CATALOG_URL=f'http://127.0.0.1:{ports["catalog"]}')
            for name in ['WEB_CATALOG_TOKEN','ORDERS_CATALOG_TOKEN','RECOMMENDATIONS_CATALOG_TOKEN','WEB_RECOMMENDATIONS_TOKEN']:env[name]=secrets.token_hex(32)
            cls.stores[variant]={'config':config,'ports':ports,'env':env,'children':{},'logs':{}}
            cls.addClassCleanup(cls.close_store,variant)
            for service in ['catalog','recommendations']:cls.start(variant,service)

    @classmethod
    def start(cls,variant,service):
        store=cls.stores[variant];env=store['env'].copy();env['DATA_DIR']=str(cls.directory/variant/service)
        log=(cls.directory/f'{variant}-{service}.log').open('ab');store['logs'][service]=log
        child=subprocess.Popen([sys.executable,'-m','uvicorn',f'services.{service}.app:app','--host','127.0.0.1','--port',str(store['ports'][service])],cwd=ROOT,env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        store['children'][service]=child
        for _ in range(100):
            if child.poll() is not None:raise AssertionError('Recommendation test startup failed: '+variant+'/'+service)
            try:
                if cls.call(variant,'/health/live',service=service)[0]==200:return
            except OSError:pass
            time.sleep(.05)
        raise AssertionError('Test service did not start')

    @classmethod
    def close_service(cls,variant,service):
        store=cls.stores[variant]
        if service in store['children']:stop(store['children'].pop(service));store['logs'].pop(service).close()

    @classmethod
    def close_store(cls,variant):
        for service in list(cls.stores[variant]['children']):cls.close_service(variant,service)

    @classmethod
    def call(cls,variant,path,body=None,owner='a'*64,service='recommendations',role='web',headers=None):
        store=cls.stores[variant];cfg=store['config']
        base={'X-Store-Id':cfg.store_id,'X-Config-Hash':cfg.config_hash}
        if role:base['Authorization']='Bearer '+store['env'][f'{role.upper()}_{service.upper()}_TOKEN']
        if owner is not None:base['X-Session-Owner']=owner
        if headers:base.update(headers)
        data=None
        if body is not None:data=json.dumps(body).encode();base['Content-Type']='application/json'
        request=Request(f'http://127.0.0.1:{store["ports"][service]}'+path,data=data,headers=base)
        try:response=build_opener(ProxyHandler({})).open(request,timeout=7)
        except HTTPError as error:response=error
        with response:return response.status,json.load(response),dict(response.headers)

    def test_a_permissions_owner_identity_and_internal_candidates(self):
        self.assertEqual(self.call('clothing','/health/ready')[0],200)
        route='/internal/v1/preferences'
        self.assertEqual(self.call('clothing',route,role=None)[0],401)
        self.assertEqual(self.call('clothing',route,owner=None)[0],401)
        self.assertEqual(self.call('clothing',route,owner='forged')[0],401)
        self.assertEqual(self.call('clothing',route,headers={'X-Config-Hash':'0'*64})[0],409)
        self.assertEqual(self.call('clothing',route,headers={'Authorization':'Bearer wrong'})[0],401)
        path='/internal/v1/recommendation-candidates'
        self.assertEqual(self.call('clothing',path,service='catalog')[0],403)
        self.assertEqual(self.call('clothing',path,service='catalog',role='orders')[0],403)
        result=self.call('clothing',path,service='catalog',role='recommendations');self.assertEqual(result[0],200);self.assertEqual(len(result[1]['items']),10)

    def test_b_preferences_ranking_validation_and_scope(self):
        body={'store_id':'roupas-demo','categories':['Camisetas e camisas'],'colors':['preta'],'sizes':['M'],'max_price_cents':10000,'use_history':True}
        result=self.call('clothing','/internal/v1/preferences',body,owner='b'*64)
        self.assertEqual(result[0],200,result[1]);self.assertEqual(result[2].get('Cache-Control'),'no-store')
        rec=self.call('clothing','/internal/v1/recommendations',owner='b'*64)
        self.assertEqual(rec[0],200,rec[1]);self.assertEqual([p['id']for p in rec[1]['items']],['camiseta'])
        self.assertTrue(rec[1]['items'][0]['reasons']);self.assertEqual(rec[1]['mode'],'personalized')
        self.assertEqual(self.call('clothing','/internal/v1/preferences',owner='c'*64)[1]['profile']['categories'],[])
        for invalid in [{**body,'session_owner':'c'*64},{**body,'max_price_cents':True},{**body,'colors':['unknown']},{**body,'sizes':['M','m']}]:
            self.assertEqual(self.call('clothing','/internal/v1/preferences',invalid)[0],422)
        self.assertEqual(self.call('clothing','/internal/v1/preferences',{**body,'store_id':'alimentos-demo'})[0],409)

    def test_c_history_retry_reset_and_restart(self):
        owner='d'*64;event={'store_id':'roupas-demo','event_id':str(uuid4()),'product_id':'camiseta','kind':'view'}
        for _ in range(2):self.assertTrue(self.call('clothing','/internal/v1/recommendation-events',event,owner=owner)[1]['saved'])
        self.assertEqual(self.call('clothing','/internal/v1/preferences',owner=owner)[1]['history_count'],1)
        rec=self.call('clothing','/internal/v1/recommendations',owner=owner)[1]
        self.assertEqual(rec['items'][0]['id'],'camisa-linho')
        self.assertEqual(self.call('clothing','/internal/v1/recommendation-events',{**event,'kind':'add_to_cart'},owner=owner)[0],409)
        self.close_service('clothing','recommendations');self.start('clothing','recommendations')
        self.assertEqual(self.call('clothing','/internal/v1/preferences',owner=owner)[1]['history_count'],1)
        self.assertEqual(self.call('clothing','/internal/v1/recommendation-events',{**event,'event_id':str(uuid4()),'product_id':'unknown'},owner=owner)[0],404)
        self.assertEqual(self.call('clothing','/internal/v1/recommendation-reset',{'store_id':'roupas-demo'},owner=owner)[0],200)
        profile=self.call('clothing','/internal/v1/preferences',owner=owner)[1]
        self.assertEqual(profile['history_count'],0);self.assertFalse(profile['profile']['use_history'])
        self.assertFalse(self.call('clothing','/internal/v1/recommendation-events',{**event,'event_id':str(uuid4())},owner=owner)[1]['saved'])

    def test_d_food_isolation_and_preferences(self):
        response=self.call('food','/internal/v1/preferences')[1]
        self.assertEqual(response['store_id'],'alimentos-demo');self.assertEqual(response['options']['colors'],[])
        rec=self.call('food','/internal/v1/recommendations');self.assertEqual(rec[0],200);self.assertTrue(all(p['kind']=='food' for p in rec[1]['items']))
        self.assertEqual(self.call('food','/internal/v1/preferences',{'store_id':'alimentos-demo','colors':['preta']})[0],422)
        self.assertEqual(self.call('food','/internal/v1/recommendation-events',{'store_id':'alimentos-demo','event_id':str(uuid4()),'product_id':'camiseta','kind':'view'})[0],404)

    def test_z_dependency_unavailable_does_not_fake_recommendations(self):
        self.close_service('clothing','catalog')
        try:
            self.assertEqual(self.call('clothing','/internal/v1/recommendations')[0],503)
            self.assertEqual(self.call('clothing','/health/live')[0],200)
            self.assertEqual(self.call('clothing','/health/ready')[0],503)
        finally:self.start('clothing','catalog')

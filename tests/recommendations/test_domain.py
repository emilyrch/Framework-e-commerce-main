"""Domain/SQLite/decoder tests. Inline async adapters do not claim HTTP coverage."""
import copy
import json
from pathlib import Path
import struct
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4
from pydantic import ValidationError

from domain.catalog import JsonCatalogLoader
from domain.errors import DomainError
from domain.models import CatalogCandidates
from foundation.config import ROOT,load
from foundation.storage import StorageError
from services.orders.catalog_client import HttpResult
from services.recommendations.models import Preferences,SavePreferences,RecordEvent,StoreCommand
from services.recommendations.repository import RecommendationsRepository
from services.recommendations.catalog_client import CandidatesClient
from services.recommendations.ranking import rank
from services.recommendations.service import RecommendationService
from tests.checkout.test_offline import run_inline,inline_thread,inline_wait,no_sleep
from tests.reviews.fixtures import NOW,OWNER


def candidates(variant='clothing'):
    config=load(ROOT/f'configurations/{variant}.json')
    snapshot=JsonCatalogLoader().load(config,ROOT/'demo-data')
    return CatalogCandidates(store_id=config.store_id,catalog_revision=snapshot.catalog_revision,items=tuple(snapshot.products.values()))


class RecommendationTests(unittest.TestCase):
    def setUp(self):
        self.config=load(ROOT/'configurations/clothing.json');self.catalog=candidates()
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.repo=RecommendationsRepository(Path(self.temp.name),self.config);self.repo.initialize()

    def event(self,product='camiseta',kind='view',id=None):
        return RecordEvent(store_id=self.config.store_id,event_id=id or uuid4(),product_id=product,kind=kind)

    def test_ten_clothing_products_have_real_local_images(self):
        self.assertEqual(len(self.catalog.items),10)
        self.assertEqual(len({p.image_url for p in self.catalog.items}),10)
        for product in self.catalog.items:
            path=ROOT/'apps/store-ropa/public'/product.image_url.lstrip('/')
            data=path.read_bytes();self.assertEqual(data[:8],b'\x89PNG\r\n\x1a\n')
            width,height=struct.unpack('>II',data[16:24]);self.assertGreaterEqual(min(width,height),400)

    def test_strict_preferences_events_duplicates_and_budget(self):
        for change in [{'max_price_cents':True},{'max_price_cents':'100'},{'max_price_cents':1.5},{'max_price_cents':0},{'use_history':'true'},{'colors':['Preta','preta']},{'session_owner':OWNER}]:
            with self.subTest(change=change),self.assertRaises(ValidationError):Preferences.model_validate(change)
        with self.assertRaises(ValidationError):RecordEvent.model_validate({'store_id':self.config.store_id,'event_id':str(uuid4()),'product_id':'camiseta','kind':'purchase','price_cents':1})

    def test_discovery_deterministic_unique_and_food(self):
        first=rank(self.catalog,Preferences(),[])
        self.assertEqual(first.mode,'discovery');self.assertEqual(first,rank(self.catalog,Preferences(),[]))
        self.assertEqual(len(first.items),6);self.assertEqual(len({p.id for p in first.items}),6)
        self.assertTrue(all(p.reasons for p in first.items))
        self.assertTrue(all(p.kind=='food' for p in rank(candidates('food'),Preferences(),[]).items))

    def test_explicit_category_budget_and_empty_result(self):
        result=rank(self.catalog,Preferences(categories=('Camisetas e camisas',),max_price_cents=15000),[])
        self.assertEqual(result.mode,'personalized')
        self.assertEqual({p.id for p in result.items[:2]},{'camiseta','camisa-linho'})
        self.assertTrue(all(p.price_cents<=15000 for p in result.items))
        self.assertEqual(rank(self.catalog,Preferences(max_price_cents=1),[]).items,())

    def test_combination_match_is_not_cartesian_or_stock(self):
        shirt=next(p for p in self.catalog.items if p.id=='camiseta')
        just_one=self.catalog.model_copy(update={'items':(shirt,)})
        self.assertEqual(rank(just_one,Preferences(colors=('azul',),sizes=('M',)),[]).items,())
        self.assertEqual(rank(just_one,Preferences(colors=('branca',),sizes=('P',)),[]).items,())
        self.assertEqual(rank(just_one,Preferences(colors=('preta',),sizes=('M',)),[]).items[0].id,'camiseta')

    def test_history_promotes_related_unseen_product_and_ignores_removed(self):
        events=[{'product_id':'camiseta','kind':'view'}]
        result=rank(self.catalog,Preferences(),events)
        self.assertEqual(result.items[0].id,'camisa-linho')
        self.assertIn('histórico',result.items[0].reasons[0])
        self.assertEqual(rank(self.catalog,Preferences(use_history=False),events).mode,'discovery')
        self.assertEqual(rank(self.catalog,Preferences(),[{'product_id':'removed','kind':'view'}]).mode,'discovery')

    def test_profiles_events_durable_and_isolated(self):
        self.repo.save(OWNER,Preferences(categories=('Calças',)),NOW)
        self.repo.record(OWNER,self.event(),NOW)
        restarted=RecommendationsRepository(Path(self.temp.name),self.config);restarted.initialize()
        self.assertEqual(restarted.profile(OWNER).categories,('Calças',));self.assertEqual(len(restarted.events(OWNER)),1)
        self.assertEqual(restarted.profile('b'*64),Preferences());self.assertEqual(restarted.events('b'*64),[])
        with self.assertRaises(StorageError):RecommendationsRepository(Path(self.temp.name),load(ROOT/'configurations/food.json')).initialize()

    def test_event_idempotency_conflict_and_history_limit(self):
        event=self.event();self.assertTrue(self.repo.record(OWNER,event,NOW));self.assertTrue(self.repo.record(OWNER,event,NOW))
        self.assertEqual(len(self.repo.events(OWNER)),1)
        with self.assertRaises(DomainError):self.repo.record(OWNER,self.event(kind='add_to_cart',id=event.event_id),NOW)
        for _ in range(105):self.repo.record(OWNER,self.event(),NOW)
        self.assertEqual(len(self.repo.events(OWNER)),100)

    def test_disable_and_reset_clear_only_the_owner_and_pause(self):
        for owner in [OWNER,'b'*64]:self.repo.record(owner,self.event(),NOW)
        self.repo.save(OWNER,Preferences(use_history=False),NOW)
        self.assertFalse(self.repo.record(OWNER,self.event(),NOW));self.assertEqual(self.repo.events(OWNER),[])
        self.assertEqual(len(self.repo.events('b'*64)),1)
        self.repo.save(OWNER,Preferences(categories=('Calças',)),NOW);self.repo.reset(OWNER,NOW)
        self.assertEqual(self.repo.profile(OWNER),Preferences(use_history=False))


class RecommendationBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.config=load(ROOT/'configurations/clothing.json');self.data=candidates()
        self.repo=RecommendationsRepository(Path(self.temp.name),self.config);self.repo.initialize()
        for name,value in [('to_thread',inline_thread),('wait_for',inline_wait),('sleep',no_sleep)]:
            ctx=patch('asyncio.'+name,value);ctx.start();self.addCleanup(ctx.stop)

    def test_service_validates_options_store_and_unknown_event(self):
        outer=self
        class Source:
            async def fetch(self):return outer.data
        service=RecommendationService(self.config,self.repo,Source(),lambda:NOW)
        result=run_inline(service.save(OWNER,SavePreferences(store_id=self.config.store_id,colors=('preta',),sizes=('M',))))
        self.assertEqual(result.profile.colors,('preta',))
        for body in [SavePreferences(store_id=self.config.store_id,colors=('unknown',)),SavePreferences(store_id='alimentos-demo')]:
            with self.assertRaises(DomainError):run_inline(service.save(OWNER,body))
        with self.assertRaises(DomainError):run_inline(service.record(OWNER,RecordEvent(store_id=self.config.store_id,event_id=uuid4(),product_id='unknown',kind='view')))
        self.assertTrue(run_inline(service.reset(OWNER,StoreCommand(store_id=self.config.store_id))).cleared)

    def test_catalog_client_checks_response_identity_domain_and_retries(self):
        outer=self
        class Transport:
            count=0;mode='ok'
            async def request(self,method,url,headers,body,timeout):
                self.count+=1
                if self.mode=='timeout':raise TimeoutError
                payload=outer.data.model_dump(mode='json')
                if self.mode=='domain':payload=candidates('food').model_dump(mode='json')
                wire={'x-store-id':outer.config.store_id,'x-config-hash':outer.config.config_hash,'content-type':'application/json'}
                if self.mode=='identity':wire['x-config-hash']='0'*64
                return HttpResult(200,wire,b'{}' if self.mode=='malformed' else json.dumps(payload).encode())
        transport=Transport();client=CandidatesClient(self.config,'http://127.0.0.1','test-token',transport)
        self.assertEqual(run_inline(client.fetch()),self.data)
        for mode in ['domain','identity','malformed','timeout']:
            transport.mode=mode;transport.count=0
            with self.assertRaises(DomainError):run_inline(client.fetch())
            self.assertEqual(transport.count,2 if mode=='timeout' else 1)

    def test_real_auth_dependencies_reject_spoofed_owner_and_wrong_role(self):
        from fastapi import Request
        from fastapi.security import HTTPAuthorizationCredentials
        from foundation.auth import internal_access,trusted_session
        from foundation.errors import ApiError
        token='test-only-'*8
        app=SimpleNamespace(state=SimpleNamespace(settings=SimpleNamespace(config=self.config,incoming_credentials=(('web',token),))))
        request=Request({'type':'http','app':app,'headers':[(b'x-session-owner',b'a'*64)]})
        credentials=HTTPAuthorizationCredentials(scheme='Bearer',credentials=token)
        self.assertIsNone(run_inline(internal_access('web')(request,credentials,self.config.store_id,self.config.config_hash)))
        self.assertEqual(run_inline(trusted_session(request,None)),OWNER)
        for creds,role,hash in [(None,'web',self.config.config_hash),(credentials,'recommendations',self.config.config_hash),(credentials,'web','0'*64)]:
            with self.assertRaises(ApiError):run_inline(internal_access(role)(request,creds,self.config.store_id,hash))
        forged=Request({'type':'http','app':app,'headers':[(b'x-session-owner',b'not-an-owner')]})
        with self.assertRaises(ApiError):run_inline(trusted_session(forged,None))

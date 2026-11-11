import copy
import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from domain.composition import compose
from domain.delivery import Address, ScheduledDelivery, UnscheduledDelivery
from domain.errors import DomainError
from domain.models import ResolveRequest, ResolvedFood
from foundation.config import ROOT, load, validate
from services.catalog.service import CatalogService


ADDRESS={'recipient':'Cliente Fictício','street':'Rua Exemplo','number':'s/n','district':'Centro','city':'São Paulo','state':'SP','postal_code':'01001000'}


class DomainComponentTests(unittest.TestCase):
    def service(self,variant):
        config=load(ROOT/f'configurations/{variant}.json');components=compose(config)
        return CatalogService(components.catalog_loader.load(config),components.selection),components

    def test_composition_selection_and_atomic_resolution(self):
        service,components=self.service('clothing')
        body={'store_id':'roupas-demo','items':[
            {'product_id':'camiseta','quantity':1,'combination_id':'camiseta-m-preta'},
            {'product_id':'camiseta','quantity':2,'combination_id':'camiseta-g-azul'}]}
        result=service.resolve(ResolveRequest.model_validate(body))
        self.assertEqual([i.combination.id for i in result.items],['camiseta-m-preta','camiseta-g-azul'])
        self.assertIsInstance(components.delivery,UnscheduledDelivery)
        for name,items,code in [
            ('missing-combination',[{'product_id':'camiseta','quantity':1}],'SELECTION_INVALID'),
            ('unregistered',[{'product_id':'camiseta','quantity':1,'combination_id':'camiseta-m-azul'}],'SELECTION_INVALID'),
            ('other-product',[{'product_id':'camiseta','quantity':1,'combination_id':'jaqueta-leve-m-verde'}],'SELECTION_INVALID'),
            ('disabled',[{'product_id':'camiseta','quantity':1,'combination_id':'camiseta-p-branca'}],'SELECTION_INVALID'),
            ('duplicate',[body['items'][0],body['items'][0]],'DUPLICATE_LINE'),
            ('partial',[body['items'][0],{'product_id':'unknown','quantity':1}],'SELECTION_INVALID'),
        ]:
            with self.subTest(name=name),self.assertRaises(DomainError) as error:
                service.resolve(ResolveRequest.model_validate({'store_id':'roupas-demo','items':items}))
            self.assertEqual(error.exception.code,code)
        # A failed resolution does not mutate the immutable loaded catalogue.
        self.assertEqual(service.resolve(ResolveRequest.model_validate(body)),result)

    def test_food_selection_forbidden_fields_and_duplicates(self):
        service,components=self.service('food')
        result=service.resolve(ResolveRequest.model_validate({'store_id':'alimentos-demo','items':[{'product_id':'biscoito','quantity':2},{'product_id':'suco','quantity':1}]}))
        self.assertIsInstance(components.delivery,ScheduledDelivery)
        self.assertEqual(result.items[0].sale_unit,'unit')
        self.assertEqual(result.items[0].food_information.allergens.status,'known')
        for combination in [None,'camiseta-m-preta']:
            with self.subTest(combination=combination):
                try:
                    request=ResolveRequest.model_validate({'store_id':'alimentos-demo','items':[{'product_id':'biscoito','quantity':1,'combination_id':combination}]})
                    with self.assertRaises(DomainError):service.resolve(request)
                except ValidationError:
                    pass
        with self.assertRaises(DomainError) as error:
            service.resolve(ResolveRequest.model_validate({'store_id':'alimentos-demo','items':[{'product_id':'biscoito','quantity':1}]*2}))
        self.assertEqual(error.exception.code,'DUPLICATE_LINE')
        with self.assertRaises(ValidationError):
            ResolveRequest.model_validate({'store_id':'alimentos-demo','items':[{'product_id':'biscoito','quantity':1,'unit_price_cents':1}]})

    def test_integer_totals_and_maximums(self):
        service,components=self.service('food')
        items=service.resolve(ResolveRequest.model_validate({'store_id':'alimentos-demo','items':[{'product_id':'biscoito','quantity':2},{'product_id':'suco','quantity':1}]})).items
        result=components.totals.calculate(items)
        self.assertEqual([line.line_total_cents for line in result.lines],[5180,1390])
        self.assertEqual(result.subtotal_cents,6570)
        self.assertEqual(result.total_cents,6570)
        self.assertEqual((result.shipping_cents,result.discount_cents),(0,0))
        base=items[0].model_dump()
        maximum=tuple(ResolvedFood.model_validate({**base,'product_id':f'item-{i}','quantity':100,'unit_price_cents':10_000_000}) for i in range(50))
        self.assertEqual(components.totals.calculate(maximum).total_cents,50_000_000_000)
        for invalid in [(),maximum+(maximum[0],),items+(items[0],)]:
            with self.assertRaises(DomainError):components.totals.calculate(invalid)
        with self.assertRaises(ValidationError):ResolvedFood.model_validate({**base,'unit_price_cents':10_000_001})

    def test_clothing_totals_keep_distinct_combinations(self):
        service,components=self.service('clothing')
        items=service.resolve(ResolveRequest.model_validate({'store_id':'roupas-demo','items':[
            {'product_id':'camiseta','combination_id':'camiseta-m-preta','quantity':1},
            {'product_id':'camiseta','combination_id':'camiseta-g-azul','quantity':2}]})).items
        self.assertEqual(components.totals.calculate(items).total_cents,26970)


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.zone=ZoneInfo('America/Sao_Paulo')
        self.now=datetime(2026,11,9,8,0,tzinfo=self.zone)
        self.config=load(ROOT/'configurations/food.json')
        self.policy=compose(self.config,clock=lambda:self.now).delivery
        self.address=Address.model_validate(ADDRESS)

    def test_future_deterministic_windows_and_immutable_snapshot(self):
        slots=self.policy.list_slots()
        self.assertEqual(len(slots),14)
        self.assertEqual(slots,self.policy.list_slots())
        self.assertTrue(all(s.starts_at>self.now and s.enabled for s in slots))
        self.assertEqual(slots[0].timezone,'America/Sao_Paulo')
        self.assertEqual(slots[0].starts_at.tzinfo.key,'America/Sao_Paulo')
        snapshot=self.policy.validate(self.address,slots[0].id)
        expected=snapshot.model_dump(mode='json')
        self.now+=timedelta(days=10)
        self.assertEqual(snapshot.model_dump(mode='json'),expected)
        with self.assertRaises(ValidationError):snapshot.slot.starts_at=self.now

    def test_boundary_past_disabled_unknown_and_horizon(self):
        first=self.policy.list_slots()[0]
        for instant in [first.starts_at,first.starts_at+timedelta(microseconds=1),first.starts_at+timedelta(days=1)]:
            self.now=instant
            with self.assertRaises(DomainError) as error:self.policy.validate(self.address,first.id)
            self.assertEqual(error.exception.code,'DELIVERY_SLOT_EXPIRED')
        self.now=first.starts_at-timedelta(microseconds=1)
        self.assertEqual(self.policy.validate(self.address,first.id).slot.id,first.id)
        for identifier in [None,'unknown','food-windows-v1:2026-11-09:unknown','other-policy:2026-11-09:morning','food-windows-v1:2026-11-16:morning']:
            with self.subTest(identifier=identifier),self.assertRaises(DomainError):self.policy.validate(self.address,identifier)
        with self.assertRaises(DomainError):self.policy.validate(self.address)
        changed=copy.deepcopy(self.config.data);changed['delivery']['schedule']['daily_windows'][0]['enabled']=False
        disabled=compose(validate(changed),clock=lambda:self.now).delivery
        self.assertTrue(all(not s.id.endswith(':morning') for s in disabled.list_slots()))
        with self.assertRaises(DomainError) as error:disabled.validate(self.address,first.id)
        self.assertEqual(error.exception.code,'DELIVERY_SLOT_INVALID')

    def test_clothing_rejects_any_window_and_validates_address(self):
        policy=compose(load(ROOT/'configurations/clothing.json')).delivery
        self.assertIsNone(policy.validate(self.address).slot)
        for identifier in [None,'food-windows-v1:2026-11-09:morning']:
            with self.assertRaises(DomainError):policy.validate(self.address,identifier)
        with self.assertRaises(DomainError):policy.list_slots()
        with self.assertRaises(ValidationError):Address.model_validate({**ADDRESS,'postal_code':'invalid'})

    def test_clock_must_be_aware_and_iana_historical_offset(self):
        policy=compose(self.config,clock=lambda:datetime(2026,11,9)).delivery
        with self.assertRaises(ValueError):policy.list_slots()
        historical=compose(self.config,clock=lambda:datetime(2018,12,1,7,tzinfo=timezone.utc)).delivery
        self.assertEqual(historical.list_slots()[0].starts_at.utcoffset(),timedelta(hours=-2))
        self.assertEqual(self.policy.list_slots()[0].starts_at.utcoffset(),timedelta(hours=-3))

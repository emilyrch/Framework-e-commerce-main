import copy
import json
import tempfile
import unicodedata
import unittest
from pathlib import Path

from pydantic import ValidationError

from domain.catalog import CatalogLoadError, JsonCatalogLoader
from domain.models import CatalogData, ResolveRequest
from foundation.config import ROOT, load


def raw_catalog(variant):
    return json.loads((ROOT/f'demo-data/{variant}/products.json').read_text(encoding='utf-8'))


class CatalogModelTests(unittest.TestCase):
    def setUp(self):
        self.loader=JsonCatalogLoader()

    def validate(self, variant, raw):
        return self.loader.validate(raw, load(ROOT/f'configurations/{variant}.json'))

    def test_both_catalogs_and_existing_local_images(self):
        for variant in ['clothing','food']:
            snapshot=self.validate(variant, raw_catalog(variant))
            self.assertGreaterEqual(len(snapshot.products),6)
            for product in snapshot.products.values():
                self.assertTrue((ROOT/'apps/store-ropa/public'/product.image_url.lstrip('/')).is_file())
                self.assertIs(type(product.price_cents),int)
            with self.assertRaises(TypeError): snapshot.products['new']=next(iter(snapshot.products.values()))
            with self.assertRaises(ValidationError): snapshot.data.products[0].price_cents=1
            with self.assertRaises(ValidationError): snapshot.data.products=()

    def test_required_fields_extra_types_limits_and_domain(self):
        mutations=[
            ('missing',lambda r:r['products'][0].pop('name')),
            ('extra',lambda r:r['products'][0].update(stock=4)),
            ('bool-price',lambda r:r['products'][0].update(price_cents=True)),
            ('string-price',lambda r:r['products'][0].update(price_cents='8990')),
            ('fraction-price',lambda r:r['products'][0].update(price_cents=8990.5)),
            ('zero-price',lambda r:r['products'][0].update(price_cents=0)),
            ('high-price',lambda r:r['products'][0].update(price_cents=10_000_001)),
            ('duplicate-product',lambda r:r['products'].append(copy.deepcopy(r['products'][0]))),
            ('wrong-store',lambda r:r.update(store_id='other-store')),
            ('wrong-dataset',lambda r:r.update(dataset_id='other-dataset')),
            ('wrong-domain',lambda r:r.update(domain='food')),
            ('bool-schema',lambda r:r.update(schema_version=True)),
            ('wrong-schema',lambda r:r.update(schema_version=2)),
            ('not-fictional',lambda r:r.update(fictional=False)),
            ('numeric-fictional',lambda r:r.update(fictional=1)),
            ('no-products',lambda r:r.update(products=[])),
            ('too-many-products',lambda r:r.update(products=r['products']*17)),
            ('mixed-kind',lambda r:r['products'].append(raw_catalog('food')['products'][0])),
            ('remote-image',lambda r:r['products'][0].update(image_url='https://example.com/private.png')),
            ('no-category',lambda r:r['products'][0].pop('category')),
        ]
        for name,mutate in mutations:
            with self.subTest(name=name):
                raw=raw_catalog('clothing');mutate(raw)
                with self.assertRaises(CatalogLoadError):self.validate('clothing',raw)

    def test_clothing_combinations_and_forbidden_fields(self):
        for name,mutate in [
            ('no-combinations',lambda r:r['products'][0].pop('combinations')),
            ('empty-combinations',lambda r:r['products'][0].update(combinations=[])),
            ('duplicate-id',lambda r:r['products'][0]['combinations'][1].update(id=r['products'][0]['combinations'][0]['id'])),
            ('duplicate-pair',lambda r:r['products'][0]['combinations'][1].update(size='m',color='PRETA')),
            ('global-id',lambda r:r['products'][1]['combinations'][0].update(id=r['products'][0]['combinations'][0]['id'])),
            ('enabled-string',lambda r:r['products'][0]['combinations'][0].update(enabled='true')),
            ('enabled-int',lambda r:r['products'][0]['combinations'][0].update(enabled=1)),
            ('missing-color',lambda r:r['products'][0]['combinations'][0].pop('color')),
            ('food-metadata',lambda r:r['products'][0].update(food_information={})),
        ]:
            with self.subTest(name=name):
                raw=raw_catalog('clothing');mutate(raw)
                with self.assertRaises(CatalogLoadError):self.validate('clothing',raw)

    def test_food_metadata_allergen_union_and_measurements(self):
        original=raw_catalog('food')
        allergens=[p['food_information']['allergens'] for p in original['products']]
        self.assertTrue(any(a['status']=='known' and a['contains'] for a in allergens))
        self.assertTrue(any(a['status']=='known' and a['contains']==[] and a['may_contain']==[] for a in allergens))
        self.assertTrue(any(a['status']=='unknown' and a['contains'] is None for a in allergens))
        for name,mutate in [
            ('metadata-missing',lambda p:p.pop('food_information')),
            ('ingredients-empty',lambda p:p['food_information'].update(ingredients=[])),
            ('allergens-missing',lambda p:p['food_information'].pop('allergens')),
            ('known-null',lambda p:p['food_information']['allergens'].update(contains=None)),
            ('unknown-empty',lambda p:p['food_information'].update(allergens={'status':'unknown','contains':[],'may_contain':[]})),
            ('duplicate-allergen',lambda p:p['food_information']['allergens'].update(contains=['trigo','TRIGO'])),
            ('contradiction',lambda p:p['food_information']['allergens'].update(may_contain=['trigo'])),
            ('nutrition-missing',lambda p:p['food_information']['nutrition_per_serving'].pop('sodium_mg')),
            ('negative',lambda p:p['food_information']['nutrition_per_serving'].update(protein_g=-1)),
            ('nan',lambda p:p['food_information']['nutrition_per_serving'].update(protein_g=float('nan'))),
            ('too-precise',lambda p:p['food_information']['nutrition_per_serving'].update(protein_g=0.001)),
            ('bool-nutrient',lambda p:p['food_information']['nutrition_per_serving'].update(protein_g=True)),
            ('string-nutrient',lambda p:p['food_information']['nutrition_per_serving'].update(protein_g='2')),
            ('wrong-unit',lambda p:p['food_information']['nutrition_per_serving'].update(serving_unit='kg')),
            ('zero-serving',lambda p:p['food_information']['nutrition_per_serving'].update(serving_amount=0)),
            ('extra',lambda p:p['food_information']['nutrition_per_serving'].update(certified=True)),
            ('by-weight',lambda p:p.update(sale_unit='kg')),
            ('combinations',lambda p:p.update(combinations=[])),
        ]:
            with self.subTest(name=name):
                raw=copy.deepcopy(original);mutate(raw['products'][0])
                with self.assertRaises(CatalogLoadError):self.validate('food',raw)

    def test_revision_ignores_order_format_and_equivalent_text_numbers(self):
        for variant in ['clothing','food']:
            raw=raw_catalog(variant);first=self.validate(variant,raw)
            changed=copy.deepcopy(raw);changed['products'].reverse()
            for p in changed['products']:
                p['name']=' '+unicodedata.normalize('NFD',p['name'])+' '
                if 'combinations' in p:p['combinations'].reverse()
                if 'food_information' in p:
                    info=p['food_information'];info['nutrition_per_serving']['sodium_mg']=float(info['nutrition_per_serving']['sodium_mg'])
                    if info['allergens']['status']=='known':
                        info['allergens']['contains'].reverse();info['allergens']['may_contain'].reverse()
            self.assertEqual(first.catalog_revision,self.validate(variant,changed).catalog_revision)
            self.assertEqual(first.catalog_revision,self.validate(variant,json.loads(json.dumps(raw,indent=8,ensure_ascii=True))).catalog_revision)

    def test_revision_changes_commercial_content(self):
        for variant,mutate in [
            ('clothing',lambda r:r['products'][0].update(price_cents=9000)),
            ('clothing',lambda r:r['products'][0]['combinations'][0].update(enabled=False)),
            ('clothing',lambda r:r['products'][0]['combinations'][0].update(color='vermelha')),
            ('food',lambda r:r['products'][0]['food_information']['nutrition_per_serving'].update(protein_g=3)),
            ('food',lambda r:r['products'][0]['food_information']['allergens'].update(may_contain=['soja'])),
            ('food',lambda r:r['products'][0]['food_information']['ingredients'].reverse()),
        ]:
            with self.subTest(variant=variant):
                raw=raw_catalog(variant);first=self.validate(variant,raw);mutate(raw)
                self.assertNotEqual(first.catalog_revision,self.validate(variant,raw).catalog_revision)

    def test_missing_malformed_duplicate_keys_and_identity(self):
        config=load(ROOT/'configurations/clothing.json')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'clothing').mkdir()
            for body in [None,'not json','{"domain":"clothing","domain":"food"}']:
                with self.subTest(body=body):
                    if body is not None:(root/'clothing/products.json').write_text(body)
                    with self.assertRaises(CatalogLoadError):self.loader.load(config,root)

    def test_selection_shape_and_quantity_strictness(self):
        for quantity in [False,True,'1',1.0,1.5,0,101]:
            with self.subTest(quantity=quantity),self.assertRaises(ValidationError):
                ResolveRequest.model_validate({'store_id':'alimentos-demo','items':[{'product_id':'biscoito','quantity':quantity}]})
        for items in [[],[{'product_id':f'item-{i}','quantity':1} for i in range(51)]]:
            with self.assertRaises(ValidationError):ResolveRequest.model_validate({'store_id':'alimentos-demo','items':items})
        self.assertEqual(len(ResolveRequest.model_validate({'store_id':'alimentos-demo','items':[{'product_id':f'item-{i}','quantity':100} for i in range(50)]}).items),50)

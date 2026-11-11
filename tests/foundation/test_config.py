import copy
import json
import subprocess
import unittest

from foundation.config import ROOT, ConfigurationError, load, validate


class ConfigurationTests(unittest.TestCase):
    def test_shared_vectors(self):
        vectors = json.loads((ROOT / 'shared/config-vectors.json').read_text(encoding='utf-8'))
        for vector in vectors:
            with self.subTest(vector=vector['name']):
                if vector['valid']:
                    result = validate(vector['config'])
                    self.assertEqual(result.config_hash, vector['config_hash'])
                else:
                    with self.assertRaises(ConfigurationError):
                        validate(vector['config'])

    def test_typescript_parity(self):
        result = subprocess.run(['node', '--experimental-strip-types', 'apps/store-ropa/scripts/check-config.ts'],
                                cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_legacy_is_not_a_manifest(self):
        for variant in ['basic','premium']:
            with self.subTest(variant=variant), self.assertRaises(ConfigurationError):
                load(ROOT / f'configurations/{variant}.json')

    def test_nested_unknown_and_bool_rejected(self):
        base = load(ROOT / 'configurations/food.json').data
        for field,value in [('shipping_cents',False),('unknown',1)]:
            config = copy.deepcopy(base)
            config['delivery'][field]=value
            with self.assertRaises(ConfigurationError):
                validate(config)

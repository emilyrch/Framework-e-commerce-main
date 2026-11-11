import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from foundation.config import ROOT


class LauncherTests(unittest.TestCase):
    def test_secret_stability_and_per_store_separation(self):
        spec=importlib.util.spec_from_file_location('launcher',ROOT/'tools/lps.py')
        launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'configurations').mkdir()
            for name in ['clothing','food']:
                (root/f'configurations/{name}.json').write_bytes((ROOT/f'configurations/{name}.json').read_bytes())
            launcher.ROOT=root
            _,path,first=launcher.prepare('clothing')
            original=path.read_bytes()
            self.assertEqual(launcher.prepare('clothing')[2],first)
            self.assertEqual(path.read_bytes(),original)
            _,_,other=launcher.prepare('food')
            self.assertNotEqual(first['WEB_CATALOG_TOKEN'],other['WEB_CATALOG_TOKEN'])
            env=launcher.environment('clothing','catalog')
            self.assertIn('WEB_CATALOG_TOKEN',env)
            self.assertNotIn('ORDERS_PAYMENTS_TOKEN',env)
            self.assertNotIn('SESSION_SECRET',env)
            web=launcher.environment('clothing','web')
            self.assertEqual(web['SESSION_SECRET'],first['SESSION_SECRET'])
            self.assertNotIn('ORDERS_PAYMENTS_TOKEN',web)

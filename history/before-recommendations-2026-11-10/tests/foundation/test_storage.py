import sqlite3
import tempfile
import unittest
from pathlib import Path

from foundation.config import ROOT, load
from foundation.storage import PrivateRepository, StorageError


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.config = load(ROOT/'configurations/clothing.json')

    def repository(self, service='orders'):
        return PrivateRepository(self.directory/(service+'.sqlite'), service, self.config)

    def test_repeat_initialization_preserves_data(self):
        for service in ['orders','payments']:
            with self.subTest(service=service):
                repo=self.repository(service);repo.initialize()
                with repo.connection() as db:
                    if service=='orders':
                        db.execute("INSERT INTO reviews VALUES ('review','roupas-demo','session',?,'{}','{}','rev','now','later')",(self.config.config_hash,))
                    else:
                        db.execute("INSERT INTO authorizations VALUES ('payment','roupas-demo','order',100,'BRL','simulated_pix','hash','approved','now','now')")
                repo.initialize()
                self.assertTrue(repo.ready())
                with repo.connection() as db:
                    table='reviews' if service=='orders' else 'authorizations'
                    self.assertEqual(db.execute(f'SELECT count(*) FROM {table}').fetchone()[0],1)

    def test_wrong_store_service_and_versions(self):
        repo=self.repository();repo.initialize()
        food=load(ROOT/'configurations/food.json')
        with self.assertRaises(StorageError):
            PrivateRepository(repo.path,'orders',food).initialize()
        with self.assertRaises(StorageError):
            PrivateRepository(repo.path,'payments',self.config).initialize()
        for sql in ['PRAGMA user_version=9','UPDATE metadata SET storage_schema_version=9']:
            with repo.connection() as db:db.execute(sql)
            with self.assertRaises(StorageError):repo.initialize()

    def test_legacy_and_tampered_schema_rejected(self):
        repo=self.repository()
        with repo.connection() as db:db.execute('CREATE TABLE orders (id TEXT PRIMARY KEY,payload TEXT)')
        with self.assertRaises(StorageError):repo.initialize()
        other=self.repository('payments');other.initialize()
        with other.connection() as db:db.execute('ALTER TABLE authorizations ADD COLUMN unexpected TEXT')
        with self.assertRaises(StorageError):other.initialize()

    def test_constraints_and_foreign_keys(self):
        repo=self.repository();repo.initialize()
        with repo.connection() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO orders(order_id,store_id,session_owner,attempt_id,review_id,config_hash,snapshot_json,status,created_at,updated_at) VALUES ('o','roupas-demo','s','missing','missing','h','{}','payment_pending','now','now')")
        pay=self.repository('payments');pay.initialize()
        with pay.connection() as db:
            db.execute("INSERT INTO authorizations VALUES ('p','roupas-demo','o',100,'BRL','simulated_pix','h','approved','now','now')")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO authorizations VALUES ('p2','roupas-demo','o',100,'BRL','simulated_pix','h','approved','now','now')")

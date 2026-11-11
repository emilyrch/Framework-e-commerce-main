"""Transações locais e schema inicial; nenhuma operação de compra nesta etapa."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from foundation.config import ConfigurationError, StoreConfig

VERSION = 1
COMMON = """
CREATE TABLE metadata (
 singleton INTEGER PRIMARY KEY CHECK(singleton=1), storage_schema_version INTEGER NOT NULL,
 store_id TEXT NOT NULL, domain TEXT NOT NULL, service TEXT NOT NULL
);
"""
ORDERS = """
CREATE TABLE reviews (
 review_id TEXT PRIMARY KEY, store_id TEXT NOT NULL, session_owner TEXT NOT NULL,
 config_hash TEXT NOT NULL, input_json TEXT NOT NULL, snapshot_json TEXT NOT NULL,
 catalog_revision TEXT NOT NULL, created_at TEXT NOT NULL, expires_at TEXT NOT NULL,
 UNIQUE(review_id,store_id,session_owner)
);
CREATE TABLE attempts (
 attempt_id TEXT PRIMARY KEY, store_id TEXT NOT NULL, session_owner TEXT NOT NULL,
 idempotency_key TEXT NOT NULL, request_hash TEXT NOT NULL, command_json TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('validating','rejected','accepted')),
 response_json TEXT, lease_owner TEXT, lease_until TEXT, version INTEGER NOT NULL DEFAULT 0,
 retry_count INTEGER NOT NULL DEFAULT 0 CHECK(retry_count>=0), next_retry_at TEXT,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(store_id,session_owner,idempotency_key), UNIQUE(attempt_id,store_id,session_owner)
);
CREATE TABLE orders (
 order_id TEXT PRIMARY KEY, store_id TEXT NOT NULL, session_owner TEXT NOT NULL,
 attempt_id TEXT NOT NULL UNIQUE REFERENCES attempts(attempt_id),
 review_id TEXT NOT NULL UNIQUE REFERENCES reviews(review_id), config_hash TEXT NOT NULL,
 snapshot_json TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('payment_pending','payment_unknown','confirmed','payment_conflict')),
 payment_id TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 lease_owner TEXT, lease_until TEXT, version INTEGER NOT NULL DEFAULT 0,
 retry_count INTEGER NOT NULL DEFAULT 0 CHECK(retry_count>=0), next_retry_at TEXT,
 FOREIGN KEY(attempt_id,store_id,session_owner) REFERENCES attempts(attempt_id,store_id,session_owner),
 FOREIGN KEY(review_id,store_id,session_owner) REFERENCES reviews(review_id,store_id,session_owner)
);
CREATE INDEX orders_owner ON orders(store_id,session_owner);
CREATE INDEX attempts_owner ON attempts(store_id,session_owner);
"""
PAYMENTS = """
CREATE TABLE authorizations (
 payment_id TEXT PRIMARY KEY, store_id TEXT NOT NULL, order_id TEXT NOT NULL,
 amount_cents INTEGER NOT NULL CHECK(amount_cents>0), currency TEXT NOT NULL CHECK(currency='BRL'),
 method TEXT NOT NULL CHECK(method='simulated_pix'), request_hash TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status='approved'), created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(store_id,order_id)
);
"""
RECOMMENDATIONS = """
CREATE TABLE profiles (
 store_id TEXT NOT NULL, session_owner TEXT NOT NULL, preferences_json TEXT NOT NULL,
 updated_at TEXT NOT NULL, PRIMARY KEY(store_id,session_owner)
);
CREATE TABLE events (
 store_id TEXT NOT NULL, session_owner TEXT NOT NULL, event_id TEXT NOT NULL,
 product_id TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('view','add_to_cart')),
 created_at TEXT NOT NULL, PRIMARY KEY(store_id,session_owner,event_id),
 FOREIGN KEY(store_id,session_owner) REFERENCES profiles(store_id,session_owner) ON DELETE CASCADE
);
CREATE INDEX recommendation_history ON events(store_id,session_owner,created_at,event_id);
"""
SCHEMAS = {'orders': ORDERS, 'payments': PAYMENTS, 'recommendations': RECOMMENDATIONS}


class StorageError(ConfigurationError):
    pass


class PrivateRepository:
    """Infraestrutura privada do dono; não cria/autoriza pedidos."""
    def __init__(self, path: Path, service: str, config: StoreConfig):
        self.path, self.service, self.config = path, service, config
        if service not in SCHEMAS:
            raise StorageError('STORAGE_INVALID_SERVICE')

    @contextmanager
    def connection(self):
        connection = sqlite3.connect(self.path, timeout=0.5, isolation_level=None)
        try:
            connection.execute('PRAGMA foreign_keys=ON')
            connection.execute('PRAGMA busy_timeout=500')
            connection.execute('PRAGMA synchronous=FULL')
            yield connection
        finally:
            connection.close()

    @contextmanager
    def transaction(self):
        try:
            with self.connection() as db:
                db.row_factory = sqlite3.Row
                db.execute('BEGIN IMMEDIATE')
                # Startup/readiness validate DDL. Every write also checks the bound identity.
                expected = (VERSION, self.config.store_id, self.config.domain, self.service)
                actual = db.execute('SELECT storage_schema_version,store_id,domain,service FROM metadata WHERE singleton=1').fetchone()
                if actual is None or tuple(actual) != expected or db.execute('PRAGMA user_version').fetchone()[0] != VERSION:
                    raise StorageError('STORAGE_IDENTITY_OR_VERSION_MISMATCH')
                yield db
                db.commit()
        except (sqlite3.Error, OSError):
            raise StorageError('STORAGE_UNAVAILABLE') from None

    def read_one(self, sql, parameters):
        try:
            with self.connection() as db:
                db.row_factory = sqlite3.Row
                row = db.execute(sql, parameters).fetchone()
                return dict(row) if row else None
        except (sqlite3.Error, OSError):
            raise StorageError('STORAGE_UNAVAILABLE') from None

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.connection() as db:
                db.execute('BEGIN IMMEDIATE')
                tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
                if not tables:
                    # Execute individual DDL statements without executescript's implicit commit.
                    for statement in (COMMON + SCHEMAS[self.service]).split(';'):
                        if statement.strip():
                            db.execute(statement)
                    db.execute('INSERT INTO metadata VALUES (1,?,?,?,?)', (VERSION, self.config.store_id, self.config.domain, self.service))
                    db.execute(f'PRAGMA user_version={VERSION}')
                self._validate(db)
                db.commit()
        except (sqlite3.Error, OSError):
            raise StorageError('STORAGE_INCOMPATIBLE_OR_UNAVAILABLE') from None

    def _validate(self, db):
        expected = (VERSION, self.config.store_id, self.config.domain, self.service)
        if db.execute('SELECT storage_schema_version,store_id,domain,service FROM metadata WHERE singleton=1').fetchone() != expected:
            raise StorageError('STORAGE_IDENTITY_OR_VERSION_MISMATCH')
        if db.execute('PRAGMA user_version').fetchone()[0] != VERSION:
            raise StorageError('STORAGE_SCHEMA_VERSION_MISMATCH')
        expected_tables = {'orders': {'metadata', 'reviews', 'attempts', 'orders'}, 'payments': {'metadata', 'authorizations'}, 'recommendations': {'metadata', 'profiles', 'events'}}[self.service]
        actual = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        if actual != expected_tables:
            raise StorageError('STORAGE_SCHEMA_MISMATCH')
        # Compare all DDL and constraints to an independently initialized in-memory reference.
        reference = sqlite3.connect(':memory:')
        try:
            reference.executescript(COMMON + SCHEMAS[self.service])
            query = "SELECT type,name,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type,name"
            if db.execute(query).fetchall() != reference.execute(query).fetchall():
                raise StorageError('STORAGE_SCHEMA_MISMATCH')
        finally:
            reference.close()
        if self.service == 'orders':
            old_work = db.execute("SELECT 1 FROM orders WHERE status IN ('payment_pending','payment_unknown') AND config_hash<>? LIMIT 1", (self.config.config_hash,)).fetchone()
            old_attempt = db.execute("SELECT 1 FROM attempts a JOIN reviews r ON json_extract(a.command_json,'$.review_id')=r.review_id WHERE a.status='validating' AND r.config_hash<>? LIMIT 1", (self.config.config_hash,)).fetchone()
            if old_work or old_attempt:
                raise StorageError('STORAGE_PENDING_CONFIG_MISMATCH')

    def ready(self) -> bool:
        try:
            with self.connection() as db:
                db.execute('BEGIN IMMEDIATE')
                self._validate(db)
                db.rollback()
            return True
        except (sqlite3.Error, StorageError, OSError):
            return False

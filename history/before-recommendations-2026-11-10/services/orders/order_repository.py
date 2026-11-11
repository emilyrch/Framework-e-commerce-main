"""Operações atômicas locais. Nenhum HTTP acontece neste módulo."""
import hashlib
import json
from datetime import datetime, timedelta
from uuid import uuid4

from domain.errors import DomainError
from foundation.storage import StorageError


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def owned_lease(row, claim, now):
    return row and row['version'] == claim['version'] and row['lease_owner'] == claim['lease_owner'] and row['lease_until'] and row['lease_until'] > now.isoformat()


class OrderOperations:
    def attempt(self, owner, key):
        return self.read_one('SELECT * FROM attempts WHERE store_id=? AND session_owner=? AND idempotency_key=?', (self.config.store_id, owner, key))

    def order(self, owner, order_id):
        return self.read_one('SELECT * FROM orders WHERE store_id=? AND session_owner=? AND order_id=?', (self.config.store_id, owner, str(order_id)))

    def order_for_attempt(self, attempt_id):
        return self.read_one('SELECT * FROM orders WHERE store_id=? AND attempt_id=?', (self.config.store_id, attempt_id))

    def review(self, owner, review_id):
        return self.read_one('SELECT * FROM reviews WHERE store_id=? AND session_owner=? AND review_id=?', (self.config.store_id, owner, str(review_id)))

    def consumed_review(self, owner, review_id):
        return self.read_one('SELECT order_id FROM orders WHERE store_id=? AND session_owner=? AND review_id=?', (self.config.store_id, owner, str(review_id)))

    def reserve(self, owner, key, command, now):
        payload = encoded(command.model_dump(mode='json'))
        digest = hashlib.sha256(payload.encode()).hexdigest()
        with self.transaction() as db:
            row = db.execute('SELECT * FROM attempts WHERE store_id=? AND session_owner=? AND idempotency_key=?', (self.config.store_id, owner, key)).fetchone()
            if row:
                if row['request_hash'] != digest:
                    raise DomainError('IDEMPOTENCY_KEY_REUSED')
                return dict(row), False
            attempt_id = str(uuid4())
            db.execute('INSERT INTO attempts (attempt_id,store_id,session_owner,idempotency_key,request_hash,command_json,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)',
                       (attempt_id, self.config.store_id, owner, key, digest, payload, 'validating', now.isoformat(), now.isoformat()))
            return dict(db.execute('SELECT * FROM attempts WHERE attempt_id=?', (attempt_id,)).fetchone()), True

    def record(self, table, record_id):
        assert table in {'attempts', 'orders'}
        pk = 'attempt_id' if table == 'attempts' else 'order_id'
        return self.read_one(f'SELECT * FROM {table} WHERE store_id=? AND {pk}=?', (self.config.store_id, record_id))

    def claim(self, table, record_id, now, resume=False):
        assert table in {'attempts', 'orders'}
        pk = 'attempt_id' if table == 'attempts' else 'order_id'
        statuses = {'validating'} if table == 'attempts' else {'payment_pending', 'payment_unknown'}
        with self.transaction() as db:
            row = db.execute(f'SELECT * FROM {table} WHERE store_id=? AND {pk}=?', (self.config.store_id, record_id)).fetchone()
            if not row or row['status'] not in statuses:
                return None
            stamp = now.isoformat()
            if row['lease_until'] and row['lease_until'] > stamp:
                return None
            if row['next_retry_at'] and row['next_retry_at'] > stamp:
                return None
            count = row['retry_count']
            if count >= 5:
                if not resume:
                    return None
                count = 0
            next_retry = (now+timedelta(seconds=45)).isoformat() if count+1 == 5 else row['next_retry_at']
            db.execute(f'UPDATE {table} SET lease_owner=?,lease_until=?,version=version+1,retry_count=?,updated_at=?,next_retry_at=? WHERE {pk}=? AND version=?',
                       (str(uuid4()), (now+timedelta(seconds=15)).isoformat(), count+1, stamp, next_retry, record_id, row['version']))
            return dict(db.execute(f'SELECT * FROM {table} WHERE {pk}=?', (record_id,)).fetchone())

    def reject(self, claim, status, code, now, details=None, fields=()):
        with self.transaction() as db:
            row = db.execute('SELECT * FROM attempts WHERE attempt_id=?', (claim['attempt_id'],)).fetchone()
            if owned_lease(row, claim, now) and row['status'] == 'validating':
                self._reject(db, claim['attempt_id'], status, code, now, details, fields)

    @staticmethod
    def _reject(db, attempt_id, status, code, now, details=None, fields=()):
        db.execute("UPDATE attempts SET status='rejected',response_json=?,lease_owner=NULL,lease_until=NULL,next_retry_at=NULL,updated_at=? WHERE attempt_id=?",
                   (encoded({'http_status': status, 'code': code, 'fields': list(fields), 'details': details}), now.isoformat(), attempt_id))

    def admit(self, claim, review, now):
        with self.transaction() as db:
            attempt = db.execute('SELECT * FROM attempts WHERE attempt_id=?', (claim['attempt_id'],)).fetchone()
            if not owned_lease(attempt, claim, now) or attempt['status'] != 'validating':
                return None
            source = db.execute('SELECT * FROM reviews WHERE review_id=? AND store_id=? AND session_owner=?',
                                (str(review.review_id), self.config.store_id, claim['session_owner'])).fetchone()
            if source is None:
                self._reject(db, claim['attempt_id'], 404, 'REVIEW_NOT_FOUND', now); return None
            if source['config_hash'] != self.config.config_hash:
                self._reject(db, claim['attempt_id'], 409, 'CONFIG_MISMATCH', now); return None
            if datetime.fromisoformat(source['expires_at']) <= now:
                self._reject(db, claim['attempt_id'], 409, 'REVIEW_EXPIRED', now); return None
            slot = getattr(review.delivery, 'slot', None)
            if slot and slot.starts_at <= now:
                self._reject(db, claim['attempt_id'], 409, 'DELIVERY_SLOT_EXPIRED', now); return None
            prior = db.execute('SELECT order_id FROM orders WHERE review_id=?', (str(review.review_id),)).fetchone()
            if prior:
                self._reject(db, claim['attempt_id'], 409, 'REVIEW_ALREADY_USED', now, {'order_id': prior['order_id']}); return None
            order_id = str(uuid4())
            db.execute('INSERT INTO orders (order_id,store_id,session_owner,attempt_id,review_id,config_hash,snapshot_json,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)',
                       (order_id, self.config.store_id, claim['session_owner'], claim['attempt_id'], str(review.review_id), self.config.config_hash,
                        review.model_dump_json(), 'payment_pending', now.isoformat(), now.isoformat()))
            db.execute("UPDATE attempts SET status='accepted',lease_owner=NULL,lease_until=NULL,next_retry_at=NULL,updated_at=? WHERE attempt_id=?", (now.isoformat(), claim['attempt_id']))
            return dict(db.execute('SELECT * FROM orders WHERE order_id=?', (order_id,)).fetchone())

    def defer(self, table, claim, now):
        assert table in {'attempts', 'orders'}
        pk = 'attempt_id' if table == 'attempts' else 'order_id'
        with self.transaction() as db:
            row = db.execute(f'SELECT * FROM {table} WHERE {pk}=?', (claim[pk],)).fetchone()
            if not owned_lease(row, claim, now):
                return
            terminal = {'accepted', 'rejected'} if table == 'attempts' else {'confirmed', 'payment_conflict'}
            if row['status'] in terminal:
                return
            delay = [2, 4, 8, 16, 30][min(row['retry_count'], 5)-1]
            status = 'validating' if table == 'attempts' else 'payment_unknown'
            db.execute(f'UPDATE {table} SET status=?,lease_owner=NULL,lease_until=NULL,next_retry_at=?,updated_at=? WHERE {pk}=?',
                       (status, (now+timedelta(seconds=delay)).isoformat(), now.isoformat(), claim[pk]))

    def finish_payment(self, claim, now, payment_id=None, conflict=False):
        if not conflict and payment_id is None:
            raise StorageError('PAYMENT_CONFIRMATION_MISSING_ID')
        with self.transaction() as db:
            row = db.execute('SELECT * FROM orders WHERE order_id=?', (claim['order_id'],)).fetchone()
            if owned_lease(row, claim, now) and row['status'] in {'payment_pending', 'payment_unknown'}:
                db.execute('UPDATE orders SET status=?,payment_id=?,lease_owner=NULL,lease_until=NULL,next_retry_at=NULL,updated_at=? WHERE order_id=?',
                           ('payment_conflict' if conflict else 'confirmed', None if conflict else str(payment_id), now.isoformat(), claim['order_id']))

    def due(self, table, now, limit=20):
        assert table in {'attempts', 'orders'}
        pk = 'attempt_id' if table == 'attempts' else 'order_id'
        statuses = "('validating')" if table == 'attempts' else "('payment_pending','payment_unknown')"
        with self.connection() as db:
            return [r[0] for r in db.execute(f'SELECT {pk} FROM {table} WHERE store_id=? AND status IN {statuses} AND retry_count<5 AND (lease_until IS NULL OR lease_until<=?) AND (next_retry_at IS NULL OR next_retry_at<=?) ORDER BY created_at LIMIT ?',
                                            (self.config.store_id, now.isoformat(), now.isoformat(), limit))]

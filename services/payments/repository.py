from pathlib import Path
import hashlib
import json
from uuid import uuid4

from foundation.config import StoreConfig
from foundation.storage import PrivateRepository
from domain.errors import DomainError
from services.payments.models import AuthorizationResponse


class PaymentsRepository(PrivateRepository):
    def __init__(self, data_dir: Path, config: StoreConfig):
        super().__init__(data_dir / 'payments.sqlite', 'payments', config)

    def lookup(self, order_id):
        row = self.read_one('SELECT * FROM authorizations WHERE store_id=? AND order_id=?', (self.config.store_id, str(order_id)))
        return self.response(row) if row else None

    @staticmethod
    def response(row):
        payload = {k: row[k] for k in ('store_id', 'order_id', 'payment_id', 'method', 'currency', 'amount_cents', 'status', 'created_at')}
        payload['simulated'] = True
        return AuthorizationResponse.model_validate_json(json.dumps(payload))

    def authorize(self, body, now):
        if body.store_id != self.config.store_id:
            raise DomainError('CONFIG_MISMATCH')
        request_hash = hashlib.sha256(json.dumps(body.model_dump(mode='json'), sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        with self.transaction() as db:
            row = db.execute('SELECT * FROM authorizations WHERE store_id=? AND order_id=?', (self.config.store_id, str(body.order_id))).fetchone()
            if row:
                if row['request_hash'] != request_hash:
                    raise DomainError('PAYMENT_CONFLICT')
                return self.response(row), False
            db.execute('INSERT INTO authorizations VALUES (?,?,?,?,?,?,?,?,?,?)', (
                str(uuid4()), self.config.store_id, str(body.order_id), body.amount_cents, body.currency,
                body.method, request_hash, 'approved', now.isoformat(), now.isoformat()))
            row = db.execute('SELECT * FROM authorizations WHERE store_id=? AND order_id=?', (self.config.store_id, str(body.order_id))).fetchone()
            result = self.response(row)
        return result, True

from pathlib import Path
import json
import re
import sqlite3

from foundation.config import StoreConfig
from foundation.storage import PrivateRepository, StorageError
from services.orders.models import SESSION_OWNER_PATTERN


class OrdersRepository(PrivateRepository):
    def __init__(self, data_dir: Path, config: StoreConfig):
        super().__init__(data_dir / 'orders.sqlite', 'orders', config)

    def save_review(self, session_owner, body, review):
        if not re.fullmatch(SESSION_OWNER_PATTERN, session_owner) or (review.store_id, review.config_hash) != (self.config.store_id, self.config.config_hash):
            raise StorageError('REVIEW_IDENTITY_MISMATCH')
        input_json = json.dumps(body.model_dump(mode='json'), ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        snapshot_json = review.model_dump_json()
        try:
            with self.connection() as db:
                db.execute('BEGIN IMMEDIATE')
                self._validate(db)
                db.execute('INSERT INTO reviews VALUES (?,?,?,?,?,?,?,?,?)', (
                    str(review.review_id), review.store_id, session_owner, review.config_hash,
                    input_json, snapshot_json, review.catalog_revision, review.created_at.isoformat(), review.expires_at.isoformat(),
                ))
                db.commit()
        except (sqlite3.Error, OSError, StorageError):
            raise StorageError('ORDER_STORAGE_UNAVAILABLE') from None

import json
from pathlib import Path
from domain.errors import DomainError
from foundation.storage import PrivateRepository
from services.recommendations.models import Preferences


class RecommendationsRepository(PrivateRepository):
    def __init__(self, data_dir: Path, config):
        super().__init__(data_dir/'recommendations.sqlite', 'recommendations', config)

    def profile(self, owner):
        row = self.read_one('SELECT preferences_json FROM profiles WHERE store_id=? AND session_owner=?', (self.config.store_id, owner))
        return Preferences.model_validate_json(row['preferences_json']) if row else Preferences()

    def events(self, owner):
        with self.connection() as db:
            rows = db.execute('SELECT product_id,kind FROM events WHERE store_id=? AND session_owner=? ORDER BY created_at,event_id', (self.config.store_id, owner)).fetchall()
            return [{'product_id':r[0], 'kind':r[1]} for r in rows]

    def save(self, owner, preferences, now):
        with self.transaction() as db:
            db.execute('INSERT INTO profiles VALUES (?,?,?,?) ON CONFLICT(store_id,session_owner) DO UPDATE SET preferences_json=excluded.preferences_json,updated_at=excluded.updated_at',
                       (self.config.store_id, owner, preferences.model_dump_json(), now.isoformat()))
            if not preferences.use_history:
                db.execute('DELETE FROM events WHERE store_id=? AND session_owner=?', (self.config.store_id, owner))

    def record(self, owner, event, now):
        with self.transaction() as db:
            profile = db.execute('SELECT preferences_json FROM profiles WHERE store_id=? AND session_owner=?', (self.config.store_id, owner)).fetchone()
            if profile and not Preferences.model_validate_json(profile['preferences_json']).use_history: return False
            if not profile:
                db.execute('INSERT INTO profiles VALUES (?,?,?,?)', (self.config.store_id, owner, Preferences().model_dump_json(), now.isoformat()))
            prior = db.execute('SELECT product_id,kind FROM events WHERE store_id=? AND session_owner=? AND event_id=?', (self.config.store_id, owner, str(event.event_id))).fetchone()
            if prior:
                if (prior['product_id'],prior['kind']) != (event.product_id,event.kind): raise DomainError('EVENT_ID_REUSED')
                return True
            db.execute('INSERT INTO events VALUES (?,?,?,?,?,?)', (self.config.store_id, owner, str(event.event_id), event.product_id, event.kind, now.isoformat()))
            db.execute('DELETE FROM events WHERE store_id=? AND session_owner=? AND event_id IN (SELECT event_id FROM events WHERE store_id=? AND session_owner=? ORDER BY created_at DESC,rowid DESC LIMIT -1 OFFSET 100)',
                       (self.config.store_id, owner, self.config.store_id, owner))
            return True

    def reset(self, owner, now):
        self.save(owner, Preferences(use_history=False), now)

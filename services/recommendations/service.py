import asyncio
import sqlite3
from pydantic import ValidationError
from domain.errors import DomainError
from foundation.storage import StorageError
from services.recommendations.models import Preferences, PreferenceOptions, ProfileResponse, EventResponse, ResetResponse
from services.recommendations.ranking import rank


class RecommendationService:
    def __init__(self, config, repository, catalog, clock):
        self.config,self.repository,self.catalog,self.clock = config,repository,catalog,clock

    async def db(self, name, *args):
        try: return await asyncio.to_thread(getattr(self.repository,name), *args)
        except (StorageError, sqlite3.Error, OSError, ValidationError): raise DomainError('RECOMMENDATION_STORAGE_UNAVAILABLE') from None

    def check_store(self, body):
        if body.store_id != self.config.store_id: raise DomainError('CONFIG_MISMATCH')

    @staticmethod
    def options(catalog):
        combinations=[c for p in catalog.items for c in getattr(p,'combinations',()) if c.enabled]
        return PreferenceOptions(categories=tuple(sorted({p.category for p in catalog.items})), colors=tuple(sorted({c.color for c in combinations})), sizes=tuple(sorted({c.size for c in combinations})))

    async def profile(self, owner):
        catalog=await self.catalog.fetch()
        return ProfileResponse(store_id=self.config.store_id, profile=await self.db('profile',owner), options=self.options(catalog), history_count=len(await self.db('events',owner)))

    async def save(self, owner, body):
        self.check_store(body)
        catalog=await self.catalog.fetch(); options=self.options(catalog)
        for field in ['categories','colors','sizes']:
            allowed={v.casefold() for v in getattr(options,field)}
            if any(v.casefold() not in allowed for v in getattr(body,field)): raise DomainError('INPUT_INVALID', ({'path':field,'code':'unknown_preference'},))
        profile=Preferences.model_validate(body.model_dump(exclude={'store_id'}))
        await self.db('save',owner,profile,self.clock())
        return ProfileResponse(store_id=self.config.store_id,profile=profile,options=options,history_count=len(await self.db('events',owner)))

    async def recommend(self, owner):
        catalog=await self.catalog.fetch()
        return rank(catalog,await self.db('profile',owner),await self.db('events',owner))

    async def record(self, owner, body):
        self.check_store(body)
        if not (await self.db('profile',owner)).use_history: return EventResponse(store_id=self.config.store_id,event_id=body.event_id,saved=False)
        catalog=await self.catalog.fetch()
        if body.product_id not in {p.id for p in catalog.items}: raise DomainError('PRODUCT_NOT_FOUND')
        saved=await self.db('record',owner,body,self.clock())
        return EventResponse(store_id=self.config.store_id,event_id=body.event_id,saved=saved)

    async def reset(self, owner, body):
        self.check_store(body); await self.db('reset',owner,self.clock())
        return ResetResponse(store_id=self.config.store_id)

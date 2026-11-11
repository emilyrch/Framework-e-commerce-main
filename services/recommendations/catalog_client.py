import asyncio
from http.client import HTTPException
from pydantic import ValidationError
from domain.errors import DomainError
from foundation.http_transport import UrllibTransport
from services.recommendations.models import CatalogCandidates


class CandidatesClient:
    def __init__(self, config, url, token, transport=None):
        self.config, self.url, self.token = config, url, token
        self.transport = transport or UrllibTransport()

    async def fetch(self):
        headers = {'Authorization':'Bearer '+self.token, 'X-Store-Id':self.config.store_id, 'X-Config-Hash':self.config.config_hash}
        for attempt in range(2):
            try:
                result = await asyncio.wait_for(self.transport.request('GET',self.url+'/internal/v1/recommendation-candidates',headers,None,1.5),timeout=1.5)
            except (OSError, TimeoutError, HTTPException):
                if attempt == 0: await asyncio.sleep(.1); continue
                raise DomainError('DEPENDENCY_UNAVAILABLE') from None
            if result.status in {500,502,503,504}:
                if attempt == 0: await asyncio.sleep(.1); continue
                raise DomainError('DEPENDENCY_UNAVAILABLE')
            if result.status == 409: raise DomainError('CONFIG_MISMATCH')
            if result.status != 200: raise DomainError('DEPENDENCY_UNAVAILABLE')
            if result.headers.get('x-store-id') != self.config.store_id or result.headers.get('x-config-hash') != self.config.config_hash:
                raise DomainError('CATALOG_RESPONSE_INVALID')
            if 'application/json' not in result.headers.get('content-type',''): raise DomainError('CATALOG_RESPONSE_INVALID')
            try: catalog = CatalogCandidates.model_validate_json(result.body)
            except (ValidationError, ValueError): raise DomainError('CATALOG_RESPONSE_INVALID') from None
            if catalog.store_id != self.config.store_id or any(p.kind != self.config.domain for p in catalog.items): raise DomainError('CATALOG_RESPONSE_INVALID')
            return catalog

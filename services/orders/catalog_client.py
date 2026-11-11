"""Cliente tipado, sem acesso aos arquivos/banco privados do catálogo."""
import asyncio
import json
import re
from http.client import HTTPException
from typing import Awaitable, Callable, Mapping, Protocol
from urllib.error import URLError

from pydantic import ValidationError

from domain.errors import DomainError
from domain.models import ClothingSelection, ResolveRequest, ResolvedClothing
from foundation.config import StoreConfig
from services.orders.models import CatalogResolution


from foundation.http_transport import HttpResult, HttpTransport, UrllibTransport


class CatalogResolver(Protocol):
    async def resolve(self, request: ResolveRequest) -> CatalogResolution: ...


class CatalogClient:
    def __init__(self, config: StoreConfig, url: str, token: str, transport: HttpTransport | None = None,
                 timeout: float = 1.5, retry_delay: float = 0.1,
                 sleep: Callable[[float], Awaitable[None]] = asyncio.sleep):
        self.config, self.url, self.token = config, url.rstrip('/') + '/internal/v1/selections/resolve', token
        self.transport, self.timeout, self.retry_delay, self.sleep = transport or UrllibTransport(), timeout, retry_delay, sleep

    async def resolve(self, request: ResolveRequest) -> CatalogResolution:
        headers = {'Authorization': 'Bearer ' + self.token, 'X-Store-Id': self.config.store_id,
                   'X-Config-Hash': self.config.config_hash, 'Content-Type': 'application/json'}
        body = request.model_dump_json().encode('utf-8')  # Only store/selection; never address/session.
        for attempt in range(2):
            try:
                result = await asyncio.wait_for(self.transport.post(self.url, headers, body, self.timeout), timeout=self.timeout)
            except (OSError, URLError, TimeoutError):
                result = None
            except (HTTPException, ValueError):
                raise DomainError('CATALOG_RESPONSE_INVALID') from None
            transient = result is None or result.status in {500, 502, 503, 504}
            if transient:
                if attempt == 0:
                    await self.sleep(self.retry_delay)
                    continue
                raise DomainError('DEPENDENCY_UNAVAILABLE')
            return self._validate(result, request)
        raise DomainError('DEPENDENCY_UNAVAILABLE')

    def _validate(self, result: HttpResult, request: ResolveRequest) -> CatalogResolution:
        if result.status in {401, 403}:
            raise DomainError('DEPENDENCY_UNAVAILABLE')
        if 300 <= result.status < 400:
            raise DomainError('CATALOG_RESPONSE_INVALID')
        if not result.headers.get('x-store-id') or not result.headers.get('x-config-hash'):
            raise DomainError('CATALOG_RESPONSE_INVALID')
        if result.headers.get('x-store-id') != self.config.store_id or result.headers.get('x-config-hash') != self.config.config_hash:
            raise DomainError('CONFIG_MISMATCH')
        if result.headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json':
            raise DomainError('CATALOG_RESPONSE_INVALID')
        if result.status != 200:
            try:
                envelope = json.loads(result.body)
                error = envelope['error']
                code = error['code']
                if not isinstance(code, str):
                    raise TypeError
            except (ValueError, KeyError, TypeError):
                raise DomainError('CATALOG_RESPONSE_INVALID') from None
            if result.status == 409 and code == 'CONFIG_MISMATCH':
                raise DomainError('CONFIG_MISMATCH')
            if result.status == 422 and code in {'SELECTION_INVALID', 'DUPLICATE_LINE'}:
                fields = error.get('fields', [])
                if not isinstance(fields, list) or len(fields) > 20 or any(
                    not isinstance(f, dict) or set(f) != {'path', 'code'} or not isinstance(f['path'], str)
                    or not isinstance(f['code'], str)
                    or not re.fullmatch(r'items\.[0-9]{1,2}(\.(product_id|combination_id|quantity))?', f['path'])
                    or f['code'] not in {'invalid_selection', 'unknown_product', 'invalid_combination', 'required_combination', 'forbidden_combination', 'duplicate_line'}
                    for f in fields
                ):
                    raise DomainError('CATALOG_RESPONSE_INVALID')
                raise DomainError(code, tuple(fields))
            raise DomainError('CATALOG_RESPONSE_INVALID')
        try:
            resolved = CatalogResolution.model_validate_json(result.body)
        except (ValidationError, ValueError):
            raise DomainError('CATALOG_RESPONSE_INVALID') from None
        if resolved.store_id != self.config.store_id:
            raise DomainError('CONFIG_MISMATCH')
        actual = {}
        for item in resolved.items:
            key = (item.product_id, item.combination.id if isinstance(item, ResolvedClothing) else None)
            if item.kind != self.config.domain or key in actual:
                raise DomainError('CATALOG_RESPONSE_INVALID')
            actual[key] = item
        expected = [(s.product_id, s.combination_id if isinstance(s, ClothingSelection) else None) for s in request.items]
        if len(actual) != len(request.items) or set(actual) != set(expected) or any(actual[k].quantity != s.quantity for k, s in zip(expected, request.items)):
            raise DomainError('CATALOG_RESPONSE_INVALID')
        return resolved.model_copy(update={'items': tuple(actual[key] for key in expected)})

import asyncio
import json
from http.client import HTTPException

from pydantic import ValidationError

from domain.errors import DomainError
from foundation.http_transport import UrllibTransport
from services.payments.models import AuthorizationRequest, AuthorizationResponse


class SimulatedPaymentGateway:
    def __init__(self, config, url, token, transport=None):
        self.config, self.url, self.token = config, url.rstrip('/'), token
        self.transport = transport or UrllibTransport()

    async def _request(self, method, order_id, amount):
        headers = {'Authorization': 'Bearer '+self.token, 'X-Store-Id': self.config.store_id,
                   'X-Config-Hash': self.config.config_hash, 'Content-Type': 'application/json'}
        body = AuthorizationRequest(store_id=self.config.store_id, order_id=order_id, method='simulated_pix', currency='BRL', amount_cents=amount)
        timeout = 1 if method == 'GET' else 2
        try:
            result = await asyncio.wait_for(self.transport.request(method, self.url+'/internal/v1/payments/by-order/'+str(order_id), headers,
                                                                    None if method == 'GET' else body.model_dump_json().encode(), timeout), timeout)
        except (OSError, TimeoutError, HTTPException, ValueError):
            raise DomainError('DEPENDENCY_UNAVAILABLE') from None
        if result.status in {500, 502, 503, 504, 401, 403}:
            raise DomainError('DEPENDENCY_UNAVAILABLE')
        if result.headers.get('x-store-id') != self.config.store_id or result.headers.get('x-config-hash') != self.config.config_hash:
            raise DomainError('CONFIG_MISMATCH')
        if result.headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json':
            raise DomainError('PAYMENT_RESPONSE_INVALID')
        if result.status in {404, 409}:
            try: code = json.loads(result.body)['error']['code']
            except (ValueError, KeyError, TypeError): raise DomainError('PAYMENT_RESPONSE_INVALID') from None
            if method == 'GET' and result.status == 404 and code == 'PAYMENT_NOT_FOUND': return None
            if result.status == 409 and code == 'PAYMENT_CONFLICT': raise DomainError('PAYMENT_CONFLICT')
            if result.status == 409 and code == 'CONFIG_MISMATCH': raise DomainError('CONFIG_MISMATCH')
            raise DomainError('PAYMENT_RESPONSE_INVALID')
        if result.status not in ({200} if method == 'GET' else {200, 201}):
            raise DomainError('PAYMENT_RESPONSE_INVALID')
        try: payment = AuthorizationResponse.model_validate_json(result.body)
        except ValidationError: raise DomainError('PAYMENT_RESPONSE_INVALID') from None
        if (payment.store_id, str(payment.order_id), payment.amount_cents) != (self.config.store_id, str(order_id), amount):
            raise DomainError('PAYMENT_CONFLICT')
        return payment

    async def lookup(self, order_id, amount):
        return await self._request('GET', order_id, amount)

    async def authorize(self, order_id, amount):
        return await self._request('PUT', order_id, amount)

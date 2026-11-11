import asyncio
import json
import time
from datetime import timezone
from uuid import UUID
from pydantic import ValidationError

from domain.errors import DomainError
from foundation.errors import ApiError
from foundation.storage import StorageError
from services.orders.checkout_models import AttemptResponse, OrderResponse, Recovery
from services.orders.models import REQUEST_TYPES, ReviewResponse


def recovery(row):
    if row['status'] in {'confirmed', 'rejected'}:
        return {'action': 'none', 'next_retry_at': None}
    if row['status'] == 'payment_conflict':
        return {'action': 'investigate', 'next_retry_at': None}
    return {'action': 'retry_same_key' if row['retry_count'] >= 5 else 'wait',
            'next_retry_at': row['next_retry_at'] or row['lease_until']}


class Checkout:
    def __init__(self, config, repository, reviews, payments, clock):
        self.config, self.repository, self.reviews, self.payments, self.clock = config, repository, reviews, payments, clock

    def now(self):
        now = self.clock()
        if now.tzinfo is None or now.utcoffset() is None: raise ValueError('Clock must be aware')
        return now.astimezone(timezone.utc)

    async def db(self, method, *args, **kwargs):
        try: return await asyncio.to_thread(getattr(self.repository, method), *args, **kwargs)
        except StorageError: raise DomainError('ORDER_STORAGE_UNAVAILABLE') from None

    async def submit(self, owner, key, command):
        deadline = time.monotonic()+8
        if command.store_id != self.config.store_id:
            raise DomainError('CONFIG_MISMATCH')
        attempt, fresh = await self.db('reserve', owner, key, command, self.now())
        try:
            await asyncio.wait_for(self.drive_attempt(attempt['attempt_id'], resume=True), timeout=max(0.01, deadline-time.monotonic()-1))
        except TimeoutError:
            pass  # Durable state/lease survives. No assumption that a remote call failed.
        return await self.outcome(owner, key, fresh)

    async def drive_attempt(self, attempt_id, resume=False):
        attempt = await self.db('record', 'attempts', attempt_id)
        if not attempt: return
        if attempt['status'] == 'accepted':
            order = await self.db('order_for_attempt', attempt_id)
            if order: await self.drive_order(order['order_id'], resume)
            return
        claim = await self.db('claim', 'attempts', attempt_id, self.now(), resume)
        if not claim: return
        try:
            command = json.loads(claim['command_json'])
            source = await self.db('review', claim['session_owner'], command['review_id'])
            if source is None:
                await self.db('reject', claim, 404, 'REVIEW_NOT_FOUND', self.now()); return
            used = await self.db('consumed_review', claim['session_owner'], command['review_id'])
            if used:
                await self.db('reject', claim, 409, 'REVIEW_ALREADY_USED', self.now(), {'order_id': used['order_id']}); return
            old = ReviewResponse.model_validate_json(source['snapshot_json'])
            if old.review_id != UUID(command['review_id']) or old.store_id != self.config.store_id or old.config_hash != source['config_hash']:
                raise DomainError('ORDER_STORAGE_UNAVAILABLE')
            if old.config_hash != self.config.config_hash:
                await self.db('reject', claim, 409, 'CONFIG_MISMATCH', self.now()); return
            if old.expires_at <= self.now():
                await self.db('reject', claim, 409, 'REVIEW_EXPIRED', self.now()); return
            body = REQUEST_TYPES[self.config.domain].model_validate_json(source['input_json'])
            try:
                _, current = await self.reviews.build_review(body)  # Revalidate without persisting a second review.
            except DomainError as exc:
                if exc.code in {'SELECTION_INVALID', 'DUPLICATE_LINE', 'INPUT_INVALID', 'DELIVERY_SLOT_INVALID'}:
                    await self.db('reject', claim, 409, 'REVIEW_CHANGED', self.now()); return
                if exc.code == 'DELIVERY_SLOT_EXPIRED':
                    await self.db('reject', claim, 409, exc.code, self.now()); return
                raise
            commercial = {'items', 'delivery', 'totals', 'payment_method'}
            if old.model_dump(mode='json', include=commercial) != current.model_dump(mode='json', include=commercial):
                await self.db('reject', claim, 409, 'REVIEW_CHANGED', self.now()); return
            order = await self.db('admit', claim, old, self.now())
        except DomainError as exc:
            if exc.code == 'ORDER_STORAGE_UNAVAILABLE': raise
            await self.db('defer', 'attempts', claim, self.now())
            return
        except (ValidationError, ValueError, KeyError):
            raise DomainError('ORDER_STORAGE_UNAVAILABLE') from None
        if order:
            # admit() returns only after the local commit. No authorization before this point.
            await self.drive_order(order['order_id'])

    async def drive_order(self, order_id, resume=False):
        claim = await self.db('claim', 'orders', order_id, self.now(), resume)
        if not claim: return
        snapshot = ReviewResponse.model_validate_json(claim['snapshot_json'])
        amount = snapshot.totals.total_cents
        try:
            payment = await self.payments.lookup(order_id, amount)
            if payment is None:
                payment = await self.payments.authorize(order_id, amount)
            await self.db('finish_payment', claim, self.now(), payment.payment_id)
        except DomainError as exc:
            if exc.code == 'ORDER_STORAGE_UNAVAILABLE': raise
            if exc.code == 'PAYMENT_CONFLICT':
                await self.db('finish_payment', claim, self.now(), conflict=True)
            else:
                await self.db('defer', 'orders', claim, self.now())

    async def recover_batch(self):
        for table in ['attempts', 'orders']:
            for record_id in await self.db('due', table, self.now()):
                operation = self.drive_attempt if table == 'attempts' else self.drive_order
                try: await asyncio.wait_for(operation(record_id), timeout=8)
                except TimeoutError: pass

    async def outcome(self, owner, key, fresh=False):
        attempt = await self.db('attempt', owner, key)
        if not attempt: raise DomainError('ATTEMPT_NOT_FOUND')
        if attempt['status'] == 'rejected':
            error = json.loads(attempt['response_json'])
            raise ApiError(error['http_status'], error['code'], error['fields'], details=error['details'])
        order = await self.db('order_for_attempt', attempt['attempt_id'])
        if order:
            return self.order_response(order), (201 if fresh and order['status'] == 'confirmed' else 200 if order['status'] in {'confirmed', 'payment_conflict'} else 202)
        return self.attempt_response(attempt, None), 202

    def order_response(self, order):
        if order['status'] == 'confirmed' and not order['payment_id']:
            raise DomainError('ORDER_STORAGE_UNAVAILABLE')
        snapshot = ReviewResponse.model_validate_json(order['snapshot_json']).model_dump(mode='json')
        payload = {key: snapshot[key] for key in ['store_id', 'review_id', 'items', 'delivery', 'totals']}
        payload.update(order_id=order['order_id'], status=order['status'], created_at=order['created_at'], updated_at=order['updated_at'],
                       payment={'payment_id': order['payment_id'], 'method': 'simulated_pix', 'simulated': True,
                                'status': 'approved' if order['status'] == 'confirmed' else 'not_observed', 'amount_cents': snapshot['totals']['total_cents']},
                       recovery=recovery(order))
        return OrderResponse.model_validate_json(json.dumps(payload))

    def attempt_response(self, attempt, order):
        error = json.loads(attempt['response_json']) if attempt['status'] == 'rejected' else None
        return AttemptResponse.model_validate_json(json.dumps({
            'store_id': self.config.store_id, 'attempt_id': attempt['attempt_id'], 'status': attempt['status'],
            'order_id': order['order_id'] if order else None, 'order_status': order['status'] if order else None,
            'recovery': recovery(order or attempt),
            'error': {k: error[k] for k in ['code', 'fields', 'details']} if error else None,
        }))

    async def get_order(self, owner, order_id):
        order = await self.db('order', owner, order_id)
        if not order: raise DomainError('ORDER_NOT_FOUND')
        return self.order_response(order)

    async def get_attempt(self, owner, key):
        attempt = await self.db('attempt', owner, key)
        if not attempt: raise DomainError('ATTEMPT_NOT_FOUND')
        return self.attempt_response(attempt, await self.db('order_for_attempt', attempt['attempt_id']))

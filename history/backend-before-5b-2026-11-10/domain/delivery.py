from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated, Callable, Literal
from zoneinfo import ZoneInfo

from pydantic import Field

from domain.errors import DomainError
from domain.models import FrozenModel, Text

ABSENT = object()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Address(FrozenModel):
    recipient: Annotated[Text, Field(max_length=80)]
    street: Annotated[Text, Field(max_length=120)]
    number: Annotated[Text, Field(max_length=20)]
    district: Annotated[Text, Field(max_length=80)]
    city: Annotated[Text, Field(max_length=80)]
    state: Annotated[str, Field(pattern=r'^[A-Z]{2}$', strict=True)]
    postal_code: Annotated[str, Field(pattern=r'^[0-9]{8}$', strict=True)]
    complement: Annotated[Text, Field(max_length=120)] | None = None


class DeliveryWindow(FrozenModel):
    id: str
    starts_at: datetime
    ends_at: datetime
    timezone: Literal['America/Sao_Paulo'] = 'America/Sao_Paulo'
    enabled: Literal[True] = True


class DeliverySnapshot(FrozenModel):
    address: Address
    shipping_cents: Literal[0] = 0
    slot: DeliveryWindow | None = None


@dataclass(frozen=True)
class UnscheduledDelivery:
    def list_slots(self) -> tuple[DeliveryWindow, ...]:
        raise DomainError('FEATURE_NOT_AVAILABLE')

    def validate(self, address: Address, slot_id=ABSENT) -> DeliverySnapshot:
        if slot_id is not ABSENT:
            raise DomainError('FEATURE_NOT_AVAILABLE')
        return DeliverySnapshot(address=address)


@dataclass(frozen=True)
class WindowDefinition:
    id: str
    start: time
    end: time
    enabled: bool


@dataclass(frozen=True)
class ScheduledDelivery:
    policy_id: str
    days_ahead: int
    windows: tuple[WindowDefinition, ...]
    clock: Callable[[], datetime] = utc_now
    zone: ZoneInfo = ZoneInfo('America/Sao_Paulo')

    def _now(self):
        now = self.clock()
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise ValueError('Clock must return an aware datetime')
        return now.astimezone(self.zone)

    def _window(self, day: date, definition: WindowDefinition):
        start = datetime.combine(day, definition.start, self.zone)
        end = datetime.combine(day, definition.end, self.zone)
        # Exclude nonexistent local instants on historical IANA transitions.
        if any(value.astimezone(timezone.utc).astimezone(self.zone) != value for value in (start, end)):
            return None
        return DeliveryWindow(id=f'{self.policy_id}:{day.isoformat()}:{definition.id}', starts_at=start, ends_at=end)

    def list_slots(self) -> tuple[DeliveryWindow, ...]:
        now = self._now()
        slots = []
        for offset in range(self.days_ahead):
            day = now.date() + timedelta(days=offset)
            for definition in self.windows:
                if definition.enabled:
                    slot = self._window(day, definition)
                    if slot and slot.starts_at > now:
                        slots.append(slot)
        return tuple(sorted(slots, key=lambda s: (s.starts_at, s.id)))

    def validate(self, address: Address, slot_id=ABSENT) -> DeliverySnapshot:
        if not isinstance(slot_id, str):
            raise DomainError('DELIVERY_SLOT_INVALID')
        try:
            policy, day_text, name = slot_id.split(':')
            day = date.fromisoformat(day_text)
            if policy != self.policy_id or day.isoformat() != day_text:
                raise ValueError
        except ValueError:
            raise DomainError('DELIVERY_SLOT_INVALID') from None
        definition = next((w for w in self.windows if w.id == name and w.enabled), None)
        if not definition:
            raise DomainError('DELIVERY_SLOT_INVALID')
        slot = self._window(day, definition)
        now = self._now()
        if not slot:
            raise DomainError('DELIVERY_SLOT_INVALID')
        if slot.starts_at <= now:
            raise DomainError('DELIVERY_SLOT_EXPIRED')
        if not now.date() <= day < now.date() + timedelta(days=self.days_ahead):
            raise DomainError('DELIVERY_SLOT_INVALID')
        return DeliverySnapshot(address=address, slot=slot)

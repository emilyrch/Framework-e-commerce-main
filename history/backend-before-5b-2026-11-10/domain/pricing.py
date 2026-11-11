from typing import Literal

from pydantic import Field

from domain.errors import DomainError
from domain.models import FrozenModel, ResolvedClothing, ResolvedFood, ResolvedItem

MAX_TOTAL_CENTS = 50_000_000_000


class PricedLine(FrozenModel):
    item: ResolvedItem
    line_total_cents: int = Field(gt=0, le=1_000_000_000)


class CalculatedTotals(FrozenModel):
    lines: tuple[PricedLine, ...]
    currency: Literal['BRL'] = 'BRL'
    subtotal_cents: int = Field(gt=0, le=MAX_TOTAL_CENTS)
    shipping_cents: Literal[0] = 0
    discount_cents: Literal[0] = 0
    total_cents: int = Field(gt=0, le=MAX_TOTAL_CENTS)


class IntegerTotalsCalculator:
    def calculate(self, items) -> CalculatedTotals:
        if not isinstance(items, (tuple, list)) or not 1 <= len(items) <= 50:
            raise DomainError('TOTAL_OUT_OF_RANGE')
        lines, identities = [], set()
        for item in items:
            if not isinstance(item, (ResolvedClothing, ResolvedFood)):
                raise DomainError('SELECTION_INVALID')
            if type(item.quantity) is not int or not 1 <= item.quantity <= 100 or type(item.unit_price_cents) is not int or not 1 <= item.unit_price_cents <= 10_000_000:
                raise DomainError('TOTAL_OUT_OF_RANGE')
            identity = (item.product_id, item.combination.id if isinstance(item, ResolvedClothing) else None)
            if identity in identities:
                raise DomainError('DUPLICATE_LINE')
            identities.add(identity)
            lines.append(PricedLine(item=item, line_total_cents=item.quantity * item.unit_price_cents))
        subtotal = sum(line.line_total_cents for line in lines)
        if subtotal > MAX_TOTAL_CENTS:
            raise DomainError('TOTAL_OUT_OF_RANGE')
        return CalculatedTotals(lines=tuple(lines), subtotal_cents=subtotal, total_cents=subtotal)

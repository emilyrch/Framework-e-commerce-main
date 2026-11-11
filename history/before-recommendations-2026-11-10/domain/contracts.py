from datetime import datetime
from pathlib import Path
from typing import Protocol

from domain.catalog import CatalogSnapshot
from domain.delivery import ABSENT, Address, DeliverySnapshot, DeliveryWindow
from domain.models import Product, ResolvedItem, Selection
from domain.pricing import CalculatedTotals
from foundation.config import StoreConfig


class CatalogLoader(Protocol):
    def load(self, config: StoreConfig, data_root: Path) -> CatalogSnapshot: ...
    def validate(self, raw: object, config: StoreConfig) -> CatalogSnapshot: ...


class ProductSelectionValidator(Protocol):
    def validate(self, product: Product, selection: Selection) -> ResolvedItem: ...


class TotalsCalculator(Protocol):
    def calculate(self, items: tuple[ResolvedItem, ...]) -> CalculatedTotals: ...


class DeliveryPolicy(Protocol):
    def list_slots(self) -> tuple[DeliveryWindow, ...]: ...
    def validate(self, address: Address, slot_id=ABSENT) -> DeliverySnapshot: ...


class Clock(Protocol):
    def __call__(self) -> datetime: ...

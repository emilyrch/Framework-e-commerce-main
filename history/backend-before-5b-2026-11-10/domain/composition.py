from dataclasses import dataclass
from datetime import time

from domain.catalog import JsonCatalogLoader
from domain.contracts import CatalogLoader, Clock, DeliveryPolicy, ProductSelectionValidator, TotalsCalculator
from domain.delivery import ScheduledDelivery, UnscheduledDelivery, WindowDefinition, utc_now
from domain.pricing import IntegerTotalsCalculator
from domain.selection import ClothingSelectionValidator, FoodSelectionValidator
from foundation.config import StoreConfig


@dataclass(frozen=True)
class DomainComponents:
    catalog_loader: CatalogLoader
    selection: ProductSelectionValidator
    totals: TotalsCalculator
    delivery: DeliveryPolicy


def scheduled(config: StoreConfig, clock: Clock):
    policy = config.data['delivery']['schedule']
    return ScheduledDelivery(policy['policy_id'], policy['days_ahead'], tuple(
        WindowDefinition(w['id'], time.fromisoformat(w['start']), time.fromisoformat(w['end']), w['enabled'])
        for w in policy['daily_windows']), clock)


REGISTRY = {
    'clothing': (ClothingSelectionValidator, lambda config, clock: UnscheduledDelivery()),
    'food': (FoodSelectionValidator, scheduled),
}


def compose(config: StoreConfig, clock: Clock = utc_now) -> DomainComponents:
    validator, delivery_factory = REGISTRY[config.domain]
    return DomainComponents(JsonCatalogLoader(), validator(), IntegerTotalsCalculator(), delivery_factory(config, clock))

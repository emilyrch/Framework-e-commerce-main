"""Portas implementadas da infraestrutura; sem contratos de compra fictícios."""
from typing import Protocol

from foundation.config import StoreConfig


class ConfigValidator(Protocol):
    def __call__(self, value: object) -> StoreConfig: ...


class StorageProbe(Protocol):
    def initialize(self) -> None: ...
    def ready(self) -> bool: ...

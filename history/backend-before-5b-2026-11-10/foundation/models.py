from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LiveResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')
    service: Literal['catalog', 'orders', 'payments']
    status: Literal['alive']


class ReadyResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')
    service: Literal['catalog', 'orders', 'payments']
    status: Literal['ready', 'not_ready']
    scope: Literal['foundation']
    store_id: str
    config_hash: str = Field(pattern='^[a-f0-9]{64}$')
    checks: dict[str, Literal['ok', 'unavailable', 'mismatch']]
    catalog_revision: str | None = None

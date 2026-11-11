from typing import Annotated, Literal
from pydantic import Field, UUID4, model_validator
from domain.models import FrozenModel, Identifier, Text, ProductSummary, CatalogCandidates

Owner = Annotated[str, Field(pattern=r'^[a-f0-9]{64}$')]
Revision = Annotated[str, Field(pattern=r'^sha256:[a-f0-9]{64}$')]


class Preferences(FrozenModel):
    categories: tuple[Text, ...] = Field(default=(), strict=False, max_length=12)
    colors: tuple[Text, ...] = Field(default=(), strict=False, max_length=12)
    sizes: tuple[Text, ...] = Field(default=(), strict=False, max_length=12)
    max_price_cents: int | None = Field(default=None, strict=True, ge=1, le=10_000_000)
    use_history: bool = True

    @model_validator(mode='after')
    def unique_options(self):
        for options in [self.categories, self.colors, self.sizes]:
            if len({v.casefold() for v in options}) != len(options): raise ValueError('duplicate preference')
        return self


class SavePreferences(Preferences):
    store_id: Identifier


class StoreCommand(FrozenModel):
    store_id: Identifier


class RecordEvent(StoreCommand):
    event_id: UUID4 = Field(strict=False)
    product_id: Identifier
    kind: Literal['view', 'add_to_cart']


class PreferenceOptions(FrozenModel):
    categories: tuple[str, ...]
    colors: tuple[str, ...]
    sizes: tuple[str, ...]


class ProfileResponse(FrozenModel):
    store_id: str
    profile: Preferences
    options: PreferenceOptions
    history_count: int


class RecommendationItem(ProductSummary):
    reasons: tuple[str, ...]


class RecommendationResponse(FrozenModel):
    store_id: str
    catalog_revision: Revision
    algorithm_version: Literal['content-v1'] = 'content-v1'
    mode: Literal['personalized', 'discovery']
    items: tuple[RecommendationItem, ...]


class EventResponse(FrozenModel):
    store_id: str
    event_id: UUID4
    saved: bool


class ResetResponse(FrozenModel):
    store_id: str
    cleared: Literal[True] = True

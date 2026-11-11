import math
import unicodedata
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator


def clean_text(value):
    if isinstance(value, str):
        if any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
            raise ValueError('invalid text')
        return unicodedata.normalize('NFC', value).strip()
    return value


def require_true(value):
    if value is not True:
        raise ValueError('fictional must be true')
    return value


def measurement(value):
    if type(value) not in {int, float}:
        raise ValueError('finite numeric measurement required')
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError('finite numeric measurement required')
    decimal = Decimal(str(value))
    if decimal.normalize().as_tuple().exponent < -2:
        raise ValueError('at most two decimal places')
    return value


Identifier = Annotated[str, BeforeValidator(clean_text), Field(strict=True, min_length=1, max_length=80, pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$')]
Text = Annotated[str, BeforeValidator(clean_text), Field(strict=True, min_length=1, max_length=160)]
Quantity = Annotated[int, Field(strict=True, ge=1, le=100)]
Money = Annotated[int, Field(strict=True, ge=1, le=10_000_000)]
Measure = Annotated[float, BeforeValidator(measurement), Field(ge=0, allow_inf_nan=False)]
TrueFlag = Annotated[Literal[True], BeforeValidator(require_true)]


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True, allow_inf_nan=False)


class Combination(FrozenModel):
    id: Identifier
    size: Annotated[Text, Field(max_length=20)]
    color: Annotated[Text, Field(max_length=40)]
    enabled: bool


class KnownAllergens(FrozenModel):
    status: Literal['known']
    contains: tuple[Text, ...] = Field(strict=False, max_length=32)
    may_contain: tuple[Text, ...] = Field(strict=False, max_length=32)

    @model_validator(mode='after')
    def unique_declarations(self):
        contains = [v.casefold() for v in self.contains]
        possible = [v.casefold() for v in self.may_contain]
        if len(set(contains)) != len(contains) or len(set(possible)) != len(possible) or set(contains) & set(possible):
            raise ValueError('duplicate or contradictory allergen declarations')
        return self


class UnknownAllergens(FrozenModel):
    status: Literal['unknown']
    contains: None
    may_contain: None


Allergens = Annotated[KnownAllergens | UnknownAllergens, Field(discriminator='status')]


class Nutrition(FrozenModel):
    serving_amount: Annotated[Measure, Field(gt=0)]
    serving_unit: Literal['g', 'ml']
    serving_description: Text
    energy_kcal: Measure
    carbohydrates_g: Measure
    total_sugars_g: Measure
    protein_g: Measure
    total_fat_g: Measure
    saturated_fat_g: Measure
    trans_fat_g: Measure
    fiber_g: Measure
    sodium_mg: Measure


class FoodInformation(FrozenModel):
    fictional: TrueFlag
    ingredients: tuple[Text, ...] = Field(strict=False, min_length=1, max_length=64)
    allergens: Allergens
    nutrition_per_serving: Nutrition


class ProductSummary(FrozenModel):
    id: Identifier
    kind: Literal['clothing', 'food']
    name: Annotated[Text, Field(max_length=100)]
    description: Annotated[Text, Field(max_length=600)]
    category: Annotated[Text, Field(max_length=60)]
    price_cents: Money
    currency: Literal['BRL']
    image_url: Annotated[str, Field(strict=True, max_length=200, pattern=r'^/demo/[a-z0-9][a-z0-9/_-]*\.(svg|webp|png|jpg)$')]


class ClothingProduct(ProductSummary):
    kind: Literal['clothing']
    combinations: tuple[Combination, ...] = Field(strict=False, min_length=1, max_length=100)

    @model_validator(mode='after')
    def unique_combinations(self):
        ids = [c.id for c in self.combinations]
        pairs = [(c.size.casefold(), c.color.casefold()) for c in self.combinations]
        if len(set(ids)) != len(ids) or len(set(pairs)) != len(pairs):
            raise ValueError('duplicate combination id or size/color pair')
        return self


class FoodProduct(ProductSummary):
    kind: Literal['food']
    sale_unit: Literal['unit']
    food_information: FoodInformation


Product = Annotated[ClothingProduct | FoodProduct, Field(discriminator='kind')]


class CatalogData(FrozenModel):
    schema_version: Annotated[int, Field(strict=True, ge=1, le=1)]
    store_id: Identifier
    domain: Literal['clothing', 'food']
    dataset_id: Identifier
    fictional: TrueFlag
    products: tuple[Product, ...] = Field(strict=False, min_length=1, max_length=100)

    @model_validator(mode='after')
    def catalog_consistency(self):
        ids = [p.id for p in self.products]
        if len(set(ids)) != len(ids):
            raise ValueError('duplicate product id')
        if any(p.kind != self.domain for p in self.products):
            raise ValueError('product kind does not match catalog domain')
        combination_ids = [c.id for p in self.products if isinstance(p, ClothingProduct) for c in p.combinations]
        if len(set(combination_ids)) != len(combination_ids):
            raise ValueError('combination id must be unique across catalog')
        return self


class FoodSelection(FrozenModel):
    product_id: Identifier
    quantity: Quantity


class ClothingSelection(FoodSelection):
    combination_id: Identifier


Selection = ClothingSelection | FoodSelection


class ResolveRequest(FrozenModel):
    store_id: Identifier
    items: tuple[Selection, ...] = Field(strict=False, min_length=1, max_length=50)


class CombinationSnapshot(FrozenModel):
    id: Identifier
    size: Text
    color: Text


class ResolvedBase(FrozenModel):
    product_id: Identifier
    name: Text
    quantity: Quantity
    unit_price_cents: Money


class ResolvedClothing(ResolvedBase):
    kind: Literal['clothing']
    combination: CombinationSnapshot


class ResolvedFood(ResolvedBase):
    kind: Literal['food']
    sale_unit: Literal['unit']
    food_information: FoodInformation


ResolvedItem = Annotated[ResolvedClothing | ResolvedFood, Field(discriminator='kind')]


class CatalogList(FrozenModel):
    store_id: Identifier
    catalog_revision: str
    items: tuple[ProductSummary, ...]


class CatalogDetail(FrozenModel):
    store_id: Identifier
    catalog_revision: str
    product: Product


class ResolvedList(FrozenModel):
    store_id: Identifier
    catalog_revision: str
    items: tuple[ResolvedItem, ...]

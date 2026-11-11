from domain.errors import DomainError
from domain.models import (
    ClothingProduct, ClothingSelection, CombinationSnapshot, FoodProduct, FoodSelection,
    ResolvedClothing, ResolvedFood,
)


class ClothingSelectionValidator:
    def validate(self, product, selection):
        if not isinstance(product, ClothingProduct) or not isinstance(selection, ClothingSelection):
            raise DomainError('SELECTION_INVALID', ({'path': 'combination_id', 'code': 'required_combination'},))
        combination = next((c for c in product.combinations if c.id == selection.combination_id and c.enabled), None)
        if not combination:
            raise DomainError('SELECTION_INVALID', ({'path': 'combination_id', 'code': 'invalid_combination'},))
        return ResolvedClothing(product_id=product.id, name=product.name, quantity=selection.quantity,
                                unit_price_cents=product.price_cents, kind='clothing',
                                combination=CombinationSnapshot(id=combination.id, size=combination.size, color=combination.color))


class FoodSelectionValidator:
    def validate(self, product, selection):
        if not isinstance(product, FoodProduct) or type(selection) is not FoodSelection:
            raise DomainError('SELECTION_INVALID', ({'path': 'combination_id', 'code': 'forbidden_combination'},))
        return ResolvedFood(product_id=product.id, name=product.name, quantity=selection.quantity,
                            unit_price_cents=product.price_cents, kind='food', sale_unit='unit',
                            food_information=product.food_information)

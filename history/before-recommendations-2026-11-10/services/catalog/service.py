from domain.catalog import CatalogSnapshot
from domain.contracts import ProductSelectionValidator
from domain.errors import DomainError
from domain.models import CatalogDetail, CatalogList, ProductSummary, ResolveRequest, ResolvedList


class CatalogService:
    def __init__(self, snapshot: CatalogSnapshot, selection: ProductSelectionValidator):
        self.snapshot, self.selection = snapshot, selection

    def list_products(self) -> CatalogList:
        items = tuple(ProductSummary.model_validate({key: getattr(product, key) for key in ProductSummary.model_fields})
                      for product in self.snapshot.products.values())
        return CatalogList(store_id=self.snapshot.data.store_id, catalog_revision=self.snapshot.catalog_revision, items=items)

    def detail(self, product_id: str) -> CatalogDetail:
        product = self.snapshot.products.get(product_id)
        if product is None:
            raise DomainError('PRODUCT_NOT_FOUND')
        return CatalogDetail(store_id=self.snapshot.data.store_id, catalog_revision=self.snapshot.catalog_revision, product=product)

    def resolve(self, request: ResolveRequest) -> ResolvedList:
        if request.store_id != self.snapshot.data.store_id:
            raise DomainError('CONFIG_MISMATCH')
        identities, resolved = set(), []
        for index, selected in enumerate(request.items):
            identity = (selected.product_id, getattr(selected, 'combination_id', None))
            field = {'path': f'items.{index}', 'code': 'invalid_selection'}
            if identity in identities:
                raise DomainError('DUPLICATE_LINE', ({**field, 'code': 'duplicate_line'},))
            identities.add(identity)
            product = self.snapshot.products.get(selected.product_id)
            if product is None:
                raise DomainError('SELECTION_INVALID', ({'path': f'items.{index}.product_id', 'code': 'unknown_product'},))
            try:
                resolved.append(self.selection.validate(product, selected))
            except DomainError as exc:
                fields = tuple({**entry, 'path': f'items.{index}.{entry["path"]}'} for entry in exc.fields) or (field,)
                raise DomainError('SELECTION_INVALID', fields) from None
        return ResolvedList(store_id=self.snapshot.data.store_id, catalog_revision=self.snapshot.catalog_revision, items=tuple(resolved))

from fastapi import APIRouter, Depends, Request

from domain.models import CatalogDetail, CatalogList, ResolveRequest, ResolvedList, CatalogCandidates
from foundation.auth import internal_access

router = APIRouter(prefix='/internal/v1', tags=['catalog'])


@router.get('/products', response_model=CatalogList, dependencies=[Depends(internal_access('web'))])
async def products(request: Request):
    return request.app.state.catalog.list_products()


@router.get('/products/{product_id}', response_model=CatalogDetail, dependencies=[Depends(internal_access('web'))])
async def product(product_id: str, request: Request):
    return request.app.state.catalog.detail(product_id)


@router.post('/selections/resolve', response_model=ResolvedList, dependencies=[Depends(internal_access('orders'))])
async def resolve(body: ResolveRequest, request: Request):
    return request.app.state.catalog.resolve(body)


@router.get('/recommendation-candidates',response_model=CatalogCandidates,dependencies=[Depends(internal_access('recommendations'))])
async def recommendation_candidates(request: Request):
    catalog=request.app.state.catalog
    return CatalogCandidates(store_id=catalog.snapshot.data.store_id,catalog_revision=catalog.snapshot.catalog_revision,items=tuple(catalog.snapshot.products.values()))

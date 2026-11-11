import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from foundation.errors import ApiError, register_errors
from foundation.auth import internal_access
from foundation.config import ROOT
from foundation.health import readiness
from foundation.models import LiveResponse, ReadyResponse
from foundation.settings import settings
from services.orders.repository import OrdersRepository
from services.payments.repository import PaymentsRepository
from services.catalog.service import CatalogService
from domain.composition import compose
from domain.delivery import utc_now


def create_app(service: str, *, clock=utc_now) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        config = settings(service)  # Failure before accepting requests, without logging secrets.
        repository = None
        if service in {'orders', 'payments'}:
            repository = {'orders': OrdersRepository, 'payments': PaymentsRepository}[service](config.data_dir, config.config)
            repository.initialize()
        app.state.settings, app.state.repository = config, repository
        app.state.components = compose(config.config, clock=clock)
        app.state.catalog = None
        app.state.reviews = None
        if service == 'catalog':
            snapshot = app.state.components.catalog_loader.load(config.config, Path(os.environ.get('CATALOG_DATA_ROOT', ROOT / 'demo-data')))
            app.state.catalog = CatalogService(snapshot, app.state.components.selection)
        if service == 'orders':
            from services.orders.catalog_client import CatalogClient
            from services.orders.service import ReviewService
            _, url, token = config.dependencies[0]
            client = CatalogClient(config.config, url, token)
            app.state.reviews = ReviewService(config.config, repository, client, app.state.components, clock)
        try:
            yield
        finally:
            # Repository opens/closes a connection per operation; no persistent handle/worker.
            app.state.repository = None
            app.state.catalog = None
            app.state.reviews = None

    app = FastAPI(title=f'LPS {service} — foundation', version='0.1.0', lifespan=lifespan)
    register_errors(app)
    if service == 'catalog':
        from services.catalog.routes import router
        app.include_router(router)
    if service == 'orders':
        from services.orders.routes import router
        app.include_router(router)

    @app.middleware('http')
    async def headers(request: Request, call_next):
        def decorate(response):
            response.headers['Cache-Control'] = 'no-store'
            current = getattr(request.app.state, 'settings', None)
            if current:
                response.headers['X-Store-Id'] = current.config.store_id
                response.headers['X-Config-Hash'] = current.config.config_hash
            return response

        limited_paths = {'catalog': '/internal/v1/selections/resolve', 'orders': '/internal/v1/reviews'}
        if request.url.path == limited_paths.get(service) and request.method == 'POST':
            if request.headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json':
                from foundation.errors import error_response
                return decorate(error_response(415, 'UNSUPPORTED_MEDIA_TYPE'))
            size, chunks = 0, []
            async for chunk in request.stream():
                size += len(chunk)
                if size > 65536:
                    from foundation.errors import error_response
                    return decorate(error_response(413, 'BODY_TOO_LARGE'))
                chunks.append(chunk)
            request._body = b''.join(chunks)
        response = await call_next(request)
        return decorate(response)

    @app.get('/health/live', tags=['health'], response_model=LiveResponse)
    async def live():
        return {'service': service, 'status': 'alive'}

    @app.get('/health/ready', tags=['health'], dependencies=[Depends(internal_access('web', 'orders'))], response_model=ReadyResponse,
             responses={401: {'description': 'Credencial interna ausente/inválida'},
                        409: {'description': 'Identidade/configuração divergente'},
                        503: {'model': ReadyResponse, 'description': 'Fundação não pronta'}})
    async def ready(request: Request):
        good, result = await readiness(request.app.state.settings, request.app.state.repository, request.app.state.catalog, request.app.state.reviews)
        return JSONResponse(result, status_code=200 if good else 503)

    return app

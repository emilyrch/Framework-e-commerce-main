import uuid

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from domain.errors import DomainError


class ApiError(Exception):
    def __init__(self, status: int, code: str, fields=()):
        self.status, self.code, self.fields = status, code, fields


def error_response(status: int, code: str, fields=()) -> JSONResponse:
    return JSONResponse(status_code=status, content={
        'error': {'code': code, 'message': 'Requisição indisponível ou inválida', 'fields': list(fields), 'retryable': status == 503},
        'request_id': str(uuid.uuid4()),
    }, headers={'Cache-Control': 'no-store'})


def register_errors(app):
    @app.exception_handler(ApiError)
    async def api_error(_request: Request, exc: ApiError):
        return error_response(exc.status, exc.code, exc.fields)

    @app.exception_handler(DomainError)
    async def domain_error(_request: Request, exc: DomainError):
        statuses = {'PRODUCT_NOT_FOUND': 404, 'CONFIG_MISMATCH': 409, 'FEATURE_NOT_AVAILABLE': 409, 'DELIVERY_SLOT_EXPIRED': 409,
                    'DEPENDENCY_UNAVAILABLE': 503, 'CATALOG_RESPONSE_INVALID': 503, 'ORDER_STORAGE_UNAVAILABLE': 503}
        return error_response(statuses.get(exc.code, 422), exc.code, exc.fields)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError):
        errors = exc.errors()
        if any(error['type'] == 'json_invalid' for error in errors):
            return error_response(400, 'MALFORMED_JSON')
        fields = tuple({'path': '.'.join(map(str, error['loc'])), 'code': error['type']} for error in errors[:20])
        return error_response(422, 'INPUT_INVALID', fields)

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, exc: HTTPException):
        return error_response(exc.status_code, 'NOT_FOUND' if exc.status_code == 404 else 'HTTP_ERROR')

    @app.exception_handler(Exception)
    async def unexpected_error(_request: Request, _exc: Exception):
        return error_response(500, 'INTERNAL_ERROR')

import uuid

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from domain.errors import DomainError


class ApiError(Exception):
    def __init__(self, status: int, code: str, fields=(), details=None):
        self.status, self.code, self.fields, self.details = status, code, fields, details


def error_response(status: int, code: str, fields=(), details=None) -> JSONResponse:
    return JSONResponse(status_code=status, content={
        'error': {'code': code, 'message': 'Requisição indisponível ou inválida', 'fields': list(fields), 'retryable': status == 503,
                  **({'details': details} if details else {})},
        'request_id': str(uuid.uuid4()),
    }, headers={'Cache-Control': 'no-store'})


def register_errors(app):
    @app.exception_handler(ApiError)
    async def api_error(_request: Request, exc: ApiError):
        return error_response(exc.status, exc.code, exc.fields, exc.details)

    @app.exception_handler(DomainError)
    async def domain_error(_request: Request, exc: DomainError):
        statuses = {'PRODUCT_NOT_FOUND': 404, 'ORDER_NOT_FOUND': 404, 'ATTEMPT_NOT_FOUND': 404, 'PAYMENT_NOT_FOUND': 404,
                    'CONFIG_MISMATCH': 409, 'FEATURE_NOT_AVAILABLE': 409, 'DELIVERY_SLOT_EXPIRED': 409,
                    'PAYMENT_CONFLICT': 409, 'IDEMPOTENCY_KEY_REUSED': 409,
                    'DEPENDENCY_UNAVAILABLE': 503, 'CATALOG_RESPONSE_INVALID': 503, 'PAYMENT_RESPONSE_INVALID': 503,
                    'ORDER_STORAGE_UNAVAILABLE': 503, 'PAYMENT_STORAGE_UNAVAILABLE': 503,
                    'RECOMMENDATION_STORAGE_UNAVAILABLE': 503, 'EVENT_ID_REUSED': 409}
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

import hmac
import re

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from foundation.errors import ApiError

bearer = HTTPBearer(auto_error=False)


def internal_access(*roles: str):
    async def authenticate(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
                           x_store_id: str | None = Header(None), x_config_hash: str | None = Header(None)):
        current = request.app.state.settings
        matched = set()
        if credentials:
            for role, token in current.incoming_credentials:
                if hmac.compare_digest(credentials.credentials.encode('utf-8'), token.encode('utf-8')):
                    matched.add(role)
        if not matched:
            raise ApiError(401, 'INTERNAL_UNAUTHORIZED')
        if not matched.intersection(roles):
            raise ApiError(403, 'INTERNAL_FORBIDDEN')
        if x_store_id != current.config.store_id or x_config_hash != current.config.config_hash:
            raise ApiError(409, 'CONFIG_MISMATCH')
    return authenticate


async def trusted_session(request: Request, _access=Depends(internal_access('web'))):
    owners = request.headers.getlist('x-session-owner')
    if len(owners) != 1 or not re.fullmatch(r'[a-f0-9]{64}', owners[0]):
        raise ApiError(401, 'SESSION_REQUIRED')
    return owners[0]

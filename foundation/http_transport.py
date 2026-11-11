"""Bounded shared HTTP transport: no proxy, redirects or service-private data."""
import asyncio
import time
from dataclasses import dataclass
from typing import Mapping, Protocol
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from domain.errors import DomainError

@dataclass(frozen=True)
class HttpResult:
    status: int
    headers: Mapping[str, str]
    body: bytes


class HttpTransport(Protocol):
    async def post(self, url: str, headers: Mapping[str, str], body: bytes, timeout: float) -> HttpResult: ...


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _post(url: str, headers: Mapping[str, str], body: bytes | None, timeout: float, method='POST') -> HttpResult:
    deadline = time.monotonic() + timeout
    request = Request(url, data=body, headers=dict(headers), method=method)
    try:
        response = build_opener(ProxyHandler({}), NoRedirect()).open(request, timeout=timeout)
    except HTTPError as exc:
        response = exc
    with response:
        chunks, size = [], 0
        while True:
            if time.monotonic() >= deadline:
                raise TimeoutError
            chunk = response.read1(65536)
            if not chunk:
                break
            size += len(chunk)
            if size > 1_048_576:
                raise DomainError('CATALOG_RESPONSE_INVALID')
            chunks.append(chunk)
        return HttpResult(response.status, {k.lower(): v for k, v in response.headers.items()}, b''.join(chunks))


class UrllibTransport:
    async def post(self, url: str, headers: Mapping[str, str], body: bytes, timeout: float) -> HttpResult:
        return await asyncio.to_thread(_post, url, headers, body, timeout)

    async def request(self, method, url, headers, body, timeout):
        return await asyncio.to_thread(_post, url, headers, body, timeout, method)



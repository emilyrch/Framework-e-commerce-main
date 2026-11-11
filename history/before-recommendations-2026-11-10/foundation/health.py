import asyncio
import json
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from foundation.settings import Settings


def check_dependency(settings: Settings, url: str, token: str) -> str:
    request = Request(url + '/health/ready', headers={
        'Authorization': 'Bearer ' + token,
        'X-Store-Id': settings.config.store_id,
        'X-Config-Hash': settings.config.config_hash,
    })
    try:
        # No environment proxy or redirects carrying internal credentials.
        from urllib.request import HTTPRedirectHandler
        class NoRedirect(HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None
        with build_opener(ProxyHandler({}), NoRedirect()).open(request, timeout=1) as response:
            value = json.loads(response.read(16385))
            if value.get('store_id') != settings.config.store_id or value.get('config_hash') != settings.config.config_hash:
                return 'mismatch'
            return 'ok' if value.get('status') == 'ready' and value.get('scope') == 'foundation' else 'unavailable'
    except HTTPError as exc:
        exc.close()
        return 'mismatch' if exc.code == 409 else 'unavailable'
    except (OSError, URLError, ValueError, AttributeError):
        return 'unavailable'


async def readiness(settings: Settings, repository, catalog=None, reviews=None, worker=None):
    checks = {'configuration': 'ok', 'manifest_schema': 'ok'}
    if repository:
        checks['storage_schema_and_access'] = 'ok' if await asyncio.to_thread(repository.ready) else 'unavailable'
    if settings.service == 'orders':
        # Report only implemented backend capabilities; browser session is not certified.
        checks['review_repository'] = checks['storage_schema_and_access']
        checks['review_service'] = 'ok' if reviews is not None else 'unavailable'
        checks['recovery_worker'] = 'ok' if worker is not None and worker.ready else 'unavailable'
    if settings.service == 'payments':
        checks['simulated_authorization'] = 'ok' if repository is not None else 'unavailable'
    if settings.service == 'catalog':
        checks['catalog_loaded'] = 'ok' if catalog is not None else 'unavailable'
    results = await asyncio.gather(*(asyncio.to_thread(check_dependency, settings, url, token) for _, url, token in settings.dependencies))
    for (name, _, _), result in zip(settings.dependencies, results):
        checks[name + '_identity'] = result
    good = all(value == 'ok' for value in checks.values())
    result = {'service': settings.service, 'status': 'ready' if good else 'not_ready',
                  'scope': 'foundation', 'store_id': settings.config.store_id,
                  'config_hash': settings.config.config_hash, 'checks': checks}
    if catalog is not None:
        result['catalog_revision'] = catalog.snapshot.catalog_revision
    return good, result

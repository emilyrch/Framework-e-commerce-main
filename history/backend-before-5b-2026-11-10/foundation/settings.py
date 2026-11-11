import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from foundation.config import ROOT, ConfigurationError, StoreConfig, load


@dataclass(frozen=True)
class Settings:
    service: str
    config: StoreConfig
    data_dir: Path
    incoming_credentials: tuple[tuple[str, str], ...]
    dependencies: tuple[tuple[str, str, str], ...]


def settings(service: str) -> Settings:
    config_path = os.environ.get('PRODUCT_CONFIG')
    if not config_path:
        raise ConfigurationError('PRODUCT_CONFIG is required')
    config = load(config_path)

    def token(name):
        value = os.environ.get(name, '')
        if len(value) < 32 or value.startswith('CHANGE_'):
            raise ConfigurationError(f'Missing or invalid secret: {name}')
        return value

    relations = {
        'catalog': ['WEB_CATALOG_TOKEN', 'ORDERS_CATALOG_TOKEN'],
        'orders': ['WEB_ORDERS_TOKEN'],
        'payments': ['WEB_PAYMENTS_TOKEN', 'ORDERS_PAYMENTS_TOKEN'],
    }
    deps = []
    if service == 'orders':
        for name in ['catalog']:
            url = os.environ.get(f'{name.upper()}_URL', f'http://127.0.0.1:{8001 if name == "catalog" else 8003}')
            parsed = urlparse(url)
            if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {'', '/'}:
                raise ConfigurationError('Invalid dependency URL')
            deps.append((name, url.rstrip('/'), token(f'ORDERS_{name.upper()}_TOKEN')))
    incoming = tuple(('web' if name.startswith('WEB_') else 'orders', token(name)) for name in relations[service])
    if len({value for _, value in incoming}) != len(incoming):
        raise ConfigurationError('Internal roles must use distinct credentials')
    return Settings(service, config,
                    Path(os.environ.get('DATA_DIR', ROOT / 'var' / config.store_id / service)),
                    incoming, tuple(deps))

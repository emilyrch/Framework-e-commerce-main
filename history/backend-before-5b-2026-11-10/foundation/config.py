"""Validação e identidade da configuração, compartilhadas entre serviços."""
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parents[1]


class ConfigurationError(ValueError):
    pass


def normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: normalize(value[k]) for k in sorted(value)}
    if isinstance(value, list):
        return [normalize(v) for v in value]
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def canonical(config: dict) -> str:
    value = normalize(config)
    value['features'] = sorted(value['features'])
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


@dataclass(frozen=True)
class StoreConfig:
    data: dict
    config_hash: str

    @property
    def store_id(self) -> str:
        return self.data['store_id']

    @property
    def domain(self) -> str:
        return self.data['domain']


def validate(data: Any) -> StoreConfig:
    def check_strings(value):
        if isinstance(value, str) and any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
            raise ConfigurationError('CONFIG_INVALID: control character or invalid Unicode')
        if isinstance(value, dict):
            for key, item in value.items():
                check_strings(key)
                check_strings(item)
        if isinstance(value, list):
            for item in value:
                check_strings(item)
    check_strings(data)
    schema = json.loads((ROOT / 'shared/config.schema.json').read_text(encoding='utf-8'))
    errors = sorted(Draft7Validator(schema).iter_errors(data), key=lambda e: str(list(e.path)))
    if errors:
        error = errors[0]
        path = '.'.join(map(str, error.path)) or 'manifest'
        raise ConfigurationError(f'CONFIG_INVALID: {path} ({error.validator})')
    source = data['catalog']['source']
    path = PurePosixPath(source)
    if '\\' in source or ':' in source or path.is_absolute() or '..' in path.parts or not source.startswith('demo-data/'):
        raise ConfigurationError('CONFIG_INVALID: catalog.source')
    windows = data['delivery'].get('schedule', {}).get('daily_windows', [])
    ids = [w['id'] for w in windows]
    if len(ids) != len(set(ids)):
        raise ConfigurationError('CONFIG_INVALID: duplicate window id')
    intervals = sorted((w['start'], w['end']) for w in windows)
    if any(a >= b for a, b in intervals) or any(intervals[i][0] < intervals[i-1][1] for i in range(1, len(intervals))):
        raise ConfigurationError('CONFIG_INVALID: overlapping or reversed windows')
    value = normalize(data)
    return StoreConfig(value, hashlib.sha256(canonical(value).encode('utf-8')).hexdigest())


def load(path: str | Path) -> StoreConfig:
    try:
        return validate(json.loads(Path(path).read_text(encoding='utf-8'), parse_constant=lambda _: (_ for _ in ()).throw(ValueError())))
    except (OSError, ValueError, RecursionError) as exc:
        if isinstance(exc, ConfigurationError):
            raise
        raise ConfigurationError('CONFIG_INVALID: unreadable or invalid JSON manifest') from None

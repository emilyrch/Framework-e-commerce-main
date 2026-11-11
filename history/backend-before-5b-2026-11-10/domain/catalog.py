import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Mapping

from pydantic import ValidationError

from domain.models import CatalogData, Product
from foundation.config import ROOT, ConfigurationError, StoreConfig, normalize


class CatalogLoadError(ConfigurationError):
    pass


def canonical_content(data: CatalogData) -> str:
    content = data.model_dump(mode='json')
    content['products'].sort(key=lambda p: p['id'])
    for product in content['products']:
        if 'combinations' in product:
            product['combinations'].sort(key=lambda c: c['id'])
        if 'food_information' in product:
            allergens = product['food_information']['allergens']
            if allergens['status'] == 'known':
                allergens['contains'].sort()
                allergens['may_contain'].sort()
    return json.dumps(normalize(content), sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


@dataclass(frozen=True)
class CatalogSnapshot:
    data: CatalogData
    catalog_revision: str = field(init=False)
    products: Mapping[str, Product] = field(init=False, repr=False)

    def __post_init__(self):
        object.__setattr__(self, 'catalog_revision', 'sha256:' + hashlib.sha256(canonical_content(self.data).encode('utf-8')).hexdigest())
        object.__setattr__(self, 'products', MappingProxyType({p.id: p for p in sorted(self.data.products, key=lambda p: p.id)}))


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON field')
        result[key] = value
    return result


class JsonCatalogLoader:
    def validate(self, raw: object, config: StoreConfig) -> CatalogSnapshot:
        try:
            data = CatalogData.model_validate(raw)
        except ValidationError as exc:
            error = exc.errors(include_input=False, include_context=False)[0]
            location = '.'.join(map(str, error['loc'])) or 'catalog'
            raise CatalogLoadError(f'CATALOG_INVALID: {location} ({error["type"]}): {error["msg"]}') from None
        if (data.store_id, data.domain, data.dataset_id, data.schema_version) != (
            config.store_id, config.domain, config.data['catalog']['dataset_id'], config.data['catalog']['schema_version']
        ):
            raise CatalogLoadError('CATALOG_INVALID: store/domain/dataset/schema mismatch')
        return CatalogSnapshot(data)

    def load(self, config: StoreConfig, data_root: Path = ROOT / 'demo-data') -> CatalogSnapshot:
        relative = PurePosixPath(config.data['catalog']['source']).relative_to('demo-data')
        filename = (data_root / relative).resolve()
        try:
            filename.relative_to(data_root.resolve())
            with filename.open('rb') as handle:
                body = handle.read(1_048_577)
            if len(body) > 1_048_576:
                raise ValueError('file too large')
            raw = json.loads(body.decode('utf-8'), object_pairs_hook=unique_keys,
                             parse_constant=lambda _: (_ for _ in ()).throw(ValueError('invalid constant')))
        except (OSError, ValueError, RecursionError):
            raise CatalogLoadError('CATALOG_INVALID: missing, inaccessible or malformed JSON (limit 1 MiB)') from None
        return self.validate(raw, config)

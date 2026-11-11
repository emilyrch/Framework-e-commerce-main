from pathlib import Path

from foundation.config import StoreConfig
from foundation.storage import PrivateRepository


class PaymentsRepository(PrivateRepository):
    def __init__(self, data_dir: Path, config: StoreConfig):
        super().__init__(data_dir / 'payments.sqlite', 'payments', config)

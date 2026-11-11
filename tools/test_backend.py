"""Runner explícito: validação completa exige loopback; offline não é aprovação HTTP."""
import argparse
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--offline', action='store_true', help='Somente componentes/SQLite; não valida HTTP, asyncio ou worker')
    args = parser.parse_args()
    if args.offline:
        names = ['tests.foundation.test_config', 'tests.foundation.test_storage', 'tests.foundation.test_launcher',
                 'tests.catalog.test_models', 'tests.catalog.test_components', 'tests.checkout.test_offline.OfflineBusinessTests',
                 'tests.checkout.test_payment_wire_offline.PaymentWireOfflineTests',
                 'tests.checkout.test_web_contracts.WebContractTests',
                 'tests.recommendations.test_domain']
        suite = unittest.defaultTestLoader.loadTestsFromNames(names)
        print('OFFLINE ONLY: real SQLite/components; inline async adapters. HTTP/worker NOT validated.', flush=True)
    else:
        probe = "import socket; socket.setdefaulttimeout(1); a,b=socket.socketpair(); a.close(); b.close()"
        try:
            result = subprocess.run([sys.executable, '-c', probe], cwd=ROOT, capture_output=True, timeout=3)
        except subprocess.TimeoutExpired:
            result = None
        if result is None or result.returncode != 0:
            print('Loopback unavailable. Full suite NOT executed. Run outside this restricted environment; --offline runs a limited subset.', file=sys.stderr)
            return 2
        suite = unittest.defaultTestLoader.discover(str(ROOT/'tests'), top_level_dir=str(ROOT))
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())

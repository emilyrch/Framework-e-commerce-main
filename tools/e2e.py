"""Real Next.js + three backend processes; exclusively temporary DBs/secrets/ports.

Requires a production frontend build and functional loopback. Does not install anything.
Does not replace visual/browser validation.
"""
import os
from pathlib import Path
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.lps import stop


def main():
    node = shutil.which('node')
    next_cli = ROOT/'apps/store-ropa/node_modules/next/dist/bin/next'
    if not node or not next_cli.is_file() or not (ROOT/'apps/store-ropa/.next/BUILD_ID').is_file():
        print('BLOCKED: Next.js and a production build are required. E2E not executed.')
        return 2
    try:
        probe = subprocess.run([sys.executable, '-c', 'import socket; socket.setdefaulttimeout(1); a,b=socket.socketpair(); a.close(); b.close()'], capture_output=True, timeout=3)
    except subprocess.TimeoutExpired:
        print('BLOCKED: loopback probe timed out. E2E not executed.')
        return 2
    if probe.returncode:
        print('BLOCKED: loopback unavailable. E2E not executed.')
        return 2
    opener = build_opener(ProxyHandler({}))
    with tempfile.TemporaryDirectory(prefix='lps-e2e-') as directory:
        directory = Path(directory)
        for variant in ['clothing', 'food']:
            children, logs = {}, []
            def port():
                with socket.socket() as sock:
                    sock.bind(('127.0.0.1', 0)); return sock.getsockname()[1]
            ports = {service:port() for service in ['catalog', 'orders', 'payments', 'recommendations', 'web']}
            env = os.environ.copy()
            for key in ['WEB_CATALOG_TOKEN', 'WEB_ORDERS_TOKEN', 'WEB_PAYMENTS_TOKEN', 'ORDERS_CATALOG_TOKEN', 'ORDERS_PAYMENTS_TOKEN', 'SESSION_SECRET','RECOMMENDATIONS_CATALOG_TOKEN','WEB_RECOMMENDATIONS_TOKEN']:
                env[key] = secrets.token_hex(32)
            env.update(PRODUCT_CONFIG=str(ROOT/f'configurations/{variant}.json'), LPS_ROOT=str(ROOT),
                       CATALOG_DATA_ROOT=str(ROOT/'demo-data'), NEXT_TELEMETRY_DISABLED='1', PYTHONUTF8='1',
                       WEB_ORIGIN=f'http://127.0.0.1:{ports["web"]}', TEST_CLOCK='2030-01-07T08:00:00-03:00', TEST_WORKER='1')
            for service in ['catalog', 'orders', 'payments','recommendations']: env[service.upper()+'_URL'] = f'http://127.0.0.1:{ports[service]}'
            def start(service):
                local = env.copy(); local['DATA_DIR'] = str(directory/variant/service)
                permissions = {'catalog': ['WEB_CATALOG_TOKEN','ORDERS_CATALOG_TOKEN','RECOMMENDATIONS_CATALOG_TOKEN'],
                    'orders': ['WEB_ORDERS_TOKEN','ORDERS_CATALOG_TOKEN','ORDERS_PAYMENTS_TOKEN'],
                    'payments': ['WEB_PAYMENTS_TOKEN','ORDERS_PAYMENTS_TOKEN'],
                    'recommendations':['WEB_RECOMMENDATIONS_TOKEN','RECOMMENDATIONS_CATALOG_TOKEN'],
                    'web': ['WEB_CATALOG_TOKEN','WEB_ORDERS_TOKEN','WEB_PAYMENTS_TOKEN','WEB_RECOMMENDATIONS_TOKEN','SESSION_SECRET']}
                for key in ['WEB_CATALOG_TOKEN','WEB_ORDERS_TOKEN','WEB_PAYMENTS_TOKEN','ORDERS_CATALOG_TOKEN','ORDERS_PAYMENTS_TOKEN','SESSION_SECRET','WEB_RECOMMENDATIONS_TOKEN','RECOMMENDATIONS_CATALOG_TOKEN']:
                    if key not in permissions[service]:local.pop(key,None)
                if service!='catalog':local.pop('CATALOG_DATA_ROOT',None)
                if service == 'web':
                    command = [node, str(next_cli), 'start', '--hostname', '127.0.0.1', '--port', str(ports[service])]
                    cwd = ROOT/'apps/store-ropa'
                else:
                    target = ['tests.checkout.server:create_app', '--factory'] if service=='orders' else [f'services.{service}.app:app']
                    command = [sys.executable, '-m', 'uvicorn', *target, '--host', '127.0.0.1', '--port', str(ports[service])]
                    cwd = ROOT
                log = (directory/f'{variant}-{service}-{len(logs)}.log').open('wb'); logs.append(log)
                children[service] = subprocess.Popen(command, cwd=cwd, env=local, stdout=log, stderr=log,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name=='nt' else 0)
                for _ in range(100):
                    if children[service].poll() is not None: raise RuntimeError('Test process failed: '+service)
                    try:
                        with opener.open(f'http://127.0.0.1:{ports[service]}/health/live', timeout=0.3) as response:
                            if response.status==200:return
                    except OSError:pass
                    time.sleep(0.05)
                raise RuntimeError('Test process not live: '+service)
            try:
                for service in ['catalog','payments','orders','recommendations','web']:start(service)
                smoke = env.copy(); smoke.update(SMOKE_ORIGIN=env['WEB_ORIGIN'], SMOKE_STATE=str(directory/f'{variant}-state.json'), SMOKE_FORBIDDEN_TOKEN=env['WEB_ORDERS_TOKEN'])
                for resume in ['0','1']:
                    if resume=='1':
                        for service in ['orders','payments']:stop(children.pop(service))
                        for service in ['payments','orders']:start(service)
                    smoke['SMOKE_RESUME']=resume
                    subprocess.run([node,'--experimental-strip-types','apps/store-ropa/scripts/smoke-e2e.ts'],cwd=ROOT,env=smoke,check=True,timeout=90)
                for service,table in [('orders','orders'),('payments','authorizations')]:
                    with sqlite3.connect(directory/variant/service/f'{service}.sqlite') as db:
                        if db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]!=1:raise AssertionError('Duplicate or missing '+table)
                print(variant+': private DB cardinality after restart passed')
            finally:
                for child in reversed(list(children.values())):stop(child)
                for log in logs:log.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

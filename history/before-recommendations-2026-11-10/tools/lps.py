"""Launcher local: somente roupas/alimentos, sem instalar ou alterar a máquina."""
import argparse
import os
import secrets
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from foundation.config import ConfigurationError, load

SECRET_NAMES = ['WEB_CATALOG_TOKEN', 'WEB_ORDERS_TOKEN', 'WEB_PAYMENTS_TOKEN',
                'ORDERS_CATALOG_TOKEN', 'ORDERS_PAYMENTS_TOKEN', 'SESSION_SECRET']


def prepare(variant):
    config = load(ROOT / 'configurations' / (variant + '.json'))
    directory = ROOT / '.local'
    directory.mkdir(exist_ok=True)
    filename = directory / (config.store_id + '.env')
    if not filename.exists():
        content = [f'PRODUCT_CONFIG=./configurations/{variant}.json', f'COMPOSE_PROJECT_NAME=lps-{config.store_id}']
        content.extend(f'{name}={secrets.token_hex(32)}' for name in SECRET_NAMES)
        try:
            with filename.open('x', encoding='utf-8', newline='\n') as handle:
                handle.write('\n'.join(content) + '\n')
            if os.name != 'nt':
                filename.chmod(0o600)
        except FileExistsError:
            pass
    values = {}
    for line in filename.read_text(encoding='utf-8').splitlines():
        if line and not line.startswith('#'):
            key, value = line.split('=', 1)
            values[key] = value
    if any(len(values.get(name, '')) < 32 for name in SECRET_NAMES):
        raise ConfigurationError('Invalid secrets file; existing values were not overwritten')
    if values.get('PRODUCT_CONFIG') != f'./configurations/{variant}.json' or values.get('COMPOSE_PROJECT_NAME') != f'lps-{config.store_id}':
        raise ConfigurationError('Secrets file belongs to another configuration')
    return config, filename, values


def environment(variant, service):
    config, _, values = prepare(variant)
    env = os.environ.copy()
    for name in SECRET_NAMES:
        env.pop(name, None)
    names = {
        'catalog': ['WEB_CATALOG_TOKEN', 'ORDERS_CATALOG_TOKEN'],
        'orders': ['WEB_ORDERS_TOKEN', 'ORDERS_CATALOG_TOKEN', 'ORDERS_PAYMENTS_TOKEN'],
        'payments': ['WEB_PAYMENTS_TOKEN', 'ORDERS_PAYMENTS_TOKEN'],
        'web': ['WEB_CATALOG_TOKEN', 'WEB_ORDERS_TOKEN', 'WEB_PAYMENTS_TOKEN', 'SESSION_SECRET'],
    }[service]
    env.update({name: values[name] for name in names})
    env.pop('CATALOG_DATA_ROOT', None)
    if service == 'catalog':
        env['CATALOG_DATA_ROOT'] = str(ROOT / 'demo-data')
    env.update(PRODUCT_CONFIG=str(ROOT / 'configurations' / (variant + '.json')), LPS_ROOT=str(ROOT),
               DATA_DIR=str(ROOT / 'var' / config.store_id / service),
               CATALOG_URL='http://127.0.0.1:8001', ORDERS_URL='http://127.0.0.1:8002', PAYMENTS_URL='http://127.0.0.1:8003',
               NEXT_TELEMETRY_DISABLED='1', PYTHONUTF8='1')
    return env


def command(service, mode='start'):
    if service == 'web':
        node = shutil.which('node')
        entrypoint = ROOT / 'apps/store-ropa/node_modules/next/dist/bin/next'
        if not node or not entrypoint.is_file():
            raise ConfigurationError('Frontend dependencies missing: run npm ci in apps/store-ropa')
        return [node, str(entrypoint), mode, '--hostname', '127.0.0.1', '--port', '3000'], ROOT / 'apps/store-ropa'
    return [sys.executable, '-m', 'uvicorn', f'services.{service}.app:app', '--host', '127.0.0.1',
            '--port', str({'catalog': 8001, 'orders': 8002, 'payments': 8003}[service]), '--workers', '1'], ROOT


def stop(process):
    if process.poll() is None:
        if os.name == 'nt':
            try:
                process.send_signal(signal.CTRL_BREAK_EVENT)
            except OSError:
                process.terminate()
        else:
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def main():
    parser = argparse.ArgumentParser(description='LPS foundation launcher')
    parser.add_argument('action', choices=['init', 'run', 'service', 'build-web'])
    parser.add_argument('variant', choices=['clothing', 'food'])
    parser.add_argument('--service', choices=['catalog', 'orders', 'payments', 'web'])
    parser.add_argument('--dev', action='store_true')
    args = parser.parse_args()
    try:
        config, filename, _ = prepare(args.variant)
        if args.action == 'init':
            print(f'{config.store_id}: secrets preserved/generated in {filename.relative_to(ROOT)} (values hidden)')
            return
        if args.action == 'build-web':
            node = shutil.which('node')
            if not node:
                raise ConfigurationError('Node.js is required')
            result = subprocess.run([node, 'node_modules/next/dist/bin/next', 'build'], cwd=ROOT/'apps/store-ropa', env=environment(args.variant,'web'))
            raise SystemExit(result.returncode)
        services = ['catalog', 'payments', 'orders', 'web'] if args.action == 'run' else [args.service]
        if None in services:
            raise ConfigurationError('--service is required')
        # Preflight all commands before starting any child.
        commands = [(service, *command(service, 'dev' if args.dev else 'start')) for service in services]
        children = []
        try:
            for service, cmd, cwd in commands:
                children.append(subprocess.Popen(cmd, cwd=cwd, env=environment(args.variant, service),
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0))
            print(f'{config.store_id}: foundation processes started; Ctrl+C to stop (data preserved)')
            while all(child.poll() is None for child in children):
                time.sleep(0.3)
            failed = next(child for child in children if child.poll() is not None)
            raise SystemExit(failed.returncode or 1)
        except KeyboardInterrupt:
            pass
        finally:
            for child in reversed(children):
                stop(child)
    except ConfigurationError as exc:
        parser.exit(2, str(exc) + '\n')


if __name__ == '__main__':
    main()

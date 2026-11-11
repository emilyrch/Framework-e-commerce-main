"""Single validation entry point. Never installs dependencies or changes demo data.

Exit 0: all selected checks passed; 1: failure; 2: incomplete/blocked.
The report is local and ignored by version control. No credentials are collected.
"""
import compileall
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import shutil
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    checks = []

    def record(name, status, detail, **extra):
        checks.append({'name': name, 'status': status, 'detail': detail, **extra})
        print(f'[{status.upper()}] {name}: {detail}', flush=True)

    def run(name, command, timeout=180, blocked_codes=(), env=None, working_dir=ROOT):
        try:
            result = subprocess.run(command, cwd=working_dir, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
            status = 'passed' if result.returncode == 0 else 'blocked' if result.returncode in blocked_codes else 'failed'
            record(name, status, 'exit '+str(result.returncode), command=command, output=(result.stdout+result.stderr)[-6000:])
        except subprocess.TimeoutExpired:
            record(name, 'failed', 'Deadline exceeded; check was not approved')

    run('backend_offline', [sys.executable, 'tools/test_backend.py', '--offline'])
    run('backend_http_async_worker', [sys.executable, 'tools/test_backend.py'], blocked_codes=(2,))
    node = shutil.which('node')
    if node:
        run('configuration_vectors', [node, '--experimental-strip-types', 'apps/store-ropa/scripts/check-config.ts'])
        run('web_boundary', [node, '--experimental-strip-types', '--test', 'apps/store-ropa/scripts/test-web.ts'])
    else:
        record('configuration_vectors', 'blocked', 'Node unavailable')
        record('web_boundary', 'blocked', 'Node unavailable')
    for name, executable, arguments in [
        ('frontend_typecheck', 'typescript/bin/tsc', ['--noEmit', '--project', 'apps/store-ropa/tsconfig.json']),
        ('frontend_lint', 'eslint/bin/eslint.js', ['apps/store-ropa', '--config', 'apps/store-ropa/eslint.config.mjs', '--max-warnings', '0']),
        ('frontend_build', 'next/dist/bin/next', ['build', 'apps/store-ropa']),
    ]:
        entry = ROOT/'apps/store-ropa/node_modules'/executable
        if not node or not entry.is_file():
            record(name, 'blocked', 'Lockfile dependencies unavailable; no installation attempted')
        elif name == 'frontend_build':
            import os
            build_env = os.environ.copy()
            build_env.update(PRODUCT_CONFIG=str(ROOT/'configurations/clothing.json'), LPS_ROOT=str(ROOT), NEXT_TELEMETRY_DISABLED='1')
            for key in ['WEB_CATALOG_TOKEN','WEB_ORDERS_TOKEN','WEB_PAYMENTS_TOKEN','WEB_RECOMMENDATIONS_TOKEN','SESSION_SECRET']:
                build_env[key] = secrets.token_hex(32)
            run(name, [node, str(entry), *arguments], timeout=300, env=build_env)
        elif name == 'frontend_lint':
            run(name,[node,str(entry),'.','--max-warnings','0'],working_dir=ROOT/'apps/store-ropa')
        else:
            run(name, [node, str(entry), *arguments])
    run('next_backend_e2e', [sys.executable, 'tools/e2e.py'], timeout=300, blocked_codes=(2,))
    good = all(compileall.compile_dir(str(ROOT/folder), quiet=2) for folder in ['foundation', 'domain', 'services', 'tools', 'tests'])
    record('python_syntax', 'passed' if good else 'failed', 'compileall')
    installed, mismatches = {}, []
    for line in (ROOT/'requirements.txt').read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.startswith('#'): continue
        name, expected = line.split('==')
        try: installed[name] = version(name)
        except PackageNotFoundError: installed[name] = None
        if installed[name] != expected: mismatches.append(name)
    record('python_pinned_versions', 'passed' if not mismatches else 'failed', ', '.join(mismatches) or 'Installed versions match requirements.txt', installed=installed)
    run('python_environment_consistency', [sys.executable, '-m', 'pip', 'check'], blocked_codes=(1,))
    record('clean_python_install', 'blocked', 'Requires independent installation from package index; not verified by installed-version comparison')
    docker = shutil.which('docker')
    record('compose_containers', 'blocked', 'Docker unavailable' if not docker else 'Run the documented isolated Compose validation; YAML inspection is not container validation')
    record('browser_e2e_visual', 'blocked', 'Requires running Next.js and a browser; unit/DTO tests do not prove rendering or E2E')
    report = {'generated_at': datetime.now(timezone.utc).isoformat(), 'release_ready': all(c['status']=='passed' for c in checks), 'checks': checks}
    target = ROOT/'.local/validation-latest.json'
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Report: .local/validation-latest.json (contains no collected credentials)', flush=True)
    return 1 if any(c['status']=='failed' for c in checks) else 2 if not report['release_ready'] else 0


if __name__ == '__main__':
    raise SystemExit(main())

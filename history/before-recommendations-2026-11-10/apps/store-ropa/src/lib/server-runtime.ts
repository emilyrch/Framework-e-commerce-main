import path from 'node:path';
import http from 'node:http';
import https from 'node:https';
import { loadManifest } from './store-config.ts';

function buildRuntime() {
  const filename = process.env.PRODUCT_CONFIG;
  if (!filename) throw new Error('PRODUCT_CONFIG is required');
  const identity = loadManifest(filename, process.env.LPS_ROOT ?? path.resolve(process.cwd(), '../..'));
  const secret = process.env.SESSION_SECRET;
  if (!secret || secret.length < 32 || secret.startsWith('CHANGE_')) throw new Error('Missing session secret');
  const origin = new URL(process.env.WEB_ORIGIN ?? 'http://127.0.0.1:3000');
  if (origin.origin !== (process.env.WEB_ORIGIN ?? 'http://127.0.0.1:3000') || origin.username || origin.password || !['http:', 'https:'].includes(origin.protocol) || (origin.protocol === 'http:' && !['127.0.0.1','localhost','[::1]'].includes(origin.hostname))) throw new Error('Invalid web origin');
  const dependencies = ['catalog', 'orders', 'payments'].map((service, index) => {
    const token = process.env[`WEB_${service.toUpperCase()}_TOKEN`];
    if (!token || token.length < 32 || token.startsWith('CHANGE_')) throw new Error('Missing internal credential');
    const url = new URL(process.env[`${service.toUpperCase()}_URL`] ?? `http://127.0.0.1:${8001+index}`);
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash || url.pathname !== '/') {
      throw new Error('Invalid dependency URL');
    }
    return { service, token, url: url.origin };
  });
  return { ...identity, dependencies };
}

let currentRuntime: ReturnType<typeof buildRuntime> | undefined;
export function runtime() {
  currentRuntime ??= buildRuntime();
  return currentRuntime;
}

function probe(url: string, headers: Record<string,string>, storeId: string, hash: string): Promise<string> {
  return new Promise(resolve => {
    let finished = false;
    const request = (url.startsWith('https:') ? https : http).get(url, { headers }, response => {
      if (response.statusCode !== 200) {
        finish(response.statusCode === 409 ? 'mismatch' : 'unavailable');
        response.destroy();
        return;
      }
      const chunks: Buffer[] = [];
      let size = 0;
      response.on('data', (chunk: Buffer) => {
        size += chunk.length;
        if (size > 16384) { finish('unavailable'); response.destroy(); }
        else chunks.push(chunk);
      });
      response.on('error', () => finish('unavailable'));
      response.on('end', () => {
        try {
          const body = JSON.parse(Buffer.concat(chunks).toString('utf8'));
          finish(body.store_id !== storeId || body.config_hash !== hash ? 'mismatch'
            : body.status === 'ready' && body.scope === 'foundation' ? 'ok' : 'unavailable');
        } catch { finish('unavailable'); }
      });
    });
    const deadline = setTimeout(() => { finish('unavailable'); request.destroy(); }, 1000);
    function finish(status: string) {
      if (!finished) { finished = true; clearTimeout(deadline); resolve(status); }
    }
    request.on('error', () => finish('unavailable'));
  });
}

export async function webReadiness() {
  const current = runtime();
  const checks: Record<string,string> = { configuration: 'ok', session_signing: 'ok' };
  await Promise.all(current.dependencies.map(async ({service, token, url}) => {
    checks[service] = await probe(`${url}/health/ready`, {
      Authorization: `Bearer ${token}`, 'X-Store-Id': current.config.store_id, 'X-Config-Hash': current.config_hash,
    }, current.config.store_id, current.config_hash);
  }));
  const ready = Object.values(checks).every(v => v === 'ok');
  return { ready, body: { service: 'web', status: ready ? 'ready' : 'not_ready', scope: 'foundation',
    store_id: current.config.store_id, config_hash: current.config_hash, checks } };
}

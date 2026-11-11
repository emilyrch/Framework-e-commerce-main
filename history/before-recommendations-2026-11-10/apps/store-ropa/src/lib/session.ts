import { createHash, createHmac, randomBytes, timingSafeEqual } from 'node:crypto';

export const SESSION_SECONDS = 30 * 86400;
type Identity = { store_id: string; sid: string; issued_at: number; expires_at: number };
function sign(value: string, secret: string) { return createHmac('sha256', secret).update(value).digest('base64url'); }
export function issueSession(store: string, secret: string, now = Math.floor(Date.now()/1000)) {
  const identity: Identity = {store_id: store, sid: randomBytes(32).toString('hex'), issued_at: now, expires_at: now+SESSION_SECONDS};
  const payload = Buffer.from(JSON.stringify(identity)).toString('base64url');
  return {token: payload+'.'+sign(payload, secret), identity};
}
export function verifySession(token: string | undefined, store: string, secret: string, now = Math.floor(Date.now()/1000)): Identity | null {
  try {
    if (!token || token.length > 1024) return null;
    const parts = token.split('.');
    if (parts.length !== 2) return null;
    const expected = Buffer.from(sign(parts[0], secret)); const supplied = Buffer.from(parts[1]);
    if (expected.length !== supplied.length || !timingSafeEqual(expected, supplied)) return null;
    const value = JSON.parse(Buffer.from(parts[0], 'base64url').toString()) as Identity;
    if (value.store_id !== store || !/^[a-f0-9]{64}$/.test(value.sid) || !Number.isSafeInteger(value.issued_at) || !Number.isSafeInteger(value.expires_at) || value.issued_at > now || value.expires_at <= now || value.expires_at-value.issued_at !== SESSION_SECONDS) return null;
    return value;
  } catch { return null; }
}
export function sessionOwner(value: Identity) { return createHash('sha256').update(value.store_id+':'+value.sid).digest('hex'); }
export function sessionContext(value: Identity, secret: string) { return sign('ui-context:'+value.store_id+':'+value.sid, secret); }

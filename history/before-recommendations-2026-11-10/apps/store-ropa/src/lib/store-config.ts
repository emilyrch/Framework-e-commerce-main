import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import path from 'node:path';

type Json = null | boolean | number | string | Json[] | { [key: string]: Json };
type Schema = { [key: string]: unknown };
export type StoreConfig = {
  schema_version: number; store_id: string; display_name: string;
  domain: 'clothing' | 'food'; currency: 'BRL'; timezone: 'America/Sao_Paulo';
  features: string[];
  catalog: { dataset_id: string; schema_version: number; source: string };
  delivery: { policy: 'scheduled' | 'unscheduled'; shipping_cents: number;
    schedule?: { policy_id: string; days_ahead: number;
      daily_windows: { id: string; start: string; end: string; enabled: boolean }[] } };
  payment: { provider: 'simulated_pix'; discount_cents: number };
};

// Only the keywords used by our closed, committed schema. Not a general Draft-7 engine.
function matches(value: unknown, schema: Schema): boolean {
  if (schema.type) {
    const type = schema.type;
    const valid = type === 'object' ? typeof value === 'object' && value !== null && !Array.isArray(value)
      : type === 'array' ? Array.isArray(value)
      : type === 'integer' ? typeof value === 'number' && Number.isSafeInteger(value)
      : typeof value === type;
    if (!valid) return false;
  }
  if ('const' in schema && value !== schema.const) return false;
  if (schema.enum && !(schema.enum as unknown[]).includes(value)) return false;
  if (typeof value === 'string') {
    const length = [...value].length; // Python/JSON Schema count Unicode code points.
    if (schema.minLength !== undefined && length < Number(schema.minLength)) return false;
    if (schema.maxLength !== undefined && length > Number(schema.maxLength)) return false;
    if (schema.pattern && !new RegExp(String(schema.pattern)).test(value)) return false;
  }
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return false;
    if (schema.minimum !== undefined && value < Number(schema.minimum)) return false;
    if (schema.maximum !== undefined && value > Number(schema.maximum)) return false;
  }
  if (Array.isArray(value)) {
    if (schema.minItems !== undefined && value.length < Number(schema.minItems)) return false;
    if (schema.maxItems !== undefined && value.length > Number(schema.maxItems)) return false;
    if (schema.uniqueItems && new Set(value.map(v => JSON.stringify(v))).size !== value.length) return false;
    if (schema.items && !value.every(v => matches(v, schema.items as Schema))) return false;
  }
  if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
    const object = value as Record<string, unknown>;
    const properties = (schema.properties ?? {}) as Record<string, Schema>;
    if (schema.required && !(schema.required as string[]).every(k => Object.hasOwn(object, k))) return false;
    if (schema.additionalProperties === false && Object.keys(object).some(k => !Object.hasOwn(properties, k))) return false;
    if (!Object.entries(properties).every(([key, rule]) => !Object.hasOwn(object, key) || matches(object[key], rule))) return false;
  }
  if (schema.allOf && !(schema.allOf as Schema[]).every(s => matches(value, s))) return false;
  if (schema.if && matches(value, schema.if as Schema) && schema.then && !matches(value, schema.then as Schema)) return false;
  return true;
}

function normalize(value: Json): Json {
  if (Array.isArray(value)) return value.map(normalize);
  if (value !== null && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map(k => [k, normalize(value[k])]));
  }
  return value;
}

export function canonical(config: StoreConfig): string {
  return JSON.stringify(normalize({ ...config, features: [...config.features].sort() } as unknown as Json));
}

export function validateManifest(input: unknown, root: string) {
  function checkStrings(value: unknown): void {
    if (typeof value === 'string' && [...value].some(c => c.codePointAt(0)! < 32 || (c.codePointAt(0)! >= 0xD800 && c.codePointAt(0)! <= 0xDFFF))) {
      throw new Error('CONFIG_INVALID: control character or invalid Unicode');
    }
    if (Array.isArray(value)) value.forEach(checkStrings);
    else if (value !== null && typeof value === 'object') Object.entries(value).forEach(([k,v]) => { checkStrings(k); checkStrings(v); });
  }
  checkStrings(input);
  const schema = JSON.parse(readFileSync(path.join(root, 'shared/config.schema.json'), 'utf8')) as Schema;
  if (!matches(input, schema)) throw new Error('CONFIG_INVALID: manifest schema');
  const config = input as StoreConfig;
  const source = config.catalog.source;
  if (source.includes('\\') || source.includes(':') || source.split('/').includes('..') || !source.startsWith('demo-data/')) {
    throw new Error('CONFIG_INVALID: catalog.source');
  }
  const windows = config.delivery.schedule?.daily_windows ?? [];
  if (new Set(windows.map(w => w.id)).size !== windows.length) throw new Error('CONFIG_INVALID: duplicate window id');
  const intervals = [...windows].sort((a,b) => a.start.localeCompare(b.start));
  if (intervals.some((w,i) => w.start >= w.end || (i > 0 && w.start < intervals[i-1].end))) {
    throw new Error('CONFIG_INVALID: overlapping or reversed windows');
  }
  return { config, config_hash: createHash('sha256').update(canonical(config), 'utf8').digest('hex') };
}

export function loadManifest(filename: string, root: string) {
  try { return validateManifest(JSON.parse(readFileSync(filename, 'utf8')), root); }
  catch { throw new Error('CONFIG_INVALID: unreadable or invalid manifest'); }
}

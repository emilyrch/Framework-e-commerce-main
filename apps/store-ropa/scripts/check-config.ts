import { readFileSync } from 'node:fs';
import path from 'node:path';
import { validateManifest } from '../src/lib/store-config.ts';

const root = path.resolve(import.meta.dirname, '../../..');
const vectors = JSON.parse(readFileSync(path.join(root, 'shared/config-vectors.json'), 'utf8')) as {
  name: string; valid: boolean; config: unknown; config_hash?: string;
}[];
for (const vector of vectors) {
  let result;
  try { result = validateManifest(vector.config, root); }
  catch { if (vector.valid) throw new Error(`Unexpected invalid vector: ${vector.name}`); }
  if (result && (!vector.valid || result.config_hash !== vector.config_hash)) throw new Error(`Vector mismatch: ${vector.name}`);
}
console.log(`TypeScript: ${vectors.length} configuration vectors OK`);

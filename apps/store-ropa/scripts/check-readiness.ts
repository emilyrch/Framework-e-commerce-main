import { webReadiness } from '../src/lib/server-runtime.ts';

const result = await webReadiness();
console.log(JSON.stringify(result));

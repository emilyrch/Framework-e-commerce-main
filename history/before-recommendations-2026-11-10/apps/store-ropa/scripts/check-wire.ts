import {readFileSync} from 'node:fs';
import {validWireResponse} from '../src/lib/wire-response.ts';
const cases=JSON.parse(readFileSync(0,'utf8')) as {route:string;body:unknown;store:string;domain:'clothing'|'food'}[];
for(const sample of cases)if(!validWireResponse(sample.route,sample.body,sample.store,sample.domain))throw new Error('Incompatible backend response: '+sample.domain+'/'+sample.route);
console.log(`${cases.length} real Python DTOs accepted by web boundary (offline, not HTTP)`);

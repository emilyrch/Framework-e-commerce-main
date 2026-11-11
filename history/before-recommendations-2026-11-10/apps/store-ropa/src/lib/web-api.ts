import { runtime as getRuntime } from './server-runtime.ts';
import { randomUUID } from 'node:crypto';
import { validWireResponse } from './wire-response.ts';
import { issueSession, verifySession, sessionContext, sessionOwner, SESSION_SECONDS } from './session.ts';

const json = (body:unknown,status=200) => Response.json(body,{status,headers:{'Cache-Control':'no-store'}});
const errorBody = (code:string,status:number,fields:unknown[]=[],details?:{order_id:string}) => ({error:{code,message:'Requisição indisponível ou inválida',fields,retryable:status===503,...(details?{details}:{})},request_id:randomUUID()});
const error = (code:string,status:number) => json(errorBody(code,status),status);

export function createWebApi(runtimeProvider = getRuntime, fetcher: typeof fetch = fetch) {
return async function handle(request:Request) {
  if(!['GET','POST'].includes(request.method)) return error('METHOD_NOT_ALLOWED',405);
  let path:string[];
  try { path = new URL(request.url).pathname.slice('/api/v1/'.length).split('/').map(decodeURIComponent); } catch {return error('RESOURCE_NOT_FOUND',404);}
  const route = path.join('/');
  const current = runtimeProvider(); const {config,config_hash} = current;
  const secret = process.env.SESSION_SECRET;
  if (!secret || secret.length<32) return error('SESSION_UNAVAILABLE',503);
  const cookieName = 'lps_session_'+config.store_id;
  const cookies=(request.headers.get('cookie')??'').split(';').map(c=>c.trim()).filter(c=>c.startsWith(cookieName+'='));
  const identity = verifySession(cookies.length===1?cookies[0].slice(cookieName.length+1):undefined,config.store_id,secret);
  const mutation = request.method==='POST';
  let body:unknown;
  if (mutation) {
    const origin = process.env.WEB_ORIGIN ?? 'http://127.0.0.1:3000';
    if (request.headers.get('origin') !== origin) return error('ORIGIN_FORBIDDEN',403);
    if (request.headers.get('content-type')?.split(';')[0].trim().toLowerCase()!=='application/json') return error('CONTENT_TYPE_INVALID',415);
    const reader = request.body?.getReader(); const chunks:Uint8Array[]=[]; let size=0;
    try {
      if (reader) while (true) { const part=await reader.read(); if(part.done) break; size+=part.value.length; if(size>65536){await reader.cancel();return error('BODY_TOO_LARGE',413);} chunks.push(part.value); }
      body=JSON.parse(Buffer.concat(chunks).toString('utf8'));
    } catch {return error('INPUT_INVALID',422);}
  }
  if (route==='session' && mutation) {
    if (!body || typeof body!=='object' || Array.isArray(body) || Object.keys(body).length) return error('INPUT_INVALID',422);
    const issued=identity ? null:issueSession(config.store_id,secret); const value=identity??issued!.identity;
    const response=json({store_id:config.store_id,session_available:true,session_context_id:sessionContext(value,secret),expires_at:new Date(value.expires_at*1000).toISOString()});
    if(issued) response.headers.set('Set-Cookie',`${cookieName}=${issued.token}; HttpOnly; SameSite=Lax; Path=/; Max-Age=${SESSION_SECONDS}${new URL(process.env.WEB_ORIGIN??'http://127.0.0.1:3000').protocol==='https:'?'; Secure':''}`);
    return response;
  }
  if(route==='store' && !mutation) return json({schema_version:1,store_id:config.store_id,display_name:config.display_name,domain:config.domain,config_hash,currency:config.currency,timezone:config.timezone,features:config.features,payment:{method:'simulated_pix',simulated:true},delivery:{scheduled:config.domain==='food',shipping_cents:0},limits:{max_lines:50,min_quantity:1,max_quantity:100}});
  const catalog = !mutation && (route==='products' || (path.length===2 && path[0]==='products' && path[1].length<=80 && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(path[1])));
  const slots = !mutation && route==='delivery-slots';
  const privateRead = !mutation && path.length===2 && ['orders','order-attempts'].includes(path[0]) && /^[a-f0-9-]{36}$/i.test(path[1]);
  const privateWrite = mutation && ['reviews','orders'].includes(route);
  if(!catalog && !slots && !privateRead && !privateWrite) return error('RESOURCE_NOT_FOUND',404);
  if((privateRead||privateWrite) && !identity) return error('SESSION_REQUIRED',401);
  const dependency=current.dependencies.find(d=>d.service===(catalog?'catalog':'orders'))!;
  const headers:Record<string,string>={Authorization:'Bearer '+dependency.token,'X-Store-Id':config.store_id,'X-Config-Hash':config_hash};
  if(identity && (privateRead||privateWrite)) headers['X-Session-Owner']=sessionOwner(identity);
  if(mutation) headers['Content-Type']='application/json';
  if(route==='orders' && mutation) {
    const key=request.headers.get('idempotency-key');
    if(!key) return error('IDEMPOTENCY_KEY_REQUIRED',400);
    if(!/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i.test(key)) return error('IDEMPOTENCY_KEY_INVALID',400);
    headers['Idempotency-Key']=key;
  }
  try {
    const upstream=await fetcher(dependency.url+'/internal/v1/'+path.map(encodeURIComponent).join('/'),{method:request.method,headers,body:mutation?JSON.stringify(body):undefined,cache:'no-store',redirect:'manual',signal:AbortSignal.timeout(route==='orders'&&mutation?11000:6000)});
    if(upstream.headers.get('x-store-id')!==config.store_id || upstream.headers.get('x-config-hash')!==config_hash) return error('DEPENDENCY_IDENTITY_INVALID',503);
    if(!upstream.headers.get('content-type')?.includes('application/json') || upstream.status>=300&&upstream.status<400) return error('DEPENDENCY_RESPONSE_INVALID',503);
    const reader=upstream.body?.getReader(); const chunks:Uint8Array[]=[];let size=0;
    if(reader) while(true){const part=await reader.read();if(part.done)break;size+=part.value.length;if(size>1048576){await reader.cancel();return error('DEPENDENCY_RESPONSE_INVALID',503);}chunks.push(part.value);}
    const value=JSON.parse(Buffer.concat(chunks).toString('utf8'));
    if(upstream.ok && value.store_id!==config.store_id) return error('DEPENDENCY_IDENTITY_INVALID',503);
    if(upstream.ok && !validWireResponse(route,value,config.store_id,config.domain)) return error('DEPENDENCY_RESPONSE_INVALID',503);
    // Error bodies are a closed projection: never return arbitrary remote messages/details.
    const fields = Array.isArray(value.error?.fields)?value.error.fields.slice(0,20).filter((f:unknown)=>f!==null&&typeof f==='object'&&'path' in f&&'code' in f).map((f:{path:unknown;code:unknown})=>({path:typeof f.path==='string'?f.path.slice(0,200):'',code:typeof f.code==='string'?f.code.slice(0,80):'invalid'})):[];
    const code=typeof value.error?.code==='string'&&/^[A-Z_]{1,80}$/.test(value.error.code)?value.error.code:'DEPENDENCY_UNAVAILABLE';
    const orderId=value.error?.details?.order_id;
    const response=json(upstream.ok?value:errorBody(code,upstream.status,fields,typeof orderId==='string'&&/^[a-f0-9-]{36}$/i.test(orderId)?{order_id:orderId}:undefined),upstream.status);
    if(upstream.status===202) response.headers.set('Retry-After','2');
    return response;
  } catch {return error('DEPENDENCY_UNAVAILABLE',503);}
};
}


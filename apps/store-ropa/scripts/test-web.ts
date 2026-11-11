import test from 'node:test';
import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';
import {issueSession,verifySession,sessionContext,sessionOwner,SESSION_SECONDS} from '../src/lib/session.ts';
import {validCart,selection,cartFingerprint,reconcileConfirmedCart} from '../src/lib/shop-types.ts';
import {createWebApi} from '../src/lib/web-api.ts';
import {loadManifest} from '../src/lib/store-config.ts';
import {validWireResponse} from '../src/lib/wire-response.ts';
import path from 'node:path';
import {followPurchase} from '../src/lib/purchase-followup.ts';
import {sessionBootstrap} from '../src/lib/browser-session.ts';

test('parallel recommendation and checkout bootstrap share one session and failures can retry',async()=>{
  let requests=0;
  const bootstrap=sessionBootstrap(async()=>{requests++;return {session_context_id:'same-owner',expires_at:'2030-01-01T00:00:00Z'};});
  const [first,second]=await Promise.all([bootstrap(),bootstrap()]);
  assert.equal(requests,1);assert.equal(first,second);
  await bootstrap();assert.equal(requests,2);
  let fail=true;
  const retry=sessionBootstrap(async()=>{if(fail){fail=false;throw new Error('temporary');}return first;});
  await assert.rejects(retry());assert.equal(await retry(),first);
});

test('purchase follow-up reaches confirmation using reads and stops at a terminal state',async()=>{
  let reads=0;const received:string[]=[];
  const result=await followPurchase(async()=>({status:++reads===2?'confirmed':'payment_pending',recovery:{action:'wait',next_retry_at:null}}),p=>received.push(p.status),{active:()=>true,sleep:async()=>{}});
  assert.equal(result,'settled');assert.equal(reads,2);assert.deepEqual(received,['payment_pending','confirmed']);
});

test('purchase follow-up is bounded on outages and cancellation ignores a late response',async()=>{
  let reads=0;
  assert.equal(await followPurchase(async()=>{reads++;throw new Error('temporary');},()=>assert.fail('No result'),{active:()=>true,sleep:async()=>{},attempts:3}),'paused');
  assert.equal(reads,3);
  let active=true;
  assert.equal(await followPurchase(async()=>{active=false;return {status:'confirmed',recovery:{action:'none',next_retry_at:null}};},()=>assert.fail('Unmounted'),{active:()=>active,sleep:async()=>{}}),'cancelled');
});

const root=path.resolve(import.meta.dirname,'../../..');
const secret='test-only-'.repeat(8);process.env.SESSION_SECRET=secret;process.env.WEB_ORIGIN='http://127.0.0.1:3000';
const identity=loadManifest(path.join(root,'configurations/clothing.json'),root);
const provider=()=>({...identity,dependencies:[{service:'catalog',token:'catalog-test-token',url:'http://catalog:8001'},{service:'orders',token:'orders-test-token',url:'http://orders:8002'}]});
const request=(route:string,body?:unknown,cookie?:string,extra:Record<string,string>={})=>new Request('http://127.0.0.1:3000/api/v1/'+route,{method:body===undefined?'GET':'POST',headers:{...(body===undefined?{}:{Origin:'http://127.0.0.1:3000','Content-Type':'application/json'}),...(cookie?{Cookie:cookie}:{}),...extra},body:body===undefined?undefined:JSON.stringify(body)});
const upstream=(value:unknown,status=200)=>Response.json(value,{status,headers:{'X-Store-Id':identity.config.store_id,'X-Config-Hash':identity.config_hash}});

test('signed session: tampering, expiry, store isolation, stable owner/context',()=>{
  const {token,identity:value}=issueSession('roupas-demo',secret,100);
  assert.deepEqual(verifySession(token,'roupas-demo',secret,101),value);
  assert.equal(verifySession(token+'x','roupas-demo',secret,101),null);
  assert.equal(verifySession(token,'alimentos-demo',secret,101),null);
  assert.equal(verifySession(token,'roupas-demo','other-secret',101),null);
  assert.equal(verifySession(token,'roupas-demo',secret,100+SESSION_SECONDS),null);
  assert.equal(verifySession(token,'roupas-demo',secret,99),null);
  assert.match(sessionOwner(value),/^[a-f0-9]{64}$/);assert.notEqual(sessionContext(value,secret),sessionOwner(value));
});
test('cart limits and selection projection never send prices',()=>{
  const line={product_id:'camiseta',combination_id:'m',quantity:2,name:'Demo',label:'M',price_cents:1200};
  assert.ok(validCart([line]));assert.ok(!validCart([line,line]));
  for(const quantity of [true,'2',1.5,0,101]) assert.ok(!validCart([{...line,quantity}]));
  assert.deepEqual(selection(line),{product_id:'camiseta',combination_id:'m',quantity:2});
  assert.deepEqual(selection({...line,combination_id:undefined}),{product_id:'camiseta',quantity:2});
  assert.equal(cartFingerprint([line,{...line,combination_id:'g'}]),cartFingerprint([{...line,combination_id:'g'},line]));
});
test('session route sets HttpOnly cookie, reuses context, omits credentials',async()=>{
  const api=createWebApi(provider);const response=await api(request('session',{}));const body=await response.json();
  assert.equal(response.status,200);const cookie=response.headers.get('set-cookie')!;
  assert.match(cookie,/HttpOnly/);assert.match(cookie,/SameSite=Lax/);assert.ok(!JSON.stringify(body).includes('sid'));
  const again=await api(request('session',{},cookie.split(';')[0]));assert.equal((await again.json()).session_context_id,body.session_context_id);assert.equal(again.headers.get('set-cookie'),null);
  assert.equal(response.headers.get('cache-control'),'no-store');
});
test('Origin, JSON type, body limit, missing session and closed routes',async()=>{
  const api=createWebApi(provider);
  assert.equal((await api(request('session',{},undefined,{Origin:'http://evil.invalid'}))).status,403);
  assert.equal((await api(request('session',{},undefined,{'Content-Type':'application/json-invalid'}))).status,415);
  assert.equal((await api(request('session',{padding:'a'.repeat(65536)}))).status,413);
  assert.equal((await api(request('orders',{}))).status,401);
  assert.equal((await api(request('payments/by-order/'+randomUUID()))).status,404);
  assert.equal((await api(request('selections/resolve',{}))).status,404);
  const store=await (await api(request('store'))).json();assert.equal(store.domain,'clothing');assert.ok(!('catalog' in store));assert.ok(!JSON.stringify(store).includes('token'));
});
test('trusted headers recreated, key preserved, owner derived from cookie',async()=>{
  const {token,identity:value}=issueSession('roupas-demo',secret);const key=randomUUID();let calls=0;
  const api=createWebApi(provider,async(input,init)=>{calls++;assert.equal(String(input),'http://orders:8002/internal/v1/orders');const headers=new Headers(init?.headers);assert.equal(headers.get('authorization'),'Bearer orders-test-token');assert.equal(headers.get('x-session-owner'),sessionOwner(value));assert.equal(headers.get('idempotency-key'),key);assert.equal(init?.redirect,'manual');return upstream({store_id:'roupas-demo',attempt_id:randomUUID(),status:'validating',order_id:null,recovery:{action:'wait',next_retry_at:null}},202);});
  const response=await api(request('orders',{store_id:'roupas-demo',review_id:randomUUID()},'lps_session_roupas-demo='+token,{'X-Session-Owner':'forged',Authorization:'forged','X-Config-Hash':'forged','Idempotency-Key':key}));
  assert.equal(response.status,202);assert.equal(response.headers.get('retry-after'),'2');assert.equal(calls,1);
});
test('identity mismatch, redirects, malformed upstream and sanitized errors',async()=>{
  for(const fake of [()=>Response.json({store_id:'other'}),()=>new Response(null,{status:302}),()=>new Response('invalid',{headers:{'X-Store-Id':'roupas-demo','X-Config-Hash':identity.config_hash,'Content-Type':'application/json'}})]){
    const api=createWebApi(provider,async()=>fake());assert.equal((await api(request('products'))).status,503);
  }
  const api=createWebApi(provider,async()=>upstream({error:{code:'INPUT_INVALID',message:'private-path-token',fields:[],stack:'secret'}},422));
  const response=await api(request('products'));assert.equal(response.status,422);assert.ok(!JSON.stringify(await response.json()).includes('private-path-token'));
});
test('food projection and delivery route use orders without forwarding browser auth',async()=>{
  const food=loadManifest(path.join(root,'configurations/food.json'),root);
  const api=createWebApi(()=>({...food,dependencies:provider().dependencies}),async(input,init)=>{
    assert.equal(String(input),'http://orders:8002/internal/v1/delivery-slots');
    assert.equal(new Headers(init?.headers).get('authorization'),'Bearer orders-test-token');
    assert.equal(new Headers(init?.headers).get('x-session-owner'),null);
    return Response.json({store_id:'alimentos-demo',timezone:'America/Sao_Paulo',server_now:'2030-01-01T12:00:00Z',items:[]},{headers:{'X-Store-Id':'alimentos-demo','X-Config-Hash':food.config_hash}});
  });
  const store=await (await api(request('store'))).json();assert.equal(store.domain,'food');assert.equal(store.delivery.scheduled,true);
  assert.equal((await api(request('delivery-slots',undefined,undefined,{'X-Session-Owner':'forged'}))).status,200);
});
test('invalid cookie never authenticates, duplicate cookies and absent Origin rejected',async()=>{
  const api=createWebApi(provider);const {token}=issueSession('roupas-demo',secret);const command={store_id:'roupas-demo',review_id:randomUUID()};
  for(const cookie of ['lps_session_roupas-demo=invalid',`lps_session_roupas-demo=${token}; lps_session_roupas-demo=${token}`])assert.equal((await api(request('reviews',command,cookie))).status,401);
  assert.equal((await api(new Request('http://127.0.0.1:3000/api/v1/session',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'}))).status,403);
});
test('malformed success and inconsistent monetary/payment snapshots never reach browser',async()=>{
  const api=createWebApi(provider,async()=>upstream({store_id:'roupas-demo',status:'confirmed'}));
  assert.equal((await api(request('products'))).status,503);
  const value={store_id:'roupas-demo',order_id:randomUUID(),review_id:randomUUID(),status:'confirmed',recovery:{action:'none',next_retry_at:null},items:[{product_id:'camiseta',name:'Demo',quantity:2,unit_price_cents:8990,line_total_cents:17980}],totals:{currency:'BRL',subtotal_cents:17980,total_cents:17980,shipping_cents:0,discount_cents:0},payment:{method:'simulated_pix',simulated:true,status:'approved',payment_id:randomUUID(),amount_cents:17980}};
  assert.ok(validWireResponse('orders',value,'roupas-demo','clothing'));
  assert.ok(!validWireResponse('orders',{...value,payment:{...value.payment,payment_id:null}},'roupas-demo','clothing'));
  assert.ok(!validWireResponse('orders',{...value,totals:{...value.totals,total_cents:1}},'roupas-demo','clothing'));
});

test('recommendation profile uses the dedicated service and trusted session',async()=>{
  const {token,identity:value}=issueSession('roupas-demo',secret);
  const prefs={store_id:'roupas-demo',profile:{categories:[],colors:[],sizes:[],max_price_cents:null,use_history:true},options:{categories:['Camisetas e camisas'],colors:['preta'],sizes:['M']},history_count:0};
  const runtime=()=>({...provider(),dependencies:[...provider().dependencies,{service:'recommendations',token:'recommendations-test-token',url:'http://recommendations:8004'}]});
  let count=0;
  const api=createWebApi(runtime,async(input,init)=>{
    count++;assert.equal(String(input),'http://recommendations:8004/internal/v1/preferences');const headers=new Headers(init?.headers);
    assert.equal(headers.get('authorization'),'Bearer recommendations-test-token');assert.equal(headers.get('x-session-owner'),sessionOwner(value));return upstream(prefs);
  });
  assert.equal((await api(request('preferences'))).status,401);
  const response=await api(request('preferences',undefined,'lps_session_roupas-demo='+token,{'X-Session-Owner':'forged'}));
  assert.equal(response.status,200);assert.equal(count,1);assert.equal(response.headers.get('cache-control'),'no-store');
});

test('recommendation wire contracts reject remote images and malformed profiles',()=>{
  const product={id:'camiseta',name:'Demo',kind:'clothing',category:'Camisetas',price_cents:8990,image_url:'/demo/clothing/camiseta.png',reasons:['Da categoria que você escolheu']};
  const result={store_id:'roupas-demo',catalog_revision:'sha256:'+'a'.repeat(64),algorithm_version:'content-v1',mode:'personalized',items:[product]};
  assert.ok(validWireResponse('recommendations',result,'roupas-demo','clothing'));
  assert.ok(!validWireResponse('recommendations',{...result,items:[{...product,image_url:'https://external.invalid/photo.png'}]},'roupas-demo','clothing'));
  assert.ok(!validWireResponse('preferences',{store_id:'roupas-demo',profile:{},options:{},history_count:0},'roupas-demo','clothing'));
  assert.ok(!validWireResponse('recommendations',result,'alimentos-demo','food'));
});

test('recommendation mutations require origin and session and never expose candidates',async()=>{
  const api=createWebApi(provider);
  assert.equal((await api(request('recommendation-reset',{store_id:'roupas-demo'}))).status,401);
  assert.equal((await api(request('recommendation-events',{},undefined,{Origin:'http://evil.invalid'}))).status,403);
  assert.equal((await api(request('recommendation-candidates'))).status,404);
});

 test('cart survives uncertain payment and edits while confirmation is in flight',()=>{
  const cart=[{product_id:'demo',quantity:1,name:'Demo',label:'Unidade',price_cents:100}];
  const pending={key:randomUUID(),review_id:randomUUID(),context:'ctx',cart_fingerprint:cartFingerprint(cart)};
  const result={order_id:randomUUID(),status:'confirmed',recovery:{action:'none',next_retry_at:null}};
  for(const status of ['validating','accepted','payment_pending','payment_unknown','payment_conflict','rejected'])
    assert.equal(reconcileConfirmedCart(cart,pending,{...result,status}),cart);
  assert.equal(reconcileConfirmedCart(cart,pending,{...result,order_id:null}),cart);
  assert.deepEqual(reconcileConfirmedCart(cart,pending,result),[]);
  const edited=[{...cart[0],quantity:2}];
  assert.equal(reconcileConfirmedCart(edited,pending,result),edited);
 });

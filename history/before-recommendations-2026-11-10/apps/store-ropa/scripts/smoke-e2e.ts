// Real HTTP through Next.js. Invoked only by tools/e2e.py with temporary resources.
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync} from 'node:fs';
import {randomUUID} from 'node:crypto';
const origin=process.env.SMOKE_ORIGIN!,statePath=process.env.SMOKE_STATE!;
assert.ok(origin&&statePath,'Use tools/e2e.py; do not point this script at demo databases');
async function call(route:string,body?:unknown,cookie?:string,key?:string,expected=200){
  const response=await fetch(origin+'/api/v1/'+route,{method:body===undefined?'GET':'POST',headers:{...(body===undefined?{}:{Origin:origin,'Content-Type':'application/json'}),...(cookie?{Cookie:cookie}:{}),...(key?{'Idempotency-Key':key}:{})},body:body===undefined?undefined:JSON.stringify(body),redirect:'manual',signal:AbortSignal.timeout(15000)});
  const result=await response.json();assert.equal(response.status,expected,`${route}: ${response.status}`);
  assert.equal(response.headers.get('cache-control'),'no-store');return {response,result};
}
if(process.env.SMOKE_RESUME==='1'){
  const state=JSON.parse(readFileSync(statePath,'utf8'));
  const {result}=await call('orders/'+state.order_id,undefined,state.cookie);assert.equal(result.status,'confirmed');
  const replay=await call('orders',state.command,state.cookie,state.key);assert.equal(replay.result.order_id,state.order_id);
  console.log('Restart persistence and same-key replay: passed');
}else{
  const page=await fetch(origin,{signal:AbortSignal.timeout(15000)});assert.equal(page.status,200);const html=await page.text();
  const store=(await call('store')).result;assert.ok(html.includes(store.domain==='food'?'despensa':'essencial'));
  assert.ok(!html.includes(process.env.SMOKE_FORBIDDEN_TOKEN!));
  const session=await call('session',{});const cookie=session.response.headers.get('set-cookie')!.split(';')[0];assert.match(session.response.headers.get('set-cookie')!,/HttpOnly/);
  const products=(await call('products')).result.items;assert.ok(products.length>=6);
  const product=(await call('products/'+products[0].id)).result.product;
  const items=store.domain==='clothing'?product.combinations.filter((c:{enabled:boolean})=>c.enabled).slice(0,2).map((c:{id:string})=>({product_id:product.id,combination_id:c.id,quantity:2})):[{product_id:product.id,quantity:2},{product_id:products[1].id,quantity:1}];
  const delivery:Record<string,unknown>={address:{recipient:'Cliente de teste',street:'Rua Ficticia',number:'10',district:'Centro',city:'Sao Paulo',state:'SP',postal_code:'01001000'}};
  if(store.domain==='food'){const slots=(await call('delivery-slots')).result;assert.ok(slots.items.length);delivery.slot_id=slots.items[0].id;}
  else await call('delivery-slots',undefined,undefined,undefined,409);
  const reviewBody={store_id:store.store_id,items,delivery,payment_method:'simulated_pix'};
  await call('reviews',{...reviewBody,price_cents:1},cookie,undefined,422);
  const review=(await call('reviews',reviewBody,cookie,undefined,201)).result;
  assert.equal(review.totals.total_cents,review.items.reduce((sum:number,l:{line_total_cents:number})=>sum+l.line_total_cents,0));
  const key=randomUUID(),command={store_id:store.store_id,review_id:review.review_id};
  await call('orders',command,undefined,key,401);
  // Intentionally discard the original outcome, then recover using only the key.
  const first=await fetch(origin+'/api/v1/orders',{method:'POST',headers:{Origin:origin,'Content-Type':'application/json',Cookie:cookie,'Idempotency-Key':key},body:JSON.stringify(command),signal:AbortSignal.timeout(15000)});
  assert.ok([200,201,202].includes(first.status));await first.arrayBuffer();
  let order_id:string|undefined;
  for(let i=0;i<12;i++){
    const attempt=(await call('order-attempts/'+key,undefined,cookie)).result;
    if(attempt.order_id){const order=(await call('orders/'+attempt.order_id,undefined,cookie)).result;if(order.status==='confirmed'){order_id=order.order_id;break;}}
    await new Promise(resolve=>setTimeout(resolve,250));
  }
  assert.ok(order_id,'Order did not reach confirmed within bounded polling');
  const replay=await call('orders',command,cookie,key);assert.equal(replay.result.order_id,order_id);
  await call('orders',{...command,review_id:randomUUID()},cookie,key,409);
  const otherSession=await call('session',{});const otherCookie=otherSession.response.headers.get('set-cookie')!.split(';')[0];
  await call('orders/'+order_id,undefined,otherCookie,undefined,404);
  writeFileSync(statePath,JSON.stringify({cookie,order_id,command,key}),{mode:0o600});
  console.log(`${store.domain}: SSR, catalog, review, real HTTP admission/replay, simulated payment and session isolation passed`);
}

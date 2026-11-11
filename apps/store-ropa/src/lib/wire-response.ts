// Defensive boundary checks. Domain validation remains in the FastAPI services.
type RecordValue = Record<string, unknown>;
const record = (v:unknown):v is RecordValue => v!==null && typeof v==='object' && !Array.isArray(v);
const integer = (v:unknown,min:number,max:number):v is number => typeof v==='number' && Number.isSafeInteger(v) && v>=min && v<=max;
const uuid = (v:unknown) => typeof v==='string' && /^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i.test(v);
const timestamp = (v:unknown) => typeof v==='string' && /(?:Z|[+-]\d\d:\d\d)$/.test(v) && Number.isFinite(Date.parse(v));
const recovery = (v:unknown) => record(v) && ['none','wait','retry_same_key','investigate'].includes(String(v.action)) && (v.next_retry_at===null || timestamp(v.next_retry_at));
function pricedItems(items:unknown,totals:unknown) {
  if(!Array.isArray(items)||items.length<1||items.length>50||!record(totals))return false;
  if(!items.every(l=>record(l)&&typeof l.product_id==='string'&&typeof l.name==='string'&&integer(l.quantity,1,100)&&integer(l.unit_price_cents,1,10000000)&&l.line_total_cents===l.quantity*l.unit_price_cents))return false;
  const sum=items.reduce((value,l)=>value+l.line_total_cents,0);
  return integer(sum,1,50000000000)&&totals.currency==='BRL'&&totals.subtotal_cents===sum&&totals.total_cents===sum&&totals.shipping_cents===0&&totals.discount_cents===0;
}
export function validWireResponse(route:string,value:unknown,store:string,domain:'food'|'clothing'):boolean {
  if(!record(value)||value.store_id!==store)return false;
  if(route==='preferences'){
    const p=value.profile,o=value.options;if(!record(p)||!record(o)||!integer(value.history_count,0,100)||typeof p.use_history!=='boolean')return false;
    if(p.max_price_cents!==null&&!integer(p.max_price_cents,1,10000000))return false;
    return ['categories','colors','sizes'].every(field=>Array.isArray(p[field])&&p[field].length<=12&&p[field].every((v:unknown)=>typeof v==='string')&&Array.isArray(o[field])&&o[field].length<=1000&&o[field].every((v:unknown)=>typeof v==='string'));
  }
  if(route==='recommendations')return value.algorithm_version==='content-v1'&&['personalized','discovery'].includes(String(value.mode))&&typeof value.catalog_revision==='string'&&/^sha256:[a-f0-9]{64}$/.test(value.catalog_revision)&&Array.isArray(value.items)&&value.items.length<=6&&value.items.every(p=>record(p)&&p.kind===domain&&typeof p.id==='string'&&typeof p.name==='string'&&typeof p.category==='string'&&integer(p.price_cents,1,10000000)&&typeof p.image_url==='string'&&/^\/demo\/[a-z0-9][a-z0-9/_-]*\.(png|jpg|webp|svg)$/.test(p.image_url)&&Array.isArray(p.reasons)&&p.reasons.length>=1&&p.reasons.length<=3&&p.reasons.every((r:unknown)=>typeof r==='string'));
  if(route==='recommendation-events')return uuid(value.event_id)&&typeof value.saved==='boolean';
  if(route==='recommendation-reset')return value.cleared===true;
  if(route==='products')return typeof value.catalog_revision==='string'&&Array.isArray(value.items)&&value.items.length<=100&&value.items.every(p=>record(p)&&p.kind===domain&&typeof p.id==='string'&&typeof p.name==='string'&&typeof p.description==='string'&&typeof p.category==='string'&&integer(p.price_cents,1,10000000)&&p.currency==='BRL');
  if(route.startsWith('products/')) {
    const p=value.product;if(!record(p)||p.kind!==domain||typeof p.name!=='string'||!integer(p.price_cents,1,10000000))return false;
    if(domain==='clothing')return Array.isArray(p.combinations)&&p.combinations.length>0&&p.combinations.every(c=>record(c)&&typeof c.id==='string'&&typeof c.size==='string'&&typeof c.color==='string'&&typeof c.enabled==='boolean');
    const info=p.food_information;if(!record(info)||!Array.isArray(info.ingredients)||!info.ingredients.every(i=>typeof i==='string')||!record(info.allergens)||!record(info.nutrition_per_serving))return false;
    const a=info.allergens;return a.status==='unknown'?a.contains===null&&a.may_contain===null:a.status==='known'&&Array.isArray(a.contains)&&Array.isArray(a.may_contain);
  }
  if(route==='delivery-slots')return value.timezone==='America/Sao_Paulo'&&timestamp(value.server_now)&&Array.isArray(value.items)&&value.items.every(s=>record(s)&&typeof s.id==='string'&&s.enabled===true&&timestamp(s.starts_at)&&timestamp(s.ends_at));
  if(route==='reviews')return uuid(value.review_id)&&timestamp(value.expires_at)&&pricedItems(value.items,value.totals);
  if(value.status==='validating'||value.status==='accepted'||value.status==='rejected')return uuid(value.attempt_id)&&recovery(value.recovery)&&(value.status==='accepted'?uuid(value.order_id):value.order_id===null);
  if(!['payment_pending','payment_unknown','confirmed','payment_conflict'].includes(String(value.status))||!uuid(value.order_id)||!uuid(value.review_id)||!recovery(value.recovery)||!pricedItems(value.items,value.totals)||!record(value.payment)||!record(value.totals))return false;
  const p=value.payment;
  if(p.method!=='simulated_pix'||p.simulated!==true||p.amount_cents!==value.totals.total_cents)return false;
  return value.status==='confirmed'?p.status==='approved'&&uuid(p.payment_id):p.status==='not_observed'&&p.payment_id===null;
}

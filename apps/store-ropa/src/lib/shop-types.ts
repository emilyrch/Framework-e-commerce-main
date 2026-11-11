export type PublicStore = {store_id:string; display_name:string; domain:'clothing'|'food'; config_hash:string; timezone:string};
export type Combination = {id:string; size:string; color:string; enabled:boolean};
export type FoodInfo = {ingredients:string[]; allergens:{status:'known'|'unknown'; contains:string[]|null; may_contain:string[]|null}; nutrition_per_serving:Record<string,string|number>};
export type Product = {id:string; name:string; description:string; category:string; price_cents:number; kind:'clothing'|'food'; image_url:string; combinations?:Combination[]; food_information?:FoodInfo};
export type CartLine = {product_id:string; combination_id?:string; quantity:number; name:string; label:string; price_cents:number; image_url?:string};
export type Slot = {id:string; starts_at:string; ends_at:string};
export type Session = {session_context_id:string; expires_at:string};
export type Review = {review_id:string; expires_at:string; items:{product_id:string; name:string; quantity:number; unit_price_cents:number; line_total_cents:number; combination?:Pick<Combination,'id'|'size'|'color'>; food_information?:FoodInfo}[]; totals:{subtotal_cents:number; shipping_cents:number; total_cents:number}};
export type Delivery = {address:{recipient:string; street:string; number:string; district:string; city:string; state:string; postal_code:string}; slot?:Slot};
export type Purchase = {order_id?:string|null; status:string; order_status?:string|null; recovery:{action:string; next_retry_at:string|null}; error?:{code:string}|null; totals?:{total_cents:number}; items?:Review['items']; delivery?:Delivery};
export type Pending = {key:string; review_id:string; context:string; order_id?:string; cart_fingerprint:string};
export function addressInput(key:string,value:string){
  return key==='state'?value.toUpperCase().replace(/[^A-Z]/g,'').slice(0,2):key==='postal_code'?value.replace(/\D/g,'').slice(0,8):value;
}
export function selection(line:CartLine) { return {product_id:line.product_id, quantity:line.quantity, ...(line.combination_id ? {combination_id:line.combination_id}: {})}; }
export function lineKey(line:Pick<CartLine,'product_id'|'combination_id'>) { return line.product_id+':'+(line.combination_id??''); }
export function cartFingerprint(lines:CartLine[]) { return JSON.stringify(lines.map(selection).sort((a,b)=>lineKey(a).localeCompare(lineKey(b)))); }
export function reconcileConfirmedCart(cart:CartLine[], pending:Pending, purchase:Purchase):CartLine[] {
  return purchase.status==='confirmed' && Boolean(purchase.order_id) && cartFingerprint(cart)===pending.cart_fingerprint ? [] : cart;
}
export function validCart(input:unknown): input is CartLine[] {
  return Array.isArray(input) && input.length<=50 && input.every(l=>l && typeof l.product_id==='string' && (l.combination_id===undefined || typeof l.combination_id==='string') && typeof l.name==='string' && typeof l.label==='string' && Number.isSafeInteger(l.quantity) && l.quantity>=1 && l.quantity<=100 && Number.isSafeInteger(l.price_cents) && l.price_cents>0) && new Set(input.map(lineKey)).size===input.length;
}
export const money = (cents:number) => new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(cents/100);

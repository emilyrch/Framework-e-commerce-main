import type {Product,PublicStore} from './shop-types';
export type Preferences={categories:string[];colors:string[];sizes:string[];max_price_cents:number|null;use_history:boolean};
export type Profile={store_id:string;profile:Preferences;options:{categories:string[];colors:string[];sizes:string[]};history_count:number};
export type SuggestedProduct=Product&{reasons:string[]};
export type Suggestions={store_id:string;mode:'personalized'|'discovery';catalog_revision:string;algorithm_version:'content-v1';items:SuggestedProduct[]};

export async function recommendationApi<T>(route:string,body?:unknown):Promise<T>{
  const response=await fetch('/api/v1/'+route,{method:body===undefined?'GET':'POST',credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(7000),headers:body===undefined?{}:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
  if(!response.ok)throw new Error('Recomendação indisponível');
  return response.json();
}
export async function recordRecommendationEvent(store:PublicStore,product_id:string,kind:'view'|'add_to_cart'){
  return recommendationApi<{saved:boolean}>('recommendation-events',{store_id:store.store_id,event_id:crypto.randomUUID(),product_id,kind});
}

import type {Purchase} from './shop-types.ts';

export const purchaseSettled = (status?:string) => ['confirmed','rejected','payment_conflict'].includes(status??'');

// Read-only bounded follow-up. A lost response must never generate a new purchase key.
export async function followPurchase(
  read:()=>Promise<Purchase>,
  receive:(purchase:Purchase)=>void,
  options:{active:()=>boolean; sleep?:(ms:number)=>Promise<void>; attempts?:number},
):Promise<'settled'|'paused'|'cancelled'> {
  const sleep=options.sleep??(ms=>new Promise(resolve=>setTimeout(resolve,ms)));
  for(let attempt=0;attempt<(options.attempts??12);attempt++){
    await sleep(2000);
    if(!options.active())return 'cancelled';
    try{
      const purchase=await read();
      if(!options.active())return 'cancelled';
      receive(purchase);
      if(purchaseSettled(purchase.status))return 'settled';
    }catch{/* Transient reads do not change durable purchase state or its key. */}
  }
  return options.active()?'paused':'cancelled';
}

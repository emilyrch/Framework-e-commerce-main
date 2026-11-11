import type {Session} from './shop-types.ts';

// Recommendation loading and checkout share one in-flight cookie bootstrap.
// Separate concurrent POSTs without a cookie could otherwise create two owners.
export function sessionBootstrap(request:()=>Promise<Session>){
  let pending:Promise<Session>|undefined;
  return ()=>{
    pending??=request().finally(()=>{pending=undefined;});
    return pending;
  };
}
export class BrowserSessionError extends Error{
  code:string;
  constructor(code:string){super(code);this.code=code;}
}
export const ensureBrowserSession=sessionBootstrap(async()=>{
  const response=await fetch('/api/v1/session',{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json'},body:'{}',signal:AbortSignal.timeout(7000)});
  const value=await response.json();
  if(!response.ok)throw new BrowserSessionError(value.error?.code??'SESSION_UNAVAILABLE');
  return value as Session;
});

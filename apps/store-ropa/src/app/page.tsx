import { runtime } from '@/lib/server-runtime';
import Storefront from '@/components/storefront';
export const dynamic='force-dynamic';
export default function Home(){
  const {config,config_hash,dependencies}=runtime();
  const services=dependencies.map(({service,url})=>({service,port:new URL(url).port||(url.startsWith('https:')?'443':'80')}));
  return <Storefront services={services} store={{store_id:config.store_id,display_name:config.display_name,domain:config.domain,config_hash,timezone:config.timezone}}/>;
}

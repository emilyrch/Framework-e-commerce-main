import path from 'node:path';
import {loadManifest} from '@/lib/store-config';
import ProductConfigurator from '@/components/product-configurator';
export const dynamic='force-dynamic';
export default function ConfiguratorPage(){
  const root=process.env.LPS_ROOT??path.resolve(process.cwd(),'../..');
  const variants=(['clothing','food'] as const).map(variant=>({variant,...loadManifest(path.join(root,'configurations',variant+'.json'),root)}));
  return <ProductConfigurator variants={variants}/>;
}

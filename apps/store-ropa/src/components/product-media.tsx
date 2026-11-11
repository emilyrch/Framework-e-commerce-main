'use client';
import {useState} from 'react';
import ProductArt from './product-art';

export default function ProductMedia({id,name,imageUrl,food=false}:{id:string;name:string;imageUrl?:string;food?:boolean}){
  const [failed,setFailed]=useState(false);
  const local=typeof imageUrl==='string'&&/^\/demo\/[a-z0-9][a-z0-9/_-]*\.(png|jpg|webp|svg)$/.test(imageUrl);
  if(!local||failed||imageUrl==='/demo/catalog-fallback.svg')return <ProductArt id={id} food={food}/>;
  // Catalog assets are local, have intrinsic dimensions, and work without an image service.
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={imageUrl} alt={`${name} — imagem ilustrativa`} width={1254} height={1254} loading="lazy" className="product-art product-photo" onError={()=>setFailed(true)}/>;
}

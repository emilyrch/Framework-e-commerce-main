'use client';
import {useCallback,useEffect,useRef,useState} from 'react';
import {money} from '@/lib/shop-types';
import type {PublicStore} from '@/lib/shop-types';
import {recommendationApi} from '@/lib/recommendations';
import type {Preferences,Profile,Suggestions} from '@/lib/recommendations';
import ProductMedia from './product-media';
import {ensureBrowserSession} from '@/lib/browser-session';

export default function RecommendationsPanel({store,revision,onSelect}:{store:PublicStore;revision:number;onSelect:(id:string)=>void}){
  const [profile,setProfile]=useState<Profile|null>(null),[suggestions,setSuggestions]=useState<Suggestions|null>(null),[draft,setDraft]=useState<Preferences|null>(null);
  const [budget,setBudget]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const profileReady=profile!==null;
  const mounted=useRef(false),generation=useRef(0),saving=useRef(false);
  const applyProfile=useCallback((value:Profile)=>{
    setProfile(value);setDraft({...value.profile,categories:value.profile.categories.filter(v=>value.options.categories.includes(v)),colors:value.profile.colors.filter(v=>value.options.colors.includes(v)),sizes:value.profile.sizes.filter(v=>value.options.sizes.includes(v))});
    setBudget(value.profile.max_price_cents===null?'':String(value.profile.max_price_cents/100));
  },[]);
  const load=useCallback(async()=>{
    if(!mounted.current)return;
    const request=++generation.current;setError('');setBusy(true);
    try{
      await ensureBrowserSession();
      const [prefs,recs]=await Promise.all([recommendationApi<Profile>('preferences'),recommendationApi<Suggestions>('recommendations')]);
      if(mounted.current&&request===generation.current){applyProfile(prefs);setSuggestions(recs);}
    }catch{if(mounted.current&&request===generation.current)setError('As sugestões estão indisponíveis. Você pode continuar escolhendo na coleção.');}
    finally{if(mounted.current&&request===generation.current)setBusy(false);}
  },[applyProfile]);
  useEffect(()=>{const counter=generation;mounted.current=true;void load();return()=>{mounted.current=false;++counter.current;};},[load]);
  useEffect(()=>{
    if(!revision||!profileReady)return;
    let active=true;const request=generation.current;
    Promise.all([recommendationApi<Suggestions>('recommendations'),recommendationApi<Profile>('preferences')]).then(([value,prefs])=>{if(active&&mounted.current&&generation.current===request){setSuggestions(value);setProfile(current=>current?{...current,history_count:prefs.history_count}:current);}}).catch(()=>{});
    return()=>{active=false;};
  },[revision,profileReady]);
  function toggle(field:'categories'|'colors'|'sizes',value:string){setDraft(current=>current?{...current,[field]:current[field].includes(value)?current[field].filter(v=>v!==value):[...current[field],value]}:current);}
  async function save(clear=false){
    if(saving.current||!draft)return;saving.current=true;setBusy(true);setError('');++generation.current;
    try{
      if(clear){await recommendationApi('recommendation-reset',{store_id:store.store_id});}
      else{
        const cents=budget.trim()===''?null:Math.round(Number(budget)*100);
        if(cents!==null&&(!Number.isSafeInteger(cents)||cents<1||cents>10000000)){setError('Informe um limite entre R$ 0,01 e R$ 100.000,00.');return;}
        applyProfile(await recommendationApi<Profile>('preferences',{...draft,max_price_cents:cents,store_id:store.store_id}));
      }
      await load();
    }catch{if(mounted.current)setError('Não foi possível salvar suas preferências. Tente novamente.');}
    finally{saving.current=false;if(mounted.current)setBusy(false);}
  }
  return <section className="recommendations" aria-labelledby="recommendation-heading">
    <div className="section-heading"><div><span className="eyebrow">ESCOLHAS QUE COMBINAM COM VOCÊ</span><h2 id="recommendation-heading">{suggestions?.mode==='personalized'?'Uma seleção com a sua cara.':'Por onde começar?'}</h2></div><span className="muted">Preferências e histórico desta sessão</span></div>
    <p className="recommendation-intro">{store.domain==='clothing'?'Conte quais categorias, cores e tamanhos você prefere.':'Escolha as categorias que você mais gosta.'} As sugestões também podem considerar os produtos que você vê e adiciona à sacola.</p>
    {error&&<div className="recommendation-error" role="status"><span>{error}</span><button className="text-button" disabled={busy} onClick={()=>void load()}>Tentar novamente</button></div>}
    {profile&&draft&&<details className="preferences"><summary>Personalizar minhas preferências <span>{profile.history_count} interações salvas</span></summary><form onSubmit={e=>{e.preventDefault();void save();}}>
      {(['categories','colors','sizes']as const).filter(field=>profile.options[field].length).map(field=><fieldset key={field}><legend>{field==='categories'?'Categorias de interesse':field==='colors'?'Cores':'Tamanhos'}</legend><div className="preference-options">{profile.options[field].map(option=><label key={option}><input type="checkbox" checked={draft[field].includes(option)} onChange={()=>toggle(field,option)}/><span>{option}</span></label>)}</div></fieldset>)}
      <div className="preference-controls"><label>Preço máximo por peça (R$)<input type="number" min="0.01" max="100000" step="0.01" placeholder="Sem limite" value={budget} onChange={e=>setBudget(e.target.value)}/></label><label className="history-toggle"><input type="checkbox" checked={draft.use_history} onChange={e=>setDraft({...draft,use_history:e.target.checked})}/><span>Usar meu histórico de visualizações e sacola. Desativar apaga as interações salvas.</span></label></div>
      <div className="preference-actions"><button className="primary" disabled={busy}>Salvar preferências →</button><button type="button" className="text-button" disabled={busy} onClick={()=>void save(true)}>Limpar preferências e histórico</button></div><p className="small-note">Limpar também pausa o histórico. Dados separados por loja e vinculados somente ao cookie deste navegador. Sugestões não representam estoque ou garantia de disponibilidade.</p>
    </form></details>}
    {!suggestions&&busy&&<p role="status" className="muted">Preparando sugestões…</p>}
    {suggestions&&(!suggestions.items.length?<div className="recommendation-empty">Nenhum produto combina com esses limites. Ajuste cor, tamanho ou preço máximo.</div>:<div className="recommendation-grid">{suggestions.items.map(p=><button className="recommendation-card" key={p.id} onClick={()=>onSelect(p.id)}><div className="recommendation-image"><ProductMedia id={p.id} name={p.name} imageUrl={p.image_url} food={store.domain==='food'}/><span aria-hidden="true">↗</span></div><span className="product-meta">{p.category}</span><h3>{p.name}</h3><strong>{money(p.price_cents)}</strong><p>{p.reasons[0]}</p></button>)}</div>)}
  </section>;
}

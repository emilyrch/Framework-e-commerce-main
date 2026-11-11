'use client';
import {useState} from 'react';
import Link from 'next/link';
import type {StoreConfig} from '@/lib/store-config';

type Variant={variant:'clothing'|'food';config:StoreConfig;config_hash:string};
export default function ProductConfigurator({variants}:{variants:Variant[]}){
  const [selected,setSelected]=useState('clothing');
  const choice=variants.find(item=>item.variant===selected)!;
  function download(){
    const url=URL.createObjectURL(new Blob([JSON.stringify(choice.config,null,2)+'\n'],{type:'application/json'}));
    const anchor=document.createElement('a');anchor.href=url;anchor.download=choice.variant+'.json';anchor.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  return <main className="flow-section configurator"><Link href="/">← Voltar à loja</Link><p className="eyebrow">LINHA DE PRODUTO DE SOFTWARE</p><h1>Uma base. Duas lojas.</h1><p>Escolha o domínio para derivar uma configuração válida. As capacidades comuns são obrigatórias; não há opções artificiais para desativá-las.</p>
    <fieldset><legend>Domínio — escolha exclusiva</legend>{variants.map(item=><label key={item.variant}><input type="radio" name="domain" value={item.variant} checked={selected===item.variant} onChange={()=>setSelected(item.variant)}/>{item.variant==='clothing'?'Loja de roupas':'Loja de alimentos'}</label>)}</fieldset>
    <h2>{choice.config.display_name}</h2><p>Identidade: <code>{choice.config.store_id}</code></p><p className="config-hash">Configuração validada: <code>{choice.config_hash}</code></p>
    <h3>Features selecionadas</h3><ul>{choice.config.features.map(feature=><li key={feature}>{feature}</li>)}</ul><p>Recomendações por preferências e histórico são uma extensão comum fixa. Não constituem toggle do manifesto v1.</p>
    <p>{selected==='clothing'?'Seleção por combinação habilitada de tamanho/cor; entrega sem agendamento.':'Produtos por unidade, informações alimentares e entrega obrigatoriamente agendada.'}</p>
    <button className="primary" onClick={download}>Baixar manifesto validado ↓</button>
    <h2>Construir e executar este produto</h2><ol><li>Encerre a variante atual com Ctrl+C no terminal.</li><li>Na raiz do mesmo repositório, execute os comandos abaixo.</li><li>Abra <strong>http://127.0.0.1:3000</strong>. Confira a loja selecionada e realize a demonstração.</li></ol>
    <pre>{`.\\.venv\\Scripts\\python.exe tools/lps.py init ${selected}\n.\\.venv\\Scripts\\python.exe tools/lps.py build-web ${selected}\n.\\.venv\\Scripts\\python.exe tools/lps.py run ${selected}`}</pre>
    <p>Para desenvolvimento, use <code>tools/lps.py run {selected} --dev</code>. O lançador utiliza o manifesto versionado <code>configurations/{selected}.json</code>, idêntico ao download. A seleção nesta tela não troca a loja em execução nem executa comandos no servidor. As duas variantes compartilham código e possuem dados privados separados.</p>
  </main>;
}

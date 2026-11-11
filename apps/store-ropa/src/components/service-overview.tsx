'use client';
import {useState} from 'react';
export type ServicePort={service:string;port:string};
export default function ServiceOverview({services}:{services:ServicePort[]}){
  const [checks,setChecks]=useState<Record<string,string>>({}),[busy,setBusy]=useState(false),[message,setMessage]=useState('');
  async function verify(){
    setBusy(true);setMessage('');
    try{
      const response=await fetch('/health/ready',{cache:'no-store',signal:AbortSignal.timeout(7000)});
      const result=await response.json();setChecks(result.checks??{});
      setMessage(response.ok?'Prontidão informada pelos processos. Isso não substitui o teste de compra.':'Há serviços indisponíveis ou configuração divergente.');
    }catch{setMessage('Não foi possível consultar a prontidão.');}finally{setBusy(false);}
  }
  return <details className="service-overview"><summary>Arquitetura do projeto · microsserviços</summary><p>Frontend Next.js e quatro aplicações FastAPI independentes. Portas de comunicação configuradas; somente o frontend é publicado no Compose.</p><ul>{services.map(item=><li key={item.service}><strong>{item.service}</strong><span>porta {item.port} · {checks[item.service]==='ok'?'pronto':checks[item.service]?'indisponível/divergente':'não verificado'}</span></li>)}</ul><button className="secondary" disabled={busy} onClick={()=>void verify()}>{busy?'Consultando…':'Consultar prontidão'}</button><p role="status">{message}</p><a href="/configurador">Abrir seletor de produtos da LPS →</a></details>;
}

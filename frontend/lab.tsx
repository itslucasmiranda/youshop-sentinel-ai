import React, {useEffect, useState} from "react";
import {api, money} from "./client";
import type {Case} from "./src";

type Counts = {tp:number; tn:number; fp:number; fn:number};
type Summary = {orders:number; creators:number; products:number; days:number; counts:Counts};
type Plan = {source:string; cases:{order:string; description:string; expected:boolean; baseline:boolean}[]};
type Proposal = {revision:string; checks:string[]; baseline:Counts; replay:Counts|null; decision:string|null};
type Row = {order:string; date:string; posted:number; expected:number; status:string};

function useRead<T>(url:string) {
  const [result,set] = useState<T>(), [error,fail] = useState("");
  useEffect(()=>{
    let active = true;
    set(undefined); fail("");
    api<T>(url).then(value=>{if(active)set(value)}).catch(e=>{if(active)fail(String(e))});
    return ()=>{active=false};
  },[url]);
  return {result,set,error};
}

export function Overview(){
  const {result,error}=useRead<Summary>("/api/twin");
  return <section><h2>Carteira simulada</h2><p>Resultados da primeira conferência sobre todos os pedidos fictícios.</p>
    {error && <p role="alert">{error}</p>}
    {result && <><div className="totals">{Object.entries({Pedidos:result.orders,Criadores:result.creators,Produtos:result.products,Dias:result.days}).map(([key,n])=><div key={key}>{key}<strong>{n.toLocaleString("pt-BR")}</strong></div>)}</div>
    <CountsView counts={result.counts}/></>}</section>
}
function CountsView({counts:c}:{counts:Counts}){
  const groups = [
    ["Problemas detectados",c.tp,"A regra pediu revisão corretamente."],
    ["Pedidos regulares",c.tn,"A regra liberou pedidos corretos."],
    ["Alertas indevidos",c.fp,"Pedidos regulares enviados para revisão."],
    ["Problemas sem alerta",c.fn,"Precisavam de revisão e passaram pela regra."]
  ] as const;
  const total = c.tp+c.tn+c.fp+c.fn;
  return <div className="outcomes"><h3>O que a regra encontrou</h3><div className="distribution" aria-hidden="true">{groups.map(([label,n])=><i key={label} style={{width:(total?n/total*100:0)+"%"}}/>)}</div><div className="legend">{groups.map(([label,n,meaning])=><div key={label}><small>{label}</small><b>{n.toLocaleString("pt-BR")}</b><p>{meaning}</p></div>)}</div></div>

}

export function Simulation({open}:{open:(id:string)=>void}){
  const [plan,set]=useState<Plan>(),[busy,wait]=useState(false),[error,fail]=useState("");
  async function run(){
    wait(true); fail("");
    try {set(await api<Plan>("/api/twin/plan",{}))} catch(e){fail(String(e))} finally{wait(false)}
  }
  return <section><h1>Testar cenários</h1><p>Execute vendas fictícias com situações conhecidas. Se o cenário pede revisão e a regra libera o pedido, você encontrou uma falha no teste.</p>
    <button disabled={busy} onClick={run}>{busy?"Executando…":"Selecionar e executar cenários"}</button>{error && <p role="alert">{error}</p>}
    {plan && <><p>{plan.source}</p><ul>{plan.cases.map(c=><li key={c.order}><strong>{c.description}</strong> · Esperado: {c.expected?"revisão":"conciliado"} · Observado: {c.baseline?"revisão":"conciliado"} <button onClick={()=>open(c.order)}>Ver {c.order}</button></li>)}</ul></>}</section>
}

export function Defense(){
  const {result,set,error}=useRead<Proposal>("/api/twin/proposals"),[failure,fail]=useState(""),[busy,wait]=useState(false);
  async function decide(event:React.FormEvent<HTMLFormElement>){
    event.preventDefault(); if(!result)return;
    const fields=Object.fromEntries(new FormData(event.currentTarget));
    wait(true);fail("");
    try{set(await api<Proposal>("/api/twin/proposals/review",{...fields,revision:result.revision}))}catch(e){fail(String(e))}finally{wait(false)}
  }
  return <section><h1>Avaliar regras</h1><p>Usamos 25 pedidos para encontrar melhorias. Autorize o teste em outros 25 para ver quantos problemas a nova regra consegue identificar.</p>
    {(error||failure)&&<p role="alert">{error||failure}</p>}
    {result&&<><h3>Verificações sugeridas</h3><ul>{result.checks.map(c=><li key={c}>{c}</li>)}</ul><h3>Antes da revisão</h3><CountsView counts={result.baseline}/>
    {result.decision?<p>Parecer registrado: {result.decision}</p>:<form onSubmit={decide}><label>Revisor <input name="reviewer" required maxLength={80}/></label><label>Justificativa <input name="note" required maxLength={500}/></label>
    <label>Decisão <select name="decision"><option value="confirmado">Aprovar repetição no laboratório</option><option value="descartado">Rejeitar</option></select></label><button disabled={busy}>Registrar decisão</button></form>}
    {result.replay&&<><h3>Após aprovação</h3><CountsView counts={result.replay}/></>}</>}</section>
}

export function Creator({open}:{open:(id:string)=>void}){
  const [n,set]=useState(1);
  const {result,error}=useRead<Row[]>("/api/twin/creators/"+n);
  return <section><h1>Comissões por criador</h1><p>Escolha quem divulgou o produto. Compare a comissão calculada pela oferta com o valor lançado em cada venda.</p><label>Perfil de demonstração <select value={n} onChange={e=>set(Number(e.target.value))}>{Array.from({length:500},(_,i)=><option key={i} value={i+1}>creator-{String(i+1).padStart(3,"0")}</option>)}</select></label>
    {error&&<p role="alert">{error}</p>}<div className="scroll-table"><table><thead><tr>{["Pedido","Data","Prevista","Registrada","Conferência"].map(label=><th key={label}>{label}</th>)}</tr></thead><tbody>{result?.map(r=><tr key={r.order}><td><button onClick={()=>open(r.order)}>{r.order}</button></td><td>{r.date.split("-").reverse().join("/")}</td><td>{money(r.expected)}</td><td>{money(r.posted)}</td><td>{r.status==="revisar"?"Revisão necessária":"Conciliado"}</td></tr>)}</tbody></table></div></section>
}

export function Graph({id}:{id:string}){
  const {result,error}=useRead<Case>("/api/orders/"+encodeURIComponent(id));
  if(!result)return <p>{error||"Carregando relações…"}</p>;
  const a=result.attribution;
  const nodes = [
    ...(a ? [
      {label:"Creator", value:a.creator, detail:"Creator associado ao link " + a.link},
      {label:"Link", value:a.link, detail:"Vinculado à oferta " + a.offer},
      {label:"Oferta", value:a.offer, detail:"Produto " + a.product},
    ] : []),
    {label:"Pedido", value:id, detail:"Regra de conciliação " + result.rule},
    ...result.events.map(e=>({label:e.event_type==="order_paid"?"Pagamento":"Reembolso",
      value:e.event_id, detail:money(e.amount_minor)+" · "+e.occurred_at_utc+" · "+e.fixture_version})),
    ...(a ? [{label:"Comissão", value:money(a.posted_minor),
      detail:"Prevista "+money(a.expected_minor)+" · Crédito atribuído a "+a.attributed_creator}] : [])
  ];
  return <section><h3>Grafo de evidências</h3><ol className="graph">{nodes.map(node=>
    <li key={node.label+node.value}><details><summary>{node.label} · {node.value}</summary><p>{node.detail}</p></details></li>)}</ol></section>
}
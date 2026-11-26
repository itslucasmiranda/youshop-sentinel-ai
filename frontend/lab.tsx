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
  const [onlyMisses, filter] = useState(false);
  const misses = plan?.cases.filter(c=>c.expected !== c.baseline).length ?? 0;
  return <section><div className="workhead"><div><h1>Testar cenários</h1><p>Descubra em quais vendas a regra deixa passar um problema.</p></div>
    <button disabled={busy} onClick={run}>{busy?"Executando…":plan?"Executar novamente":"Executar simulação"} →</button></div>
    {error && <p role="alert">{error}</p>}
    {!plan && <div className="workflow"><h2>Como funciona o teste</h2><div className="stages">
      <div><b>Selecionar vendas</b><p>O sistema reúne uma venda regular e pedidos com situações conhecidas.</p></div>
      <div><b>Conferir o alerta</b><p>A regra decide se cada pedido merece revisão.</p></div>
      <div><b>Investigar diferenças</b><p>Abra o pedido para comparar a decisão com o resultado esperado.</p></div></div></div>}
    {plan && <><div className="verdict"><div><small>Resultado da rodada</small><h2>{misses} de {plan.cases.length} casos divergiram</h2><p>Uma divergência ocorre quando a decisão da regra difere da resposta conhecida do teste.</p></div></div>
      <div className="sectionbar"><h2>Casos testados</h2><label className="inlinecheck"><input type="checkbox" checked={onlyMisses} onChange={e=>filter(e.target.checked)}/>Só divergências</label></div>
      <div className="casegrid">{plan.cases.filter(c=>!onlyMisses || c.expected!==c.baseline).map(c=><article className="casecard" key={c.order}>
        <span className={c.expected===c.baseline?"pill":"pill amber"}>{c.expected===c.baseline?"Decisão correta":c.expected?"Problema sem alerta":"Alerta indevido"}</span>
        <h3>{c.description}</h3><dl><dt>Deveria</dt><dd>{c.expected?"Pedir revisão":"Liberar"}</dd><dt>A regra decidiu</dt><dd>{c.baseline?"Pedir revisão":"Liberar"}</dd></dl>
        <button onClick={()=>open(c.order)}>Investigar {c.order} ↗</button></article>)}</div>
      {onlyMisses && !misses && <p>Todos os casos tiveram a decisão esperada.</p>}<p className="subtle">Método de seleção · {plan.source}</p></>}</section>
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
    {result&&<><div className="verdict"><div><small>Diagnóstico da regra inicial</small><h2>{result.baseline.fn} problemas passaram sem alerta</h2><p>Esses pedidos deveriam ter sido encaminhados a uma pessoa para conferência.</p></div></div>
      <div className="casegrid"><article className="casecard"><h2>O que muda no teste?</h2><p>As verificações sugeridas pedem revisão nestas situações:</p><ul>{result.checks.map(c=><li key={c}>{c}</li>)}</ul></article>
      <article className="casecard"><h2>Decisão do revisor</h2><p>A aprovação repete o teste nos 25 pedidos reservados. A rejeição encerra a proposta.</p>
      {result.decision?<strong>Parecer registrado · {result.decision}</strong>:<details><summary>Revisar proposta</summary><form onSubmit={decide}><label>Revisor <input name="reviewer" required maxLength={80}/></label><label>Justificativa <input name="note" required maxLength={500}/></label>
      <label>Decisão <select name="decision"><option value="confirmado">Aprovar teste</option><option value="descartado">Rejeitar proposta</option></select></label><button disabled={busy}>Registrar decisão</button></form></details>}</article></div>
      <h3>Resultado inicial</h3><CountsView counts={result.baseline}/>
    {result.replay&&<><h3>Após aprovação</h3><CountsView counts={result.replay}/></>}</>}</section>
}

export function Creator({open}:{open:(id:string)=>void}){
  const [n,set]=useState(1);
  const {result,error}=useRead<Row[]>("/api/twin/creators/"+n);
  const [scope,filter]=useState("todos");
  const rows=[...(result??[])].sort((a,b)=>b.date.localeCompare(a.date));
  const total=(key:"expected"|"posted")=>rows.reduce((sum,r)=>sum+r[key],0);
  const months=Array.from(new Set(rows.map(r=>r.date.slice(0,7)))).sort().map(m=>({
    month:m, amount:rows.filter(r=>r.date.startsWith(m)).reduce((sum,r)=>sum+r.posted,0)
  }));
  const visible=rows.filter(r=>scope==="todos"||r.status===scope);
  return <section><div className="workhead"><div><h1>Comissões por criador</h1><p>Veja quanto a oferta prevê e quanto foi lançado para quem divulgou a venda.</p></div>
    <label>Escolher criador<select value={n} onChange={e=>set(Number(e.target.value))}>{Array.from({length:500},(_,i)=><option key={i} value={i+1}>Criador {String(i+1).padStart(3,"0")}</option>)}</select></label></div>
    {error&&<p role="alert">{error}</p>}{result?<><div className="casegrid"><article className="casecard"><small>Comissão registrada</small><h2 className="bigvalue">{money(total("posted"))}</h2><p>Somando {rows.length} pedidos. A regra da oferta prevê <b>{money(total("expected"))}</b>.</p></article>
    <article className="casecard"><h3>Lançamentos por mês</h3>{months.map(m=><div className="monthrow" key={m.month}><span>{new Date(m.month+"-15T12:00:00").toLocaleDateString("pt-BR",{month:"short"})}</span><meter min={0} max={Math.max(1,...months.map(x=>x.amount))} value={m.amount}/><b>{money(m.amount)}</b></div>)}</article></div>
    <div className="sectionbar"><h2>Extrato de pedidos</h2><select aria-label="Filtrar extrato" value={scope} onChange={e=>filter(e.target.value)}><option value="todos">Todos os pedidos</option><option value="revisar">Em revisão</option><option value="conciliado">Conciliados</option></select></div>
    <div className="scroll-table"><table><thead><tr>{["Pedido","Data","Prevista","Registrada","Situação"].map(label=><th key={label}>{label}</th>)}</tr></thead><tbody>{visible.map(r=><tr key={r.order}><td><button onClick={()=>open(r.order)}>{r.order} ↗</button></td><td>{r.date.split("-").reverse().join("/")}</td><td>{money(r.expected)}</td><td>{money(r.posted)}</td><td><span className={r.status==="revisar"?"pill amber":"pill"}>{r.status==="revisar"?"Em revisão":"Conciliado"}</span></td></tr>)}</tbody></table>{!visible.length&&<p>Nenhum pedido nesta situação para este criador.</p>}</div></>:!error&&<p role="status">Consultando extrato…</p>}</section>
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
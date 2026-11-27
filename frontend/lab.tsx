import React, {useEffect, useRef, useState} from "react";
import {api, money} from "./client";
import type {Case} from "./src";

type Counts = {tp:number; tn:number; fp:number; fn:number};
type Summary = {orders:number; creators:number; products:number; days:number; counts:Counts};
type Plan = {source:string; cases:{order:string; description:string; expected:boolean; baseline:boolean}[]};
type Proposal = {revision:string; checks:string[]; baseline:Counts; replay:Counts|null; decision:string|null};
type Row = {order:string; date:string; posted:number; expected:number; status:string; payout_status:string; payout_date:string};

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

export function Overview({evaluate}:{evaluate:()=>void}){
  const {result,error}=useRead<Summary>("/api/twin");
  return <section><h2>Carteira simulada</h2>
    {error && <p role="alert">{error}</p>}
    {!result && !error && <p role="status">Carregando o resumo…</p>}
    {result && <><div className="totals">{Object.entries({Pedidos:result.orders,Criadores:result.creators,Produtos:result.products,"Sinalizados pela regra":result.counts.tp+result.counts.fp}).map(([key,n])=><div key={key}>{key}<strong>{n.toLocaleString("pt-BR")}</strong></div>)}</div>
    <details><summary>Ver resultados da regra em {result.days} dias simulados</summary><CountsView counts={result.counts}/><button onClick={evaluate}>Avaliar regras →</button></details></>}</section>
}
const outcomes = [
  ["tp","Problemas detectados","A regra pediu revisão corretamente."],
  ["tn","Pedidos regulares liberados","A regra liberou pedidos corretos."],
  ["fp","Alertas indevidos","Pedidos regulares enviados para revisão."],
  ["fn","Problemas sem alerta","Precisavam de revisão e passaram pela regra."],
] as const;

function CountsView({counts:c}:{counts:Counts}){
  const total = c.tp+c.tn+c.fp+c.fn;
  return <div className="outcomes"><h3>O que a regra encontrou</h3><div className="distribution" aria-hidden="true">{outcomes.map(([key])=><i key={key} style={{width:(total?c[key]/total*100:0)+"%"}}/>)}</div><div className="legend">{outcomes.map(([key,label,meaning])=><div key={key}><small>{label}</small><b>{c[key].toLocaleString("pt-BR")}</b><p>{meaning}</p></div>)}</div></div>

}

export function Simulation({open,evaluate}:{open:(id:string)=>void;evaluate:()=>void}){
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
        <h3>{c.expected?"Condições do cenário":"Venda regular"}</h3>
        {c.expected&&<ul className="scenario-signals">{c.description.split(" + ").map(condition=><li key={condition}>{condition}</li>)}</ul>}
        <dl><dt>Esperado</dt><dd>{c.expected?"Pedir revisão":"Liberar"}</dd><dt>Observado</dt><dd>{c.baseline?"Pediu revisão":"Liberou"}</dd></dl>
        <button aria-label={`Investigar pedido ${c.order}`} onClick={()=>open(c.order)}>Investigar pedido ↗</button></article>)}</div>
      {onlyMisses && !misses && <p>Todos os casos tiveram a decisão esperada.</p>}<p className="subtle">Seleção dos casos · {plan.source}</p><button onClick={evaluate}>Avaliar proposta de regra →</button></>}</section>
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
    {!result && !error && <p role="status">Carregando a proposta…</p>}
    {result&&<><div className="verdict"><div><small>Diagnóstico da regra inicial</small><h2>{result.baseline.fn} problemas passaram sem alerta</h2><p>Esses pedidos deveriam ter sido encaminhados a uma pessoa para conferência.</p></div></div>
      <div className="casegrid"><article className="casecard"><h2>O que muda no teste?</h2><p>As verificações sugeridas pedem revisão nestas situações:</p><ul>{result.checks.map(c=><li key={c}>{c}</li>)}</ul></article>
      <article className="casecard"><h2>Decisão do revisor</h2><p>A aprovação repete a conferência nos mesmos 25 pedidos reservados, desta vez com as verificações novas. A rejeição encerra a proposta.</p>
      {result.decision?<strong role="status">{result.decision==="confirmado"?"Teste aprovado e executado":"Proposta rejeitada"}</strong>:<details><summary>Revisar proposta</summary><form onSubmit={decide}><label>Revisor <input name="reviewer" required maxLength={80}/></label><label>Justificativa <input name="note" required maxLength={500}/></label>
      <label>Decisão <select name="decision"><option value="confirmado">Aprovar teste</option><option value="descartado">Rejeitar proposta</option></select></label><button disabled={busy}>Registrar decisão</button></form></details>}</article></div>
      <h2>Comparação nos 25 pedidos reservados</h2>
      <div className="scroll-table"><table><thead><tr><th scope="col">Resultado</th><th scope="col">Regra inicial</th><th scope="col">Após aprovação</th></tr></thead>
      <tbody>{outcomes.map(([key,label])=><tr key={key}><th scope="row">{label}</th><td>{result.baseline[key]}</td><td>{result.replay?.[key]??"—"}</td></tr>)}</tbody></table></div>
      {!result.replay&&<p className="subtle">{result.decision==="descartado"?"A proposta foi rejeitada.":"A segunda coluna de resultados será preenchida após a aprovação."}</p>}</>}</section>
}

export function Creator({open}:{open:(id:string)=>void}){
  const [n,set]=useState(1);
  const {result,error}=useRead<Row[]>("/api/twin/creators/"+n);
  const [scope,filter]=useState("todos");
  const [payout,filterPayout]=useState("");
  const rows=[...(result??[])].sort((a,b)=>b.date.localeCompare(a.date));
  const total=(key:"expected"|"posted")=>rows.reduce((sum,r)=>sum+r[key],0);
  const months=Array.from(new Set(rows.map(r=>r.date.slice(0,7)))).sort().map(m=>({
    month:m, amount:rows.filter(r=>r.date.startsWith(m)).reduce((sum,r)=>sum+r.posted,0)
  }));
  const visible=rows.filter(r=>(scope==="todos"||r.status===scope)&&(!payout||r.payout_status===payout));
  const flagged=rows.filter(r=>r.status==="revisar").length;
  return <section><div className="workhead"><div><h1>Comissões por criador</h1><p>Veja quanto a oferta prevê e quanto foi lançado para quem divulgou a venda.</p></div>
    <label>Escolher criador<select value={n} onChange={e=>set(Number(e.target.value))}>{Array.from({length:500},(_,i)=><option key={i} value={i+1}>Criador {String(i+1).padStart(3,"0")}</option>)}</select></label></div>
    {error&&<p role="alert">{error}</p>}{result?<><div className="casegrid"><article className="casecard"><small>Comissão registrada</small><h2 className="bigvalue">{money(total("posted"))}</h2><p>Somando {rows.length} pedidos. A regra da oferta prevê <b>{money(total("expected"))}</b>.</p></article>
    <article className="casecard"><h3>Lançamentos por mês</h3>{months.map(m=><div className="monthrow" key={m.month}><span>{new Date(m.month+"-15T12:00:00").toLocaleDateString("pt-BR",{month:"short"})}</span><meter min={0} max={Math.max(1,...months.map(x=>x.amount))} value={m.amount}/><b>{money(m.amount)}</b></div>)}</article></div>
    <div className="sectionbar"><h2>Extrato de pedidos</h2><select aria-label="Filtrar extrato" value={scope} onChange={e=>filter(e.target.value)}><option value="todos">Todos os pedidos</option><option value="revisar">Em revisão</option><option value="conciliado">Conciliados</option></select></div>
    {flagged>0 && scope!=="revisar" && <p><button onClick={()=>filter("revisar")}>Ver pedidos sinalizados ({flagged}) →</button></p>}
    <label>Repasse em 31/03/2026<select value={payout} onChange={e=>filterPayout(e.target.value)}>
      <option value="">Todos os repasses</option>
      {["Comissão retida","Repasse agendado","Repasse concluído"].map(label=><option key={label}>{label}</option>)}
    </select></label>
    <p className="subtle">Abra um pedido para conferir os eventos que explicam o repasse.</p>
    <div className="scroll-table"><table><thead><tr>{["Pedido","Venda","Prevista","Registrada","Conferência","Repasse","Último registro"].map(label=><th key={label}>{label}</th>)}</tr></thead><tbody>{visible.map(r=><tr key={r.order}><td><button onClick={()=>open(r.order)}>{r.order} ↗</button></td><td>{r.date.split("-").reverse().join("/")}</td><td>{money(r.expected)}</td><td>{money(r.posted)}</td><td><span className={r.status==="revisar"?"pill amber":"pill"}>{r.status==="revisar"?"Em revisão":"Conciliado"}</span></td><td>{r.payout_status}</td><td>{r.payout_date.split("-").reverse().join("/")}</td></tr>)}</tbody></table>{!visible.length&&<p>Nenhum pedido nesta situação para este criador.</p>}</div></>:!error&&<p role="status">Consultando extrato…</p>}</section>
}

export function Graph({result}:{result:Case}){
  const [selected, select] = useState(0);
  const a=result.attribution;
  const nodes = [
    ...(a ? [
      {label:"Criador", hint:"Quem divulgou", value:a.creator,
        detail:"O registro da divulgação identifica o criador associado à venda."},
      {label:"Link", hint:"Como a venda foi associada", value:a.link,
        detail:`O link conecta ${a.creator} à oferta ${a.offer}.`},
      {label:"Oferta", hint:"Qual condição se aplica", value:a.offer,
        detail:result.lab_checks?.offer ?? `Esta oferta é do produto ${a.product}. Suas condições servem de base para calcular a comissão prevista.`},
    ] : []),
    {label:"Pedido", hint:"Onde os registros se encontram", value:result.order_id,
      detail:result.events.some(event=>event.event_type==="order_refunded")
        ? `O histórico registra ${money(result.refunded_minor)} em reembolsos. O saldo do pedido é de ${money(result.net_minor)}.`
        : `Nenhum reembolso consta no histórico deste pedido. O saldo registrado é de ${money(result.net_minor)}.`},
    ...result.events.map(event => {
      const payment = event.event_type==="order_paid";
      return {label:payment?"Pagamento":"Reembolso", hint:payment?"Valor pago":"Valor devolvido",
        value:money(event.amount_minor),
        detail:payment?(result.lab_checks?.confirmation ?? "Este evento registra a entrada do pagamento."):"Este evento registra uma devolução ao comprador e reduz o saldo da venda.",
        reference:event.event_id, time:new Date(event.occurred_at_utc).toLocaleString("pt-BR")};
    }),
    ...(a ? [{label:"Comissão", hint:"O que ficou registrado", value:money(a.posted_minor),
      detail:`O crédito foi atribuído a ${a.attributed_creator}. A regra da oferta prevê ${money(a.expected_minor)}.`,
      difference:money(a.posted_minor-a.expected_minor)}] : []),
    ...(result.status==="conciliado" && Object.keys(result.lab_checks??{}).length ? [{
      label:"Resultado do teste", hint:"Por que deveria ir para revisão", value:"Problema sem alerta",
      detail:"Os valores conferem. A regra inicial liberou o pedido sem verificar estas condições: "+Object.values(result.lab_checks??{}).join(" ")
    }] : [])
  ];
  const current = nodes[selected];
  const active = useRef<HTMLButtonElement>(null);
  function goTo(index:number) {
    select(index);
    if (window.matchMedia("(max-width: 650px)").matches) {
      requestAnimationFrame(() => active.current?.scrollIntoView({block:"nearest",inline:"nearest"}));
    }
  }
  return <section className="evidence-walk">
    <h3>Fluxo de evidências do pedido</h3>
    <p>Siga as setas ou clique em uma etapa para ver o que aquele registro comprova.</p>
    <div className="evidence-layout">
      <ol className="evidence-steps" aria-label="Etapas do fluxo">{nodes.map((node,index)=>
        <li key={"reference" in node ? node.reference : node.label}>
          <button ref={selected===index?active:undefined} type="button" aria-current={selected===index?"step":undefined}
            aria-label={node.label} onClick={()=>goTo(index)}>
            <span className="step-number" aria-hidden="true">{index+1}</span>
            <span><strong>{node.label}</strong><small>{node.hint}</small></span>
          </button>
        </li>)}</ol>
      <div className="step-detail" aria-live="polite">
        <small>Etapa {selected+1} de {nodes.length}</small>
        <h4>{current.label}</h4>
        <p>{current.detail}</p>
        <dl>
          <div><dt>{"reference" in current ? "Valor do evento" : current.hint}</dt><dd>{current.value}</dd></div>
          {"reference" in current && <>
            <div><dt>Identificador do evento</dt><dd>{current.reference}</dd></div>
            <div><dt>Quando aconteceu</dt><dd>{current.time}</dd></div>
          </>}
          {"difference" in current && <div><dt>Diferença entre registrada e prevista</dt><dd>{current.difference}</dd></div>}
        </dl>
        <div className="step-controls">
          <button type="button" disabled={selected===0} onClick={()=>goTo(selected-1)}>← Anterior</button>
          <button type="button" disabled={selected===nodes.length-1} onClick={()=>goTo(selected+1)}>Próxima etapa →</button>
        </div>
      </div>
    </div>
  </section>
}

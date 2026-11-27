import React, {useEffect, useState} from "react";
import {api, money} from "./client";

type Order = {order:string; date:string; expected:number; posted:number; status:string};
const fmtDate = (date:string) => date.slice(8)+"/"+date.slice(5,7);
const tones = ["#5be2cb","#a198ff","#f4bd79","#88bcff"];
const add = (rows:Order[], key:"expected"|"posted") => rows.reduce((sum,row)=>sum+row[key],0);

function Trend({rows, start, days}:{rows:Order[];start:number;days:number}){
  const [hover,setHover]=useState<number|null>(null);
  let posted=0,expected=0;
  const series=Array.from({length:days},(_,i)=>{
    const date=new Date(start+i*86400000).toISOString().slice(0,10);
    const daily=rows.filter(r=>r.date===date);
    posted+=add(daily,"posted");expected+=add(daily,"expected");
    return {date,posted,expected};
  });
  const max=Math.max(1,posted,expected);
  const x=(i:number)=>8+i/(days-1)*584;
  const y=(v:number)=>145-v/max*120;
  const line=(key:"posted"|"expected")=>series.map((v,i)=>(i?"L":"M")+x(i)+","+y(v[key])).join(" ");
  const i=Math.min(hover??days-1,days-1);
  return <section className="panel trend"><div className="panelhead"><h2>Evolução das comissões</h2><small>Acumulado no período</small></div>
    <div className="serieskey"><span>● Registrada</span><span>● Prevista</span></div>
    <svg viewBox="0 0 600 156" preserveAspectRatio="none" role="img" aria-label="Comissões registradas e previstas acumuladas" onPointerMove={e=>{const box=e.currentTarget.getBoundingClientRect();setHover(Math.max(0,Math.min(days-1,Math.round((e.clientX-box.left)/box.width*(days-1)))))}} onPointerLeave={()=>setHover(null)}>
      <defs><linearGradient id="fill" x2="0" y2="1"><stop stopColor="#58dcc5" stopOpacity=".32"/><stop offset="1" stopColor="#58dcc5" stopOpacity="0"/></linearGradient></defs>
      {[25,65,105,145].map(h=><line key={h} x1="0" x2="600" y1={h} y2={h} stroke="#293848" strokeDasharray="3 5"/>)}
      <path d={line("posted")+" L592,145 L8,145 Z"} fill="url(#fill)"/>
      <path d={line("posted")} fill="none" stroke={tones[0]} strokeWidth="3"/><path d={line("expected")} fill="none" stroke={tones[1]} strokeWidth="2" strokeDasharray="5 4"/>
      <line x1={x(i)} x2={x(i)} y1="12" y2="146" stroke="#8597b0" strokeDasharray="2 4"/>
      <circle cx={x(i)} cy={y(series[i].posted)} r="4" fill={tones[0]}/>
    </svg><div className="axis"><span>{fmtDate(series[0].date)}</span><span>{fmtDate(series[days-1].date)}</span></div>
    <div className="readout"><b>{fmtDate(series[i].date)}</b> · Registrada {money(series[i].posted)} · Prevista {money(series[i].expected)}</div>
    <input className="dayrange" aria-label="Explorar dia do gráfico" type="range" min="0" max={days-1} value={i} onChange={e=>setHover(Number(e.target.value))}/></section>
}

export function Dashboard({open}:{open:(id:string)=>void}){
  const [creator,choose]=useState(2),[days,period]=useState(90),[data,save]=useState<Order[]>(),[error,fail]=useState(""),[filter,select]=useState("todos");
  useEffect(()=>{let active=true;save(undefined);fail("");api<Order[]>("/api/twin/creators/"+creator).then(rows=>{if(active)save(rows)}).catch(e=>{if(active)fail(String(e))});return ()=>{active=false}},[creator]);
  const last=Date.UTC(2026,2,31), start=last-(days-1)*86400000;
  const rows=(data??[]).filter(row=>Date.parse(row.date)>=start).sort((a,b)=>b.date.localeCompare(a.date)||a.order.localeCompare(b.order));
  const reviewed=rows.filter(row=>row.status==="revisar").length;
  const stats=[["Pedidos no período",String(rows.length),"Vendas vinculadas ao perfil"],["Comissão registrada",money(add(rows,"posted")),"Valor lançado para o criador"],["Comissão prevista",money(add(rows,"expected")),"Pela regra da oferta"],["Em revisão",String(reviewed),"Pedidos que exigem conferência"]];
  const filtered=rows.filter(r=>filter==="todos"||r.status===filter);
  return <><div className="dashhead"><div><h2>Comissões no período</h2><p>Acompanhe os lançamentos e investigue diferenças por criador.</p></div><label>Perfil simulado<select value={creator} onChange={e=>choose(Number(e.target.value))}>{Array.from({length:500},(_,i)=><option value={i+1} key={i}>Criador {String(i+1).padStart(3,"0")}</option>)}</select></label></div>
    <div className="period"><small>{fmtDate(new Date(start).toISOString())} — 31/03/2026</small><div>{[7,30,90].map(n=><button key={n} aria-pressed={days===n} onClick={()=>period(n)}>{n} dias</button>)}</div></div>
    {error?<p role="alert">{error}</p>:!data?<p role="status">Consultando pedidos…</p>:<>
    <div className="kpis">{stats.map(([label,value,hint],i)=><article key={label} style={{borderTopColor:tones[i]}}><small>{label}</small><strong>{value}</strong><span>{hint}</span></article>)}</div>
    <div className="chartgrid"><Trend key={days+"-"+creator} rows={rows} start={start} days={days}/><section className="panel"><h2>Situação dos pedidos</h2><div className="ring" style={{background:rows.length?"conic-gradient(#f4bd79 0 "+reviewed/rows.length*100+"%, #5be2cb 0)":"#30404e"}}><div><strong>{rows.length}</strong><small>pedidos</small></div></div>
    <div className="ringlabel"><span>● Conciliados</span><b>{rows.length-reviewed}</b></div><div className="ringlabel amber"><span>● Em revisão</span><b>{reviewed}</b></div></section></div>
    <section className="panel"><div className="panelhead"><h2>Pedidos do período</h2><select aria-label="Filtrar por situação" value={filter} onChange={e=>select(e.target.value)}><option value="todos">Todas as situações</option><option value="revisar">Em revisão</option><option value="conciliado">Conciliados</option></select></div>
    <div className="scroll-table"><table><thead><tr>{["Pedido","Venda","Prevista","Registrada","Situação"].map(k=><th key={k}>{k}</th>)}</tr></thead><tbody>{filtered.map(r=><tr key={r.order}><td><button onClick={()=>open(r.order)}>{r.order} ↗</button></td><td>{fmtDate(r.date)}</td><td>{money(r.expected)}</td><td>{money(r.posted)}</td><td><span className={r.status==="revisar"?"pill amber":"pill"}>{r.status==="revisar"?"Em revisão":"Conciliado"}</span></td></tr>)}</tbody></table></div>{!filtered.length&&<p>Nenhum pedido nesta seleção.</p>}</section></>}</>
}

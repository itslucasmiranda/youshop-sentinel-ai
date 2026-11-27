import {Dashboard} from "./dashboard";
import {areas, Guide, Example} from "./guide";
import {api, money} from "./client";
import {Overview, Simulation, Defense, Creator, Graph, Related} from "./lab";
import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";

type Event = {
  event_id: string;
  event_type: string;
  amount_minor: number;
  occurred_at_utc: string;
  fixture_version: string;
};
type Attribution = {
  creator: string;
  link: string;
  offer: string;
  product: string;
  attributed_creator: string;
  expected_minor: number;
  posted_minor: number;
};
export type Case = {
  payout?: {id:string; date:string; label:string; detail:string; amount_minor:number}[];
  lab_checks?: {offer?:string; confirmation?:string};
  order_id: string;
  rule: string;
  revision: string;
  status: string;
  reasons: string[];
  events: Event[];
  paid_minor: number;
  refunded_minor: number;
  net_minor: number;
  attribution: Attribution | null;
  review: null | { decision: string; note: string; reviewer: string };
};
type Answer = {
  case_finding?: string;
  message: string;
  draft?: string;
  model?: string;
  sources: { id: string; section: string; url: string; summary: string }[];
};
type Evaluation = {
  counts: Record<string, number>;
  cases: {
    name: string;
    result: string;
    simulated_seconds_to_alert: number | null;
  }[];
};
const caseNames: Record<string, string> = {
  "repasse-retido": "Repasse · comissão retida",
  "repasse-agendado": "Repasse · transferência agendada",
  "repasse-concluido": "Repasse · transferência concluída",
  "repasse-cancelado": "Repasse · pedido cancelado",
  "comissao-apos-reembolso": "Comissão após reembolso integral",
  "atribuicao-divergente": "Venda atribuída a outro criador",
  "comissao-normal": "Venda com comissão correta",
  "compra-propria": "Compra pelo próprio criador",
  "contas-associadas": "Contas associadas",
  "dois-pagamentos": "Dois pagamentos no mesmo pedido",
  "ordem-invertida": "Reembolso anterior ao pagamento",
  "reembolso-excedente": "Reembolso maior que o pagamento",
  "reembolso-integral": "Reembolso integral",
  "reembolso-parcial": "Reembolso parcial",
  "reembolso-sem-venda": "Reembolso sem pagamento registrado",
  "trafego-atipico": "Volume de cliques atípico",
  venda: "Venda regular",
};
const caseLabel = (id: string) => caseNames[id.replace(/^lab-/, "")] ?? id;
const demoOrder = "lab-comissao-apos-reembolso";
const displayAmounts = (text: string) =>
  text.replace(/(-?\d+) centavos/g, (_, amount: string) => money(Number(amount)));
const path = (id: string) => "/api/orders/" + encodeURIComponent(id);
function Order({ id, open }: { id: string; open:(id:string)=>void }) {
  const [view, choose] = useState("Movimentações");
  const [question, setQuestion] = useState<string>();
  const [data, setData] = useState<Case>(),
    [answer, setAnswer] = useState<Answer>(),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    api<Case>(path(id))
      .then(setData)
      .catch((e) => setError(e.message));
  }, [id]);
  async function submit(
    ev: React.FormEvent<HTMLFormElement>,
    kind: "review" | "explanation",
  ) {
    ev.preventDefault();
    if (!data) return;
    const fields = Object.fromEntries(new FormData(ev.currentTarget));
    setBusy(true);
    setError("");
    setAnswer(undefined);
    try {
      if (kind === "review") {
        await api(path(id) + "/review", { ...fields, revision: data.revision });
        setData(await api<Case>(path(id)));
      } else setAnswer(await api<Answer>(path(id) + "/explanation", fields));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  const missed = data?.status==="conciliado" && Object.keys(data.lab_checks??{}).length>0;
  const hasRefund = data?.events.some(event => event.event_type === "order_refunded");
  const eventQuestion = hasRefund ? "Qual evento comprova o reembolso?" : "Qual evento confirma o pagamento do pedido?";
  const suggestions = [
    missed ? "Por que a regra liberou este pedido?" : "O que há de errado com o pedido?",
    eventQuestion,
    data?.payout ? "Qual é a situação do repasse?" : "Qual é o saldo do pedido?",
  ];
  return (
    <>
      {error && <p role="alert">{error}</p>}
      {!data && !error && <p role="status">Buscando os registros do pedido…</p>}
      {data && (
        <>
          <article className="verdict"><div><span className={missed||data.status==="revisar"&&!data.review?"pill amber":"pill"}>{missed?"Problema sem alerta":data.review?"Revisão registrada":data.status==="revisar"?"Revisão necessária":"Conciliado"}</span>
            <h2>{missed?"A regra liberou. O cenário esperava revisão.":data.attribution && data.attribution.expected_minor!==data.attribution.posted_minor
              ? money(Math.abs(data.attribution.posted_minor-data.attribution.expected_minor))+" de diferença na comissão"
              : data.status==="revisar"?"Este pedido precisa de conferência":"A regra liberou este pedido"}</h2>
            <p>{data.attribution ? "A oferta prevê "+money(data.attribution.expected_minor)+". O valor registrado para "+data.attribution.attributed_creator+" é "+money(data.attribution.posted_minor)+"."
                : "Consulte os pagamentos e reembolsos abaixo. Este pedido não possui uma oferta de comissão vinculada."}</p>
            {missed && <><p>A regra inicial conferiu os lançamentos. Estas condições do laboratório ficaram fora da conferência:</p>
              <ul>{Object.values(data.lab_checks??{}).map(reason=><li key={reason}>{reason}</li>)}</ul></>}
            </div><small>{id}</small></article>
          <dl className="order-values">
            <div><dt>Venda</dt><dd>{money(data.paid_minor)}</dd></div>
            <div><dt>Reembolso</dt><dd>{money(data.refunded_minor)}</dd></div>
            <div><dt>Comissão prevista</dt><dd>{data.attribution ? money(data.attribution.expected_minor) : "Sem oferta"}</dd></div>
            <div><dt>Comissão registrada</dt><dd>{data.attribution ? money(data.attribution.posted_minor) : "Sem oferta"}</dd></div>
            <div className="difference"><dt>Diferença</dt><dd>{data.attribution ? money(data.attribution.posted_minor - data.attribution.expected_minor) : "Não se aplica"}</dd></div>
          </dl>
          {data.payout && <section className="workspacepanel">
            <h3>Repasse ao criador</h3>
            <p>Último registro da simulação: <strong>{data.payout[data.payout.length-1].label}</strong></p>
            <ol className="eventline">{data.payout.map(record=>
              <li key={record.id}><strong>{record.date.split("-").reverse().join("/")} · {record.label} · {money(record.amount_minor)}</strong>
                <p>{record.detail}</p><small>Registro {record.id}</small>
              </li>)}</ol>
          </section>}
          {id === demoOrder && view === "Movimentações" &&
            <button onClick={() => choose("Perguntar sobre o pedido")}>Consultar evidência do reembolso →</button>}
          <div className="switcher" aria-label="Detalhes do pedido">{["Movimentações","Perguntar sobre o pedido","Pedidos relacionados",...(data.status==="revisar"||data.review?["Revisar alerta"]:[])].map(name=><button key={name} aria-pressed={view===name} onClick={()=>choose(name)}>{name}</button>)}</div>
          {view==="Pedidos relacionados" && <Related id={id} open={open}/>}
          {view==="Movimentações" && <section className="workspacepanel">
          <p>{hasRefund ? "Saldo após reembolso" : "Saldo registrado"} <strong>{money(data.net_minor)}</strong></p>
          <h3>Histórico do pedido</h3>
          <ol className="eventline">
            {data.events.map((e) => (
              <li key={e.event_id}>
                <b>
                  {e.event_type === "order_paid" ? "Pagamento" : "Reembolso"} ·{" "}
                  {money(e.amount_minor)}
                </b>
                <br />
                {new Date(e.occurred_at_utc).toLocaleString("pt-BR")} · Registro {e.event_id}
              </li>
            ))}
          </ol>
          {!!data.reasons.length && (
            <p>
              Motivos para revisão ·{" "}
              {data.reasons.map((x) => x.replaceAll("_", " ")).join(", ")}
            </p>
          )}
          </section>}
          {view==="Revisar alerta" && (data.review ? (
            <section className="workspacepanel" role="status">
              <h3>{data.review.decision === "confirmado" ? "Alerta confirmado" : "Alerta descartado"}</h3>
              <p>Decisão de {data.review.reviewer}</p>
              <p>{data.review.note}</p>
            </section>
          ) : (
            data.status === "revisar" && (
              <form onSubmit={(e) => submit(e, "review")}>
                <h3>Revisão humana</h3>
                <label>
                  Responsável
                  <input required name="reviewer" maxLength={80} />
                </label>
                <label>
                  Decisão
                  <select name="decision">
                    <option value="confirmado">Confirmar alerta</option>
                    <option value="descartado">Descartar alerta</option>
                  </select>
                </label>
                <label>
                  Justificativa
                  <input required name="note" maxLength={500} />
                </label>
                <button disabled={busy}>Registrar revisão</button>
              </form>
            )
          ))}
          {view==="Perguntar sobre o pedido" && <><form onSubmit={(e) => submit(e, "explanation")}>
            <h3>Que registro explica este pedido?</h3><p>A resposta usa os eventos desta venda. Você pode perguntar sobre o pagamento, o reembolso ou a comissão.</p>
            <div className="question-options" aria-label="Sugestões de perguntas">
              {suggestions.map(suggestion=>
                <button type="button" key={suggestion} disabled={busy} aria-pressed={(question??eventQuestion)===suggestion}
                  onClick={()=>{setQuestion(suggestion);setAnswer(undefined)}}>{suggestion}</button>)}
            </div>
            <label>
              Pergunta
              <input
                name="question"
                value={question??eventQuestion}
                onChange={(event) => setQuestion(event.target.value)}
                required
                maxLength={400}
              />
            </label>
            <button disabled={busy}>{busy ? "Consultando…" : "Consultar"}</button>
          </form>
          {answer && (
            <section className="workspacepanel evidence-answer" aria-live="polite">
              <h3>Evidências do pedido</h3>
              <p>{displayAmounts(answer.message)}</p>
              {answer.case_finding && <p>{displayAmounts(answer.case_finding)}</p>}
              {answer.draft && <p>Seleção de evidências por IA · {answer.model}</p>}
              {answer.sources.map((s) => (
                <p key={s.id}>
                  {s.summary}{" "}
                  <a href={s.url}>
                    {s.id} · {s.section}
                  </a>
                </p>
              ))}
              {data.status === "revisar" && <button onClick={() => choose("Revisar alerta")}>
                {data.review ? "Ver decisão humana" : "Registrar decisão humana"} →
              </button>}
            </section>
          )}
          </>}
          <details><summary>Rastrear a origem dos registros</summary><Graph result={data}/></details>
        </>
      )}
    </>
  );
}
type ExperimentResult = {
  counts: Record<string, number>;
  missed_commission_minor: number;
};
type Experiment = {
  revision: string;
  finding: string;
  proposed_check: string;
  baseline: ExperimentResult;
  replay: ExperimentResult | null;
  review: null | { decision: string };
  evidence: Event[];
};
function RuleExperiment() {
  const [result, setResult] = useState<Experiment>(),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    api<Experiment>("/api/experiment")
      .then(setResult)
      .catch((e) => setError(e.message));
  }, []);
  async function decide(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!result) return;
    setBusy(true);
    try {
      setResult(
        await api<Experiment>("/api/experiment/review", {
          ...Object.fromEntries(new FormData(e.currentTarget)),
          revision: result.revision,
        }),
      );
      setError("");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <details>
      <summary>Teste complementar · confirmação de venda</summary>
      {!result && !error && <p role="status">Carregando o teste…</p>}
      {error && <p role="alert">{error}</p>}
      {result && (
        <>
          <div className="casegrid experiment-steps">
            <article className="casecard"><h3>O que passou sem alerta</h3><p>{result.finding}</p>
              <small>Registro {result.evidence[0].event_id}</small></article>
            <article className="casecard"><h3>O que será testado</h3><p>{result.proposed_check}</p>
              <small>A aprovação repete o teste com os mesmos pedidos fictícios.</small></article>
          </div>
          <div className="scroll-table experiment-table"><table><thead><tr><th scope="col">Indicador</th><th scope="col">Antes</th><th scope="col">Após aprovação</th></tr></thead>
          <tbody>
            <tr><th scope="row">Problemas sem alerta</th><td>{result.baseline.counts.fn}</td><td>{result.replay?.counts.fn??"—"}</td></tr>
            <tr><th scope="row">Alertas indevidos</th><td>{result.baseline.counts.fp}</td><td>{result.replay?.counts.fp??"—"}</td></tr>
            <tr><th scope="row">Comissão simulada sem alerta</th><td>{money(result.baseline.missed_commission_minor)}</td><td>{result.replay ? money(result.replay.missed_commission_minor) : "—"}</td></tr>
          </tbody></table></div>
          {result.review ? (
            <p role="status">{result.replay ? "Teste aprovado e executado." : "Proposta rejeitada. A nova rodada não foi executada."}</p>
          ) : (
            <form onSubmit={decide}>
              <h3>Registrar decisão humana</h3>
              <label>
                Revisor da regra
                <input required name="reviewer" maxLength={80} />
              </label>
              <label>
                Parecer
                <select name="decision">
                  <option value="confirmado">Aprovar para o laboratório</option>
                  <option value="descartado">Rejeitar proposta</option>
                </select>
              </label>
              <label>
                Motivo do parecer
                <input required name="note" maxLength={500} />
              </label>
              <button disabled={busy}>{busy ? "Registrando…" : "Registrar parecer"}</button>
            </form>
          )}
        </>
      )}
    </details>
  );
}
const validationViews = [
  {key:"todos", label:"Todos os casos"},
  {key:"tp", label:"Alertas corretos"},
  {key:"tn", label:"Pedidos regulares liberados"},
  {key:"fp", label:"Alertas indevidos"},
  {key:"fn", label:"Problemas sem alerta"},
];

function Validation({open}:{open:(id:string)=>void}) {
  const [scores, setScores] = useState<Evaluation>();
  const [error, setError] = useState("");
  const [filter, select] = useState("todos");
  useEffect(() => {
    api<Evaluation>("/api/validation").then(setScores).catch(e=>setError(e.message));
  }, []);
  const cases = scores?.cases.filter(c=>filter==="todos"||c.result===filter) ?? [];
  return <details><summary>Conferência dos 13 casos de referência</summary>
    {error && <p role="alert">{error}</p>}
    {!scores && !error && <p role="status">Carregando casos…</p>}
    {scores && <>
      <p>Compare a decisão da regra inicial com o resultado esperado de cada caso fictício.</p>
      <div className="validation-filters" aria-label="Filtrar casos de referência">
        {validationViews.map(({key,label})=><button key={key} type="button" aria-pressed={filter===key} onClick={()=>select(key)}>
          <strong>{key==="todos" ? scores.cases.length : scores.counts[key]}</strong>{label}
        </button>)}
      </div>
      <ul className="validation-list">
        {cases.map(c=><li key={c.name}>
          <div><strong>{caseLabel(c.name)}</strong>
            <small>{c.simulated_seconds_to_alert === null ? "Sem alerta" :
              c.simulated_seconds_to_alert === 0 ? "Alerta no primeiro evento" :
              `Alerta após ${c.simulated_seconds_to_alert} s simulados`}</small>
          </div>
          <span className={["tp","tn"].includes(c.result)?"pill":"pill amber"}>
            {validationViews.find(item=>item.key===c.result)?.label}
          </span>
          <button type="button" onClick={()=>open("lab-"+c.name)}>Abrir pedido ↗</button>
        </li>)}
      </ul>
      {cases.length===0 && <p role="status">Nenhum caso neste grupo.</p>}
    </>}
  </details>
}

type Location = {screen:keyof typeof areas; order:string; depth:number};
const initialLocation: Location = {screen:"Visão geral", order:"", depth:0};

function App() {
  const [location, setLocation] = useState<Location>(() => history.state?.sentinel ?? initialLocation);
  const {screen, order, depth} = location;
  const main = useRef<HTMLElement>(null);
  const navigated = useRef(false);
  const [ids, setIds] = useState<string[]>([]);
  const [error, setError] = useState("");
  const id = order || (ids.includes(demoOrder) ? demoOrder : ids[0] ?? "");

  function navigate(next: keyof typeof areas, nextOrder = id) {
    if (next === screen && nextOrder === id) return;
    navigated.current = true;
    const entry = {screen:next, order:nextOrder, depth:depth+1};
    history.pushState({sentinel:entry}, "");
    setLocation(entry);
  }
  function show(next: keyof typeof areas) { navigate(next); }
  function explore(nextOrder:string) { navigate("TrustGraph", nextOrder); }
  function select(nextOrder:string) {
    const entry = {...location, order:nextOrder};
    history.replaceState({sentinel:entry}, "");
    setLocation(entry);
  }
  useEffect(() => {
    if (!history.state?.sentinel) history.replaceState({sentinel:initialLocation}, "");
    function backOrForward(event:PopStateEvent) {
      navigated.current = true;
      setLocation(event.state?.sentinel ?? initialLocation);
    }
    window.addEventListener("popstate", backOrForward);
    return () => window.removeEventListener("popstate", backOrForward);
  }, []);
  useEffect(() => {
    if (!navigated.current) return;
    window.scrollTo(0, 0);
    main.current?.focus({preventScroll:true});
  }, [screen, depth]);
  useEffect(() => {
    api<string[]>("/api/orders")
      .then(setIds)
      .catch((e) => setError(e.message));
  }, []);
  return (
    <>
      <aside className="rail"><div className="brand"><span aria-hidden="true">S</span> Sentinel</div><p>Central de comissões</p>
        <nav aria-label="Navegação principal">{(Object.keys(areas) as (keyof typeof areas)[]).map(name=><button key={name} aria-current={screen===name?"page":undefined} onClick={()=>show(name)}>{areas[name]}</button>)}</nav>
      </aside><main ref={main} tabIndex={-1} aria-label={areas[screen]}><header className="topline"><span>YouShop / Operações</span><span>● Dados de demonstração</span></header>
        {depth>0 && <button className="back-link" type="button" onClick={()=>history.back()}>← Voltar</button>}
        {screen==="Visão geral" && <><h1>Resumo da operação</h1><Example open={()=>explore(demoOrder)}/><Overview evaluate={()=>show("Defesa")}/><Dashboard open={explore}/></>}
        {screen==="Ajuda" && <Guide/>}{screen==="Simulação" && <Simulation open={explore} evaluate={()=>show("Defesa")}/>}
        {screen==="Defesa" && <><Defense/><Validation open={explore}/><RuleExperiment/></>}{screen==="Creator" && <Creator open={explore}/>}
        {screen==="TrustGraph" && <><h1>Conferir pedido</h1><p>Veja o que foi pago, quanto voltou ao comprador e qual comissão ficou registrada.</p>
        {error && <p role="alert">{error}</p>}
        <label>
          Pedido sintético
          <select value={id} onChange={(e) => select(e.target.value)}>
            {(id && !ids.includes(id) ? [id,...ids] : ids).map((v) => (
              <option key={v} value={v}>{caseLabel(v)}</option>
            ))}
          </select>
        </label>
        {ids.includes(demoOrder) && id !== demoOrder && (
          <button onClick={() => select(demoOrder)}>Abrir exemplo de comissão após reembolso</button>
        )}
        {id && <Order key={id} id={id} open={explore}/>}</>}
        <footer>
          <a href="/docs">Referência técnica para desenvolvedores</a>
        </footer>
      </main>
    </>
  );
}
createRoot(document.getElementById("app")!).render(<App />);

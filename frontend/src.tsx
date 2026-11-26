import {areas, Guide, Example} from "./guide";
import {api, money} from "./client";
import {Overview, Simulation, Defense, Creator, Graph} from "./lab";
import React, { useEffect, useState } from "react";
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
function Order({ id }: { id: string }) {
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
  return (
    <>
      {error && <p role="alert">{error}</p>}
      {data && (
        <>
          <h2>Resultado da conferência</h2><small>Pedido {id}</small>
          <p>
            {data.status === "revisar" ? "Revisão necessária" : "Conciliado"}
          </p>
          <section className="totals">
            {[
              ["Pago", data.paid_minor],
              ["Reembolsado", data.refunded_minor],
              ["Saldo do pedido", data.net_minor],
            ].map(([k, v]) => (
              <div key={k}>
                <small>{k}</small>
                <strong>{money(Number(v))}</strong>
              </div>
            ))}
          </section>
          <h3>Histórico de pagamentos e reembolsos</h3>
          <ol>
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
          {data.attribution && (
            <section>
              <h3>Quem recebe a comissão?</h3>
              <p>
                {[
                  data.attribution.product,
                  data.attribution.offer,
                  data.attribution.link,
                  data.attribution.creator,
                ].join(" → ")}
              </p>
              <p>
                Crédito atribuído a {data.attribution.attributed_creator}.
                Comissão prevista {money(data.attribution.expected_minor)} ·
                registrada {money(data.attribution.posted_minor)}.
              </p>
            </section>
          )}
          {!!data.reasons.length && (
            <p>
              Motivos para revisão ·{" "}
              {data.reasons.map((x) => x.replaceAll("_", " ")).join(", ")}
            </p>
          )}
          {data.review ? (
            <p>
              Revisão registrada por {data.review.reviewer} ·{" "}
              {data.review.decision} · {data.review.note}
            </p>
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
          )}
          <form onSubmit={(e) => submit(e, "explanation")}>
            <h3>Consultar evidências</h3>
            <label>
              Pergunta
              <input
                name="question"
                defaultValue={id === demoOrder ? "Por que a comissão ficou em revisão após o reembolso do pedido?" : "Qual evento confirma o pagamento do pedido?"}
                required
                maxLength={400}
              />
            </label>
            <button disabled={busy}>Consultar</button>
          </form>
          {answer && (
            <section aria-live="polite">
              <h4>Resposta para {id}</h4>
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
            </section>
          )}
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
      <summary>Experimento de regra · confirmação de venda</summary>
      {error && <p role="alert">{error}</p>}
      {result && (
        <>
          <p>
            {result.finding} Evidência: {result.evidence[0].event_id}.
          </p>
          <p>{result.proposed_check}</p>
          <p>
            Antes da revisão: {result.baseline.counts.fn} caso esperado sem
            alerta · comissão simulada{" "}
            {money(result.baseline.missed_commission_minor)}.
          </p>
          {result.review ? (
            <p>Decisão registrada · {result.review.decision}</p>
          ) : (
            <form onSubmit={decide}>
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
              <button disabled={busy}>Registrar parecer</button>
            </form>
          )}
          {result.replay && (
            <p>
              Após a repetição: {result.replay.counts.fn} falso(s) negativo(s),{" "}
              {result.replay.counts.fp} falso(s) positivo(s),{" "}
              {money(result.replay.missed_commission_minor)} de comissão
              simulada sem alerta.
            </p>
          )}
        </>
      )}
    </details>
  );
}
function App() {
  const [screen, show] = useState<keyof typeof areas>("Visão geral");
  function explore(order:string){select(order);show("TrustGraph")}
  const [ids, setIds] = useState<string[]>([]),
    [id, select] = useState(""),
    [scores, setScores] = useState<Evaluation>(),
    [error, setError] = useState("");
  useEffect(() => {
    Promise.all([
      api<string[]>("/api/orders"),
      api<Evaluation>("/api/validation"),
    ])
      .then(([list, results]) => {
        setIds(list);
        select(list.includes(demoOrder) ? demoOrder : list[0]);
        setScores(results);
      })
      .catch((e) => setError(e.message));
  }, []);
  return (
    <>
      <aside className="rail"><div className="brand"><span aria-hidden="true">S</span> Sentinel</div><p>Central de comissões</p>
        <nav aria-label="Navegação principal">{(Object.keys(areas) as (keyof typeof areas)[]).map(name=><button key={name} aria-current={screen===name?"page":undefined} onClick={()=>show(name)}>{areas[name]}</button>)}</nav>
      </aside><main><header className="topline"><span>YouShop / Operações</span><span>● Dados de demonstração</span></header>
        {screen==="Visão geral" && <><h1>Resumo da operação</h1><Example open={()=>explore(demoOrder)}/><Overview/></>}
        {screen==="Ajuda" && <Guide/>}{screen==="Simulação" && <Simulation open={explore}/>}
        {screen==="Defesa" && <><Defense/><RuleExperiment/></>}{screen==="Creator" && <Creator open={explore}/>}
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
        {id && <><Order key={id} id={id}/><details><summary>Rastrear a origem dos registros</summary><Graph key={"graph"+id} id={id}/></details></>}
        {scores && (
          <details>
            <summary>
              Validação defensiva · {scores.cases.length} cenários
            </summary>
            <p>
              Alertas esperados detectados: {scores.counts.tp} · Falsos
              positivos: {scores.counts.fp} · Falsos negativos:{" "}
              {scores.counts.fn}
            </p>
            <ul>
              {scores.cases.map((c) => (
                <li key={c.name}>
                  {caseLabel(c.name)} ·{" "}
                  {["tp", "tn"].includes(c.result)
                    ? "conforme esperado"
                    : "divergente"}
                  {c.simulated_seconds_to_alert !== null &&
                    " · primeiro alerta em " +
                      c.simulated_seconds_to_alert +
                      " s simulados"}
                </li>
              ))}
            </ul>
          </details>
        )}
        <RuleExperiment /></>}
        <footer>
          <a href="/docs">Referência técnica para desenvolvedores</a>
        </footer>
      </main>
    </>
  );
}
createRoot(document.getElementById("app")!).render(<App />);

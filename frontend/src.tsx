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
type Case = {
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
  message: string;
  draft?: string;
  sources: { id: string; section: string; url: string; summary: string }[];
};
type Evaluation = {
  counts: Record<string, number>;
  cases: { name: string; result: string }[];
};
const money = (n: number) =>
  (n / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const path = (id: string) => "/api/orders/" + encodeURIComponent(id);
async function api<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(
    url,
    body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
  if (!res.ok) {
    const e = await res.json();
    throw Error(
      typeof e.detail === "string" ? e.detail : "Confira os dados informados.",
    );
  }
  return res.json();
}
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
          <h2>{id}</h2>
          <p>
            {data.status === "revisar" ? "Revisão necessária" : "Conciliado"} ·{" "}
            {data.rule}
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
          <h3>Eventos sintéticos</h3>
          <ol>
            {data.events.map((e) => (
              <li key={e.event_id}>
                <b>
                  {e.event_type === "order_paid" ? "Pagamento" : "Reembolso"} ·{" "}
                  {money(e.amount_minor)}
                </b>
                <br />
                {e.event_id} · {e.occurred_at_utc} · {e.fixture_version}
              </li>
            ))}
          </ol>
          {data.attribution && (
            <section>
              <h3>Atribuição da oferta fictícia</h3>
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
                defaultValue="Qual evento confirma o pagamento do pedido?"
                required
                maxLength={400}
              />
            </label>
            <button disabled={busy}>Consultar</button>
          </form>
          {answer && (
            <section aria-live="polite">
              <p>{answer.message}</p>
              {answer.draft && <p>Rascunho gerado por IA · {answer.draft}</p>}
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
function App() {
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
        select(list[0]);
        setScores(results);
      })
      .catch((e) => setError(e.message));
  }, []);
  return (
    <>
      <header>YouShop Sentinel AI</header>
      <main>
        <h1>Conciliação de pedidos</h1>
        {error && <p role="alert">{error}</p>}
        <label>
          Pedido sintético
          <select value={id} onChange={(e) => select(e.target.value)}>
            {ids.map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </label>
        {id && <Order key={id} id={id} />}
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
                  {c.name} ·{" "}
                  {["tp", "tn"].includes(c.result)
                    ? "conforme esperado"
                    : "divergente"}
                </li>
              ))}
            </ul>
          </details>
        )}
        <footer>
          <a href="/docs">Documentação da API</a>
        </footer>
      </main>
    </>
  );
}
createRoot(document.getElementById("app")!).render(<App />);

import json
import os
import re
import unicodedata
from http.client import HTTPConnection, HTTPException
from itertools import islice

REFERENCES = (
    ("YS-REFUND-01",
     "O guia descreve a solicitação de reembolso de um pedido pelo relatório de vendas.",
     "https://ajuda.youshop.co/guides/lWitm85hA0nT9JiVZFsj", "Etapas 1 a 7"),
    ("YS-TERMS-01",
     "A cláusula 12.3 trata da compra pelo próprio link nas condições descritas nos termos.",
     "https://www.youshop.co/termosepoliticas", "Cláusula 12.3"),
    ("YS-CREATORS-01",
     "O guia descreve links de divulgação e a comissão exibida em cada oferta.",
     "https://ajuda.youshop.co/guides/IQ2WaPblIMMUqNhDSKdY", "Etapas 13 e 23"),
    ("YS-WEBHOOK-01",
     "O guia descreve eventos de checkout e confirmação de pagamento de pedidos.",
     "https://ajuda.youshop.co/guides/1472b4bf-e3a3-485a-a396-2cd5c9ee9d95", "Etapas 21 e 22"),
)


def tokens(text):
    normalized = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    return set(re.findall(r"[a-z]+", normalized))


DEFAULT_MODEL = "sentinel-qwen-local"


def explain(case, question, *, use_model=None, model=None):
    words = tokens(question)
    answer = dict(sources=[], revision=case["revision"], mode="evidencia_insuficiente",
                  event_ids=[event["event_id"] for event in case["events"]],
                  citation_ids=[], message="As evidências locais não respondem à pergunta.")
    if words & tokens("saque saques retirada retiradas withdrawal"):
        answer["message"] = "Não há evidência local para determinar a data do próximo saque."
        return answer

    refund = words & tokens("reembolso reembolsos reembolsado reembolsada estorno estornado devolução")
    payment = words & tokens("pagamento pagamentos pago paga")
    commission = words & tokens("comissão comissões")
    review = words & tokens("revisão revisar divergência divergente")
    how_to_refund = refund and words & tokens("solicitar solicito pedir procedimento guia")
    offer = case["attribution"]
    findings = {}
    if offer and (commission or review):
        expected, posted = offer["expected_minor"], offer["posted_minor"]
        finding = (f"A regra da oferta fictícia prevê {expected} centavos de comissão. "
                   f"O livro-razão registrou {posted} centavos.")
        if "comissao_divergente" in offer["reasons"]:
            finding += f" A divergência de {abs(posted - expected)} centavos exige revisão humana."
        findings[offer["rule"]] = finding
        answer["case_finding"] = f"{finding} [{offer['rule']}]"

    ledger = {}
    if words & tokens("saldo líquido"):
        ledger[case["rule"]] = f"O saldo líquido do pedido sintético é {case['net_minor']} centavos."

    history = words & tokens("histórico")
    for event in case["events"]:
        kind = event["event_type"]
        if kind == "order_refunded" and (history or (refund and not how_to_refund)):
            action = "reembolso"
        elif kind == "order_paid" and (history or (payment and not refund)):
            action = "pagamento"
        else:
            continue
        ledger[event["event_id"]] = (
            f"O pedido sintético registra {action} de {event['amount_minor']} centavos "
            f"em {event['occurred_at_utc']}."
        )
    findings.update(ledger)

    source_ids = set()
    if how_to_refund:
        source_ids.add("YS-REFUND-01")
    if words & tokens("autocompra"):
        source_ids.add("YS-TERMS-01")
    if not (review or refund or (commission and offer)) and words & tokens("oferta afiliação afiliado creator"):
        source_ids.add("YS-CREATORS-01")
    if words & tokens("webhook checkout"):
        source_ids.add("YS-WEBHOOK-01")
    sources = [dict(id=key, summary=summary, url=url, section=section, accessed="2026-11-23")
               for key, summary, url, section in REFERENCES if key in source_ids]
    if not (findings or sources):
        return answer

    answer.update(mode="evidencia_local", sources=sources,
                  citation_ids=[*findings, *(source["id"] for source in sources)],
                  message=" ".join(f"{fact} [{key}]" for key, fact in ledger.items()) or (
                      "Resultado da conciliação do pedido." if findings else "Referências locais para a consulta."
                  ))
    enabled = os.getenv("SENTINEL_LOCAL_AI") == "1" if use_model is None else use_model
    if not enabled:
        return answer

    model = model or os.getenv("SENTINEL_OLLAMA_MODEL", "").strip() or DEFAULT_MODEL
    facts = {**findings, **{source["id"]: source["summary"] for source in sources}}
    answer["model"] = model
    try:
        ids = select_citations(question, dict(islice(facts.items(), 12)), model)
    except (ValueError, OSError, HTTPException):
        answer["generation_status"] = "error"
        return answer
    answer.update(generation_status="selected" if ids else "empty", model_citation_ids=ids)
    if ids:
        answer.update(mode="rascunho_ia", sources=[source for source in sources if source["id"] in ids],
                      citation_ids=list(dict.fromkeys([*findings, *ids])),
                      draft=" ".join(f"{facts[key]} [{key}]" for key in ids))
    return answer


def select_citations(question, facts, model):
    context = dict(question=question, facts=facts)
    instructions = ("Selecione até três IDs dos fatos que respondem à pergunta. "
                    "Retorne uma lista vazia "
                    "quando os fatos não responderem. Use exatamente os IDs fornecidos.")
    schema = {"type": "object", "properties": {"ids": {"type": "array", "maxItems": 3,
              "items": {"type": "string", "enum": list(facts)}}}, "required": ["ids"],
              "additionalProperties": False}
    request = dict(model=model, temperature=0, max_tokens=180, stream=False,
                   reasoning_effort="none",
                   response_format={"type": "json_schema", "json_schema": {"name": "evidence", "schema": schema}},
                   messages=[
        dict(role="system", content=instructions),
        dict(role="user", content=json.dumps(context, ensure_ascii=False)),
    ])
    connection = HTTPConnection("127.0.0.1", 11434, timeout=90)
    try:
        connection.request("POST", "/v1/chat/completions", json.dumps(request), {"Content-Type": "application/json"})
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError("Modelo local indisponível.")
        raw = response.read(16385)
        if len(raw) > 16384:
            raise ValueError("Resposta excede o limite.")
        payload = json.loads(raw)
        try:
            draft = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("Resposta incompleta.") from exc
        if not isinstance(draft, str) or not draft.strip():
            raise ValueError("Resposta incompleta.")
        selection = json.loads(draft)
        ids = selection.get("ids") if isinstance(selection, dict) and selection.keys() == {"ids"} else None
        if not isinstance(ids, list) or len(ids) > 3 or any(not isinstance(i, str) or i not in facts for i in ids):
            raise ValueError("Referências inválidas.")
        return list(dict.fromkeys(ids))
    finally:
        connection.close()

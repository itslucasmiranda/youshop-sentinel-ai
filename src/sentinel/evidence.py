import json
import os
import re
import unicodedata
from http.client import HTTPConnection

REFERENCES = (
    ("YS-REFUND-01", "reembolso solicitar estorno devolução",
     "O guia descreve a solicitação de reembolso de um pedido pelo relatório de vendas.",
     "https://ajuda.youshop.co/guides/lWitm85hA0nT9JiVZFsj", "Etapas 1 a 7"),
    ("YS-TERMS-01", "autocompra próprio dispositivo rede",
     "A cláusula 12.3 trata da compra pelo próprio link nas condições descritas nos termos.",
     "https://www.youshop.co/termosepoliticas", "Cláusula 12.3"),
    ("YS-CREATORS-01", "oferta comissão afiliado creator link afiliação",
     "O guia descreve links de divulgação e a comissão exibida em cada oferta.",
     "https://ajuda.youshop.co/guides/IQ2WaPblIMMUqNhDSKdY", "Etapas 13 e 23"),
    ("YS-WEBHOOK-01", "evento pagamento pago checkout pedido webhook",
     "O guia descreve eventos de checkout e confirmação de pagamento de pedidos.",
     "https://ajuda.youshop.co/guides/1472b4bf-e3a3-485a-a396-2cd5c9ee9d95", "Etapas 21 e 22"),
)


def tokens(text):
    normalized = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    return set(re.findall(r"[a-z]+", normalized))


def explain(case, question):
    words = tokens(question)
    sources = [dict(id=key, summary=summary, url=url, section=section, accessed="2026-11-23")
               for key, tags, summary, url, section in REFERENCES if words & tokens(tags)]
    answer = dict(sources=sources, revision=case["revision"], mode="evidencia_local",
                  event_ids=[e["event_id"] for e in case["events"]],
                  message="As fontes disponíveis não estabelecem uma política de cálculo ou estorno de comissão.")
    if not sources:
        answer.update(mode="evidencia_insuficiente", message="Nenhuma referência local corresponde à consulta.")
        return answer
    facts = {s["id"]: s["summary"] for s in sources}
    if words & tokens("saldo líquido total"):
        facts[case["rule"]] = f"O saldo líquido do pedido sintético é {case['net_minor']} centavos."
    offer = case["attribution"]
    if offer and words & tokens("comissão comissões oferta"):
        facts[offer["rule"]] = (
            f"A regra da oferta fictícia prevê {offer['expected_minor']} centavos de comissão "
            f"sobre o saldo remanescente. O registro contém {offer['posted_minor']} centavos."
        )
        answer["case_finding"] = facts[offer["rule"]] + f" [{offer['rule']}]"
    for event in case["events"]:
        action = "pagamento" if event["event_type"] == "order_paid" else "reembolso"
        if action in words or words & tokens("histórico eventos"):
            facts[event["event_id"]] = f"O pedido sintético registra {action} de {event['amount_minor']} centavos."
    if os.getenv("SENTINEL_LOCAL_AI") != "1":
        return answer
    context = dict(question=question, facts=facts)
    instructions = ("Selecione até três IDs dos fatos que respondem à pergunta. Inclua a referência "
                    "documental e o evento relevante quando disponíveis. Retorne uma lista vazia "
                    "quando os fatos não responderem. Use exatamente os IDs fornecidos.")
    schema = {"type": "object", "properties": {"ids": {"type": "array", "maxItems": 3,
              "items": {"type": "string", "enum": list(facts)}}}, "required": ["ids"],
              "additionalProperties": False}
    request = dict(model="sentinel-qwen-local", temperature=0, max_tokens=180,
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
        payload = json.load(response)
        choices = payload.get("choices") or []
        draft = choices[0].get("message", {}).get("content") if choices else None
        if not isinstance(draft, str) or not draft.strip():
            raise ValueError("Resposta incompleta.")
        selection = json.loads(draft)
        ids = selection.get("ids") if isinstance(selection, dict) else None
        if not isinstance(ids, list) or len(ids) > 3 or any(not isinstance(i, str) or i not in facts for i in ids):
            raise ValueError("Referências inválidas.")
        if ids:
            answer.update(mode="rascunho_ia", model="sentinel-qwen-local",
                          draft=" ".join(f"{facts[i]} [{i}]" for i in dict.fromkeys(ids)))
        else:
            answer.update(mode="evidencia_insuficiente", message="A seleção do modelo não encontrou resposta fundamentada.")
    finally:
        connection.close()
    return answer

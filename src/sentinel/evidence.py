import json
import os
import re
import unicodedata
from http.client import HTTPConnection

REFERENCES = (
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
    if os.getenv("SENTINEL_LOCAL_AI") != "1":
        return answer
    context = dict(question=question, reconciliation=case, references=sources)
    instructions = ("Responda em português em até três frases. Use apenas os eventos sintéticos "
                    "e as referências fornecidas. Cite seus IDs. Informe lacunas. "
                    "Não proponha ações financeiras nem presuma regras de comissão.")
    request = dict(temperature=0, max_tokens=180, messages=[
        dict(role="system", content=instructions),
        dict(role="user", content=json.dumps(context, ensure_ascii=False)),
    ])
    connection = HTTPConnection("127.0.0.1", 18765, timeout=90)
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
        answer.update(mode="rascunho_ia", draft=draft)
    finally:
        connection.close()
    return answer

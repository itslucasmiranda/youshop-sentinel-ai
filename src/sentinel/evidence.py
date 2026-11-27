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

REVIEW_REASONS = {
    "pagamento_ausente": "Nenhum pagamento aparece no histórico.",
    "pagamentos_multiplos": "Há mais de um pagamento registrado para o pedido.",
    "reembolso_excedente": "O total devolvido supera o valor pago.",
    "sequencia_inconclusiva": "O primeiro reembolso aparece antes ou no mesmo instante do primeiro pagamento.",
    "versoes_incompativeis": "Os registros vieram de versões diferentes dos dados de teste.",
    "comprador_igual_ao_criador": "O comprador e o criador têm o mesmo identificador.",
    "contas_associadas": "O caso informa mais de uma conta vinculada ao criador.",
    "atribuicao_divergente": "O crédito foi lançado para um criador diferente do associado ao link.",
    "trafego_atipico": "O volume de cliques supera o limite da regra fictícia.",
}


def diagnose(case):
    offer = case["attribution"]
    reasons = case["reasons"]
    findings = []
    if "comissao_divergente" in reasons and offer:
        expected, posted = offer["expected_minor"], offer["posted_minor"]
        findings.append(f"A comissão prevista é de {expected} centavos, mas foram registrados "
                        f"{posted} centavos. A diferença é de {abs(posted - expected)} centavos.")
        if case["paid_minor"] > 0 and case["net_minor"] == 0:
            findings.append(f"O pagamento de {case['paid_minor']} centavos foi reembolsado integralmente.")
    findings.extend(REVIEW_REASONS[reason] for reason in reasons if reason in REVIEW_REASONS)
    if not reasons:
        if case.get("lab_checks"):
            findings.append("A regra inicial liberou o pedido porque os valores conferem. "
                            "O cenário esperava revisão por condições que essa regra ainda não verifica.")
            findings.extend(case["lab_checks"].values())
            return " ".join(findings), [case["rule"], offer["rule"], *[e["event_id"] for e in case["events"]]]
        findings.append("A regra atual não sinalizou divergências neste pedido.")
        if not offer:
            findings.append("O pedido não tem oferta vinculada para conferir a comissão.")
    citations = [case["rule"], *(event["event_id"] for event in case["events"])]
    if offer:
        citations.append(offer["rule"])
    return " ".join(findings), citations


def order_topics(case):
    offer = case["attribution"]
    review = case.get("review")
    events = case["events"]
    diagnosis, _ = diagnose(case)
    return {
        "diagnostico": ("Motivos do alerta ou situação do pedido", diagnosis),
        "resumo": ("Resumo do pedido e dos valores",
                   f"Neste pedido, foram {case['paid_minor']} centavos pagos, "
                   f"{case['refunded_minor']} centavos devolvidos e saldo de {case['net_minor']} centavos. "
                   f"{diagnosis}"),
        "valores": ("Totais de pagamento, reembolso e saldo",
                    f"O total pago foi de {case['paid_minor']} centavos, o total devolvido foi de "
                    f"{case['refunded_minor']} centavos e o saldo ficou em {case['net_minor']} centavos."),
        "historico": ("Histórico, horário e identificadores das movimentações",
                      " ".join(
                          f"{'Pagamento' if e['event_type'] == 'order_paid' else 'Reembolso'} de "
                          f"{e['amount_minor']} centavos em {e['occurred_at_utc']} [{e['event_id']}]."
                          for e in events)),
        "atribuicao": ("Quem comprou ou divulgou, produto, link e atribuição de crédito",
                       (f"O criador associado à divulgação é {offer['creator']}. O crédito foi lançado "
                        f"para {offer['attributed_creator']}. Comprador: {offer['buyer']}. "
                        f"Produto: {offer['product']}. Link de divulgação: {offer['link']}."
                        if offer else "O pedido não tem vínculo com um criador, produto ou link no registro local.")),
        "oferta": ("Oferta, taxa e valores de comissão",
                   (f"A oferta {offer['offer']} aplica {offer['rate_bps'] / 100:g}% sobre o saldo após reembolsos. "
                    f"A comissão prevista é de {offer['expected_minor']} centavos e a registrada é de "
                    f"{offer['posted_minor']} centavos."
                    if offer else "O pedido não tem oferta vinculada para calcular a comissão.")),
        "parecer": ("Decisão humana, responsável e justificativa",
                    (f"Decisão: alerta {review['decision']}. Responsável: {review['reviewer']}. "
                     f"Justificativa: {review['note']}" if review else
                     "Ainda não há decisão humana registrada para este pedido.")),
    }


def topic_reply(answer, case, topics, keys, model=None):
    message = " ".join(topics[key][1] for key in keys)
    refs = [case["rule"]]
    if any(key in keys for key in ("diagnostico", "resumo", "valores", "historico")):
        refs.extend(answer["event_ids"])
    if case["attribution"] and any(key in keys for key in ("diagnostico", "resumo", "atribuicao", "oferta")):
        refs.append(case["attribution"]["rule"])
    answer.update(mode="evidencia_local", message=message, citation_ids=refs)
    if model:
        answer.update(model=model, generation_status="selected")
    return answer


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
    enabled = os.getenv("SENTINEL_LOCAL_AI") == "1" if use_model is None else use_model
    model = model or os.getenv("SENTINEL_OLLAMA_MODEL", "").strip() or DEFAULT_MODEL
    topics = order_topics(case)
    how_to_refund = refund and words & tokens("solicitar solicito pedir procedimento guia")
    if case.get("lab_checks") and not case["reasons"] and words & tokens(
        "liberou liberado liberada revisão revisar vigência vencida venceu confirmação"
    ):
        return topic_reply(answer, case, topics, ["diagnostico"])
    direct = []
    if words & tokens("parecer responsável justificativa revisor aprovou decidiu revisou decisão confirmou descartou"):
        direct.append("parecer")
    if words & tokens("quem qual quais quanto porcentagem taxa") and words & tokens(
        "criador criadora comprador compradora atribuído produto link divulgou comprou creditado taxa porcentagem"
    ):
        direct.append("oferta" if words & tokens("taxa porcentagem") else "atribuicao")
    if words & tokens("resumo resuma aconteceu situação status") and not refund and not payment:
        direct.append("resumo")
    if words & tokens("quanto total soma") and (payment or refund) and not commission and not how_to_refund:
        direct.append("valores")
    if direct:
        return topic_reply(answer, case, topics, direct)
    issue = words & tokens("errado errada erro erros problema problemas anomalia inconsistência irregularidade")
    if issue and words & tokens("pedido venda caso comissão alerta") and not refund and not payment:
        message, citations = diagnose(case)
        answer.update(mode="evidencia_local", message=message, citation_ids=citations)
        return answer
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
    if refund and not how_to_refund and not any(e["event_type"] == "order_refunded" for e in case["events"]):
        ledger[case["rule"]] = "Nenhum evento de reembolso consta no histórico deste pedido."
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
        if enabled:
            try:
                keys = select_citations(question, {key: data[0] for key, data in topics.items()}, model)
                if keys:
                    return topic_reply(answer, case, topics, keys, model)
            except (ValueError, OSError, HTTPException):
                pass
        answer["message"] += " Posso explicar valores, movimentações, criador, oferta ou revisão deste pedido."
        return answer

    answer.update(mode="evidencia_local", sources=sources,
                  citation_ids=[*findings, *(source["id"] for source in sources)],
                  message=" ".join(f"{fact} [{key}]" for key, fact in ledger.items()) or (
                      "Resultado da conciliação do pedido." if findings else "Referências locais para a consulta."
                  ))
    if not enabled:
        return answer

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

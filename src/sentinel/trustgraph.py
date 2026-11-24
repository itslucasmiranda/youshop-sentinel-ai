import hashlib
import json
from collections import Counter
from .affiliates import AFFILIATE_CASES, affiliate_evidence

RULE = "synthetic-ledger-v1"


def reconcile(events, journey=None):
    """Reconcile one synthetic order using integer BRL centavos."""
    evidence = sorted(events, key=lambda e: (e["occurred_at_utc"], e["event_id"]))
    payments = [e for e in evidence if e["event_type"] == "order_paid"]
    refunds = [e for e in evidence if e["event_type"] == "order_refunded"]
    paid = sum(e["amount_minor"] for e in payments)
    refunded = sum(e["amount_minor"] for e in refunds)
    reasons = []
    if len(payments) != 1:
        reasons.append("pagamento_ausente" if not payments else "pagamentos_multiplos")
    if refunded > paid:
        reasons.append("reembolso_excedente")
    if payments and refunds and refunds[0]["occurred_at_utc"] <= payments[0]["occurred_at_utc"]:
        reasons.append("sequencia_inconclusiva")
    if len({e["fixture_version"] for e in evidence}) > 1:
        reasons.append("versoes_incompativeis")
    attribution = affiliate_evidence(journey, paid-refunded) if journey else None
    if attribution:
        reasons.extend(attribution["reasons"])
    fingerprint = hashlib.sha256(json.dumps([RULE, evidence, attribution], sort_keys=True).encode()).hexdigest()
    return dict(rule=RULE, revision=fingerprint, events=evidence, paid_minor=paid,
                refunded_minor=refunded, net_minor=paid-refunded, currency="BRL",
                origin="synthetic", status="revisar" if reasons else "conciliado", reasons=reasons,
                attribution=attribution)


# Fixed, project-owned test cases. Labels are used only by the evaluator.
CASES = (
    ("venda", (("order_paid", 10000),), False),
    ("reembolso-integral", (("order_paid", 10000), ("order_refunded", 10000)), False),
    ("reembolso-parcial", (("order_paid", 10000), ("order_refunded", 4000)), False),
    ("reembolso-sem-venda", (("order_refunded", 3000),), True),
    ("reembolso-excedente", (("order_paid", 900), ("order_refunded", 1000)), True),
    ("dois-pagamentos", (("order_paid", 1000), ("order_paid", 1000)), True),
    ("ordem-invertida", (("order_refunded", 900), ("order_paid", 900)), True),
)


def scenario_events(name, entries):
    return [
        dict(event_id=f"lab-{name}-{i}", order_id=f"lab-{name}", event_type=kind,
             occurred_at_utc=f"2026-01-01T12:00:{i:02d}Z", amount_minor=amount,
             currency="BRL", origin="synthetic", fixture_version="ledger-lab-v1")
        for i, (kind, amount) in enumerate(entries)
    ]


def scenarios():
    for name, entries, expected in CASES:
        yield name, scenario_events(name, entries), None, expected
    for name, journey, expected in AFFILIATE_CASES:
        entries = [("order_paid", 10000)]
        if name == "comissao-apos-reembolso":
            entries.append(("order_refunded", 10000))
        yield name, scenario_events(name, entries), journey, expected


def evaluate():
    counts = Counter(dict(tp=0, tn=0, fp=0, fn=0))
    cases = []
    for name, events, journey, expected in scenarios():
        decision = reconcile(events, journey)
        actual = decision["status"] == "revisar"
        key = {(True, True): "tp", (False, False): "tn",
               (False, True): "fp", (True, False): "fn"}[expected, actual]
        counts[key] += 1
        cases.append(dict(name=name, expected_review=expected, actual_review=actual, result=key))
    return dict(counts=dict(counts), cases=cases, rule=RULE)

from dataclasses import replace

from .affiliates import BASE
from .trustgraph import evaluate, reconcile, scenario_events, scenarios

PROPOSAL = "synthetic-sale-evidence-v1"
FIXTURE = "venda-sem-comprovacao"


def experiment(approved=False):
    baseline = evaluate()
    counts = baseline["counts"].copy()
    # In this training contract the sale confirmation is an independent fact.
    # All existing offers include it. The holdout fixture deliberately lacks it.
    events = scenario_events(FIXTURE, [("order_paid", 10000)])
    journey = replace(BASE, sale_confirmed=False)
    case = reconcile(events, journey)
    base_alert = case["status"] == "revisar"
    counts["tp" if base_alert else "fn"] += 1
    result = dict(counts=counts, missed_commission_minor=journey.posted_minor if not base_alert else 0)
    replay = None
    if approved:
        after = dict(tp=0, tn=0, fp=0, fn=0)
        missed = 0
        for _, rows, offer, expected in [*scenarios(), (FIXTURE, events, journey, True)]:
            decision = reconcile(rows, offer)
            alert = decision["status"] == "revisar" or bool(offer and not offer.sale_confirmed)
            key = ("tp" if alert else "fn") if expected else ("fp" if alert else "tn")
            after[key] += 1
            if expected and not alert and offer:
                missed += offer.posted_minor
        replay = dict(counts=after, missed_commission_minor=missed)
    return dict(proposal=PROPOSAL, scenario=FIXTURE, baseline=result, replay=replay,
                revision=case["revision"], evidence=case["events"],
                finding="Há comissão registrada para uma venda fictícia sem confirmação independente.",
                proposed_check="Encaminhar a comissão para revisão quando faltar a confirmação sintética da venda.")

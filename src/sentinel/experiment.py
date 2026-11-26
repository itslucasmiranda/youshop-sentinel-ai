import hashlib
import json
from dataclasses import replace

from .affiliates import BASE
from .trustgraph import evaluate, scenario_events, scenarios

PROPOSAL = "synthetic-sale-evidence-v1"
FIXTURE = "venda-sem-comprovacao"


def experiment(approved=False):
    # In this training contract the sale confirmation is an independent fact.
    # All existing offers include it. The holdout fixture deliberately lacks it.
    events = scenario_events(FIXTURE, [("order_paid", 10000)])
    journey = replace(BASE, sale_confirmed=False)
    catalogue = [*scenarios(), (FIXTURE, events, journey, True)]
    baseline = evaluate(catalogue)
    revision = hashlib.sha256(json.dumps([PROPOSAL, baseline], sort_keys=True).encode()).hexdigest()
    result = {k: baseline[k] for k in ("counts", "missed_commission_minor")}
    replay = None
    if approved:
        after = evaluate(catalogue, require_confirmation=True)
        replay = {k: after[k] for k in result}
    return dict(proposal=PROPOSAL, scenario=FIXTURE, baseline=result, replay=replay,
                revision=revision, evidence=events,
                finding="Há comissão registrada para uma venda fictícia sem confirmação independente.",
                proposed_check="Encaminhar a comissão para revisão quando faltar a confirmação sintética da venda.")

"""Synthetic snapshots of a creator payout. Amounts are integer BRL cents."""
from dataclasses import replace

from .affiliates import BASE
from .trustgraph import scenario_events


# The date of each entry is when it was recorded. A scheduled transfer
# has a separate due date and only becomes paid with a settlement record.
HOLD = ("2026-01-02", "Comissão retida", "A comissão aguarda a conferência do pedido.")
RELEASE = ("2026-01-05", "Comissão liberada", "A conferência liberou o valor para repasse.")
SCHEDULE = ("2026-01-06", "Repasse agendado", "O repasse desta comissão está previsto para 08/01/2026.")
SETTLE = ("2026-01-08", "Repasse concluído", "O registro confirma o repasse simulado em 08/01/2026.")
CANCEL = ("2026-01-03", "Pedido cancelado", "A venda foi cancelada e reembolsada. A comissão foi revertida.")

SNAPSHOTS = {
    "repasse-retido": (HOLD,),
    "repasse-agendado": (HOLD, RELEASE, SCHEDULE),
    "repasse-concluido": (HOLD, RELEASE, SCHEDULE, SETTLE),
    "repasse-cancelado": (HOLD, CANCEL),
}


def orders():
    for name, steps in SNAPSHOTS.items():
        cancelled = steps[-1] == CANCEL
        entries = [("order_paid", 10000)]
        if cancelled:
            entries.append(("order_refunded", 10000))
        events = scenario_events(name, entries)
        if cancelled:
            events[-1]["occurred_at_utc"] = CANCEL[0] + "T12:00:00Z"
        yield "lab-" + name, (events, replace(BASE, posted_minor=0) if cancelled else BASE)


def timeline(order_id):
    steps = SNAPSHOTS.get(order_id.removeprefix("lab-")) if order_id.startswith("lab-") else None
    if steps is None:
        return None
    records = []
    for index, (day, label, detail) in enumerate(steps):
        records.append(dict(date=day, label=label, detail=detail,
                            id=f"{order_id}-repasse-{index}",
                            amount_minor=0 if label == CANCEL[1] else BASE.posted_minor))
    return records

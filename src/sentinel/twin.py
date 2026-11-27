"""Reproducible synthetic orders and a bounded catalogue of accounting checks."""
import hashlib
import json
import os
import re
from collections import Counter
from datetime import date, timedelta
from functools import lru_cache
from http.client import HTTPException
from itertools import combinations

from .affiliates import Journey
from .evidence import DEFAULT_MODEL, select_citations
from .trustgraph import reconcile

SIZE = 10000
PERIOD_START = date(2026, 1, 1)
PERIOD_DAYS = 90
PERIOD_END = PERIOD_START + timedelta(days=PERIOD_DAYS - 1)
SIGNALS = {"receipt": "Falta confirmação independente da venda",
           "expired": "Oferta fora da vigência na data da venda",
           "refund": "Comissão lançada após reembolso integral"}
# Only pre-approved ledger fixture transformations can be combined.
RECIPES = [()] + [(key,) for key in SIGNALS] + list(combinations(SIGNALS, 2)) + [tuple(SIGNALS)]


def fixture(index, signals=None):
    signals = RECIPES[index % len(RECIPES)] if signals is None else signals
    order = f"sim-{index:05}"
    creator = f"creator-{index % 500 + 1:03}"
    product = f"produto-{(index * 13 + index // 500) % 100 + 1:03}"
    day = PERIOD_START + timedelta(days=index % PERIOD_DAYS)
    paid = 2500 + index * 137 % 35000
    journey = Journey(creator=creator, attributed_creator=creator, buyer=f"cliente-{index:05}",
                      product=product, offer=f"oferta-{product}", link=f"link-{creator}-{product}",
                      posted_minor=paid // 10, sale_confirmed="receipt" not in signals)
    kinds = ["order_paid"]
    if "refund" in signals:
        kinds.append("order_refunded")
    events = [dict(event_id=f"{order}-{i}", order_id=order, event_type=kind,
                   amount_minor=paid, occurred_at_utc=f"{day}T12:00:0{i}Z", origin="synthetic",
                   currency="BRL", fixture_version="twin-v1") for i, kind in enumerate(kinds)]
    expiry = day + timedelta(days=-1 if "expired" in signals else 30)
    return events, journey, expiry


def lookup(order):
    if re.fullmatch(r"sim-[0-9]{5}", order) and int(order[4:]) < SIZE:
        return fixture(int(order[4:]))
    return None, None, None


def simulate(index, recipe):
    events, journey, expiry = fixture(index, recipe)
    result = reconcile(events, journey)
    return dict(order=events[0]["order_id"], signals=list(recipe), expected=bool(recipe),
                baseline=result["status"] == "revisar", receipt=not journey.sale_confirmed,
                expired=events[0]["occurred_at_utc"][:10] > expiry.isoformat())


def score(rows, checks=()):
    counts = Counter(dict(tp=0, tn=0, fp=0, fn=0))
    for row in rows:
        actual = row["baseline"] or any(row[key] for key in checks)
        counts[("tn", "fp", "fn", "tp")[2 * int(row["expected"]) + int(actual)]] += 1
    return dict(counts)


@lru_cache(maxsize=1)
def summary():
    rows = [simulate(i, RECIPES[i % len(RECIPES)]) for i in range(SIZE)]
    return dict(orders=len(rows), creators=500, products=100, days=PERIOD_DAYS, counts=score(rows))


def payout_history(events, journey, expiry, case):
    """Fictional settlement calendar as of the final day of the simulation."""
    order = events[0]["order_id"]
    sale = date.fromisoformat(events[0]["occurred_at_utc"][:10])
    records = []

    def record(day, label, detail):
        records.append(dict(date=day.isoformat(), label=label, detail=detail,
                            id=f"{order}-repasse-{len(records)}", amount_minor=journey.posted_minor))

    reasons = []
    if case["status"] == "revisar":
        reasons.append("a conferência financeira sinalizou o pedido")
    if not journey.sale_confirmed:
        reasons.append("falta confirmação independente da venda")
    if sale > expiry:
        reasons.append("a oferta venceu antes da venda")
    if reasons:
        record(sale, "Comissão retida", "O calendário fictício reteve a comissão porque " + " e ".join(reasons) + ".")
        return records

    release = sale + timedelta(days=3)
    transfer = sale + timedelta(days=7)
    record(sale, "Comissão retida", "Início da espera de três dias prevista no calendário fictício.")
    if release <= PERIOD_END:
        record(release, "Repasse agendado", f"A comissão foi liberada para repasse em {transfer:%d/%m/%Y}.")
    if transfer <= PERIOD_END:
        record(transfer, "Repasse concluído", f"O simulador registra a transferência em {transfer:%d/%m/%Y}.")
    return records


def creator_orders(number):
    rows = []
    for i in range(number - 1, SIZE, 500):
        events, journey, expiry = fixture(i)
        case = reconcile(events, journey)
        latest = payout_history(events, journey, expiry, case)[-1]
        rows.append(dict(order=events[0]["order_id"], date=events[0]["occurred_at_utc"][:10],
                         expected=case["attribution"]["expected_minor"], posted=journey.posted_minor,
                         status=case["status"], payout_status=latest["label"], payout_date=latest["date"]))
    return rows


def recipe_catalogue():
    return {"combinacao-" + str(i): " + ".join(SIGNALS[k] for k in recipe) or "Venda regular"
            for i, recipe in enumerate(RECIPES)}


def plan():
    catalogue = recipe_catalogue()
    # Prioritize combinations that expose baseline misses, with a regular control.
    ranked = sorted(range(1, len(RECIPES)), key=lambda i: (
        simulate(i, RECIPES[i])["baseline"], -len(RECIPES[i]), i))
    chosen = ["combinacao-" + str(i) for i in ranked[:3]]
    source = "prioridade por divergências"
    if os.getenv("SENTINEL_LOCAL_AI") == "1":
        try:
            ids = select_citations("Escolha combinações distintas para testar revisão de comissões.",
                                   catalogue, os.getenv("SENTINEL_OLLAMA_MODEL") or DEFAULT_MODEL)
            if any(key != "combinacao-0" for key in ids):
                chosen = list(dict.fromkeys([*(key for key in ids if key != "combinacao-0"), *chosen]))[:3]
                source = "seleção por Ollama local"
        except (ValueError, OSError, HTTPException):
            source = "prioridade local após falha do modelo"
    keys = ["combinacao-0", *chosen]
    return dict(source=source, cases=[dict(description=catalogue[key], **simulate(i, RECIPES[i]))
                                     for key in keys for i in [int(key.split("-")[1])]])


def proposals(approved=False):
    rows = [simulate(i, RECIPES[i % len(RECIPES)]) for i in range(50)]
    discovery, validation = rows[:25], rows[25:]
    before = score(discovery)
    found = []
    for key in ("receipt", "expired"):
        if score(discovery, [key])["fn"] < before["fn"]:
            found.append(key)
    revision = hashlib.sha256(json.dumps([rows, found, SIGNALS], sort_keys=True).encode()).hexdigest()
    return dict(revision=revision, checks=[SIGNALS[k] for k in found], baseline=score(validation),
                discovery_size=len(discovery), validation_size=len(validation)), score(validation, found) if approved else None


"""Score fixed Portuguese evidence questions against explicit synthetic labels."""

import argparse
import json
import sqlite3
from contextlib import closing
from http.client import HTTPConnection, HTTPException
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from sentinel.data import seed_demo
from sentinel.evidence import DEFAULT_MODEL, explain
from sentinel.trustgraph import reconcile, scenarios


LAB_ORDER = "lab-comissao-apos-reembolso"
LABELS = (
    ("commission_review", LAB_ORDER, "Por que a comissão ficou em revisão após o reembolso do pedido?",
     ("synthetic-offer-v1", f"{LAB_ORDER}-1"), ("prevê 0 centavos", "registrou 1000 centavos")),
    ("lab_refund", LAB_ORDER, "Qual evento comprova o reembolso do pedido?",
     (f"{LAB_ORDER}-1",), ("10000 centavos",)),
    ("demo_refund", "demo-order-1", "Qual evento confirma o estorno?",
     ("demo-refund-1",), ("10000 centavos",)),
    ("withdrawal_date", LAB_ORDER, "Qual é a data do próximo saque deste pedido?",
     (), ("Não há evidência local", "data do próximo saque")),
    ("refund_guide", "demo-order-1", "Como solicitar reembolso pelo relatório?",
     ("YS-REFUND-01",), ()),
    ("payment_event", "demo-order-1", "Qual evento confirma o pagamento do pedido?",
     ("demo-paid-1",), ("10000 centavos",)),
    ("missing_refund", "lab-venda", "Qual evento confirma o reembolso?",
     (), ("As evidências locais não respondem",)),
)


def installed_models():
    connection = HTTPConnection("127.0.0.1", 11434, timeout=5)
    try:
        connection.request("GET", "/api/tags")
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError(f"Ollama HTTP {response.status}")
        return {entry["name"] for entry in json.load(response)["models"]}
    finally:
        connection.close()


def run(live=False):
    cases = {f"lab-{name}": reconcile(events, journey) for name, events, journey, _ in scenarios()}
    with TemporaryDirectory() as temporary:
        path = Path(temporary) / "evaluation.sqlite3"
        seed_demo(path)
        with closing(sqlite3.connect(path)) as db:
            db.row_factory = sqlite3.Row
            events = db.execute("SELECT * FROM synthetic_events WHERE order_id = ?", ("demo-order-1",))
            cases["demo-order-1"] = reconcile([dict(event) for event in events])

    models = []
    skipped = {}
    if live:
        requested = (DEFAULT_MODEL, "qwen3:4b")
        try:
            installed = installed_models()
        except (OSError, HTTPException, ValueError, KeyError, TypeError) as error:
            skipped.update(dict.fromkeys(requested, str(error)))
        else:
            for model in requested:
                if model in installed or f"{model}:latest" in installed:
                    models.append(model)
                else:
                    skipped[model] = "Model absent from the local Ollama inventory."

    methods = {}
    for model in (None, *models):
        rows = []
        for name, order, question, expected, text in LABELS:
            start = perf_counter()
            answer = explain(cases[order], question, use_model=model is not None, model=model)
            elapsed = perf_counter() - start
            actual = set(answer["citation_ids"])
            gold = set(expected)
            abstained = answer["mode"] == "evidencia_insuficiente"
            rendered = " ".join((answer["message"], answer.get("case_finding", "")))
            rows.append(dict(case=name, order_id=order, seconds=round(elapsed, 4),
                             expected_citations=expected, citations=answer["citation_ids"],
                             precision=len(actual & gold) / len(actual) if actual else None,
                             recall=len(actual & gold) / len(gold) if gold else None,
                             abstained=abstained, generation=answer.get("generation_status", "not_called"),
                             model_citations=answer.get("model_citation_ids"),
                             passed=(actual == gold and abstained == (not gold)
                                     and all(fragment in rendered for fragment in text))))
        methods[model or "deterministic"] = dict(
            source="live_ollama" if model else "deterministic", cases=rows,
            passed=sum(row["passed"] for row in rows),
            generation_errors=sum(row["generation"] == "error" for row in rows),
            model_exact_matches=sum(row["model_citations"] is not None
                                    and set(row["model_citations"]) == set(row["expected_citations"])
                                    for row in rows),
        )
    return dict(suite="evidence-retrieval-v2", skipped_models=skipped, methods=methods)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Also evaluate installed local Ollama models.")
    args = parser.parse_args()
    print(json.dumps(run(live=args.live), indent=2))

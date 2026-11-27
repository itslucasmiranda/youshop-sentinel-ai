import os
import sqlite3
from contextlib import closing
from http.client import HTTPException as TransportError
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, StringConstraints

from . import twin
from .data import SCHEMA
from .evidence import explain
from .experiment import PROPOSAL, experiment
from .trustgraph import evaluate, reconcile, scenarios

router = APIRouter(prefix="/api")
LAB = {f"lab-{name}": (events, journey) for name, events, journey, _ in scenarios()}
REVIEWS = """
CREATE TABLE IF NOT EXISTS case_reviews (
    order_id TEXT NOT NULL, revision TEXT NOT NULL, decision TEXT NOT NULL,
    reviewer TEXT NOT NULL, note TEXT NOT NULL,
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(order_id, revision)
)
"""


def database():
    path = Path(os.getenv("SENTINEL_DB", "sentinel-demo.sqlite3"))
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute(SCHEMA)
    db.execute(REVIEWS)
    db.execute("""CREATE TABLE IF NOT EXISTS experiment_reviews (
        proposal TEXT NOT NULL, revision TEXT NOT NULL, decision TEXT NOT NULL, reviewer TEXT NOT NULL,
        note TEXT NOT NULL, recorded_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(proposal,revision))""")
    return db


def case_details(db, order_id):
    events, journey = LAB.get(order_id, (None, None))
    expiry = None
    if events is None:
        events, journey, expiry = twin.lookup(order_id)
    if events is None:
        events = [dict(row) for row in db.execute(
            "SELECT * FROM synthetic_events WHERE order_id = ?", (order_id,))]
    if not events:
        raise HTTPException(404, "Pedido ausente.")
    case = reconcile(events, journey)
    if expiry is not None:
        sale = events[0]["occurred_at_utc"][:10]
        checks = {}
        if sale > expiry.isoformat():
            checks["offer"] = (f"A oferta venceu em {expiry:%d/%m/%Y}. "
                               f"A venda ocorreu em {'/'.join(reversed(sale.split('-')))}.")
        if not journey.sale_confirmed:
            checks["confirmation"] = "Existe um evento de pagamento, mas falta a confirmação independente da venda."
        case["lab_checks"] = checks
    review = db.execute("SELECT * FROM case_reviews WHERE order_id=? AND revision=?",
                        (order_id, case["revision"])).fetchone()
    return dict(**case, order_id=order_id, review=dict(review) if review else None)


@router.get("/orders")
def orders():
    with closing(database()) as db:
        ids = {r[0] for r in db.execute("SELECT DISTINCT order_id FROM synthetic_events")}
        return sorted(ids | LAB.keys())


@router.get("/orders/{order_id}")
def order(order_id: str):
    with closing(database()) as db:
        return case_details(db, order_id)


class Review(BaseModel):
    revision: str = Field(pattern="^[0-9a-f]{64}$")
    reviewer: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    decision: Literal["confirmado", "descartado"]
    note: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


@router.post("/orders/{order_id}/review")
def review(order_id: str, body: Review):
    with closing(database()) as db, db:
        db.execute("BEGIN IMMEDIATE")
        case = case_details(db, order_id)
        if case["status"] != "revisar" or case["revision"] != body.revision:
            raise HTTPException(409, "Caso indisponível para esta revisão.")
        existing = case["review"]
        if existing:
            if any(existing[k] != v for k, v in body.model_dump().items()):
                raise HTTPException(409, "Já existe uma decisão para estas evidências.")
            return existing
        db.execute("INSERT INTO case_reviews(order_id,revision,decision,reviewer,note) "
                   "VALUES (?,?,?,?,?)", (order_id, body.revision, body.decision, body.reviewer, body.note))
        return case_details(db, order_id)["review"]


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=400)


@router.post("/orders/{order_id}/explanation")
def explanation(order_id: str, body: Question):
    case = order(order_id)
    try:
        return explain(case, body.question)
    except (ValueError, OSError, TransportError):
        raise HTTPException(503, "O modelo local não conseguiu gerar a explicação.")


@router.get("/validation")
def validation():
    return evaluate()


@router.get("/experiment")
def read_experiment():
    with closing(database()) as db:
        row = db.execute("SELECT * FROM experiment_reviews WHERE proposal=? AND revision=?",
                         (PROPOSAL, experiment()["revision"])).fetchone()
        return dict(**experiment(bool(row and row["decision"] == "confirmado")),
                    review=dict(row) if row else None)


@router.post("/experiment/review")
def review_experiment(body: Review):
    if body.revision != experiment()["revision"]:
        raise HTTPException(409, "A evidência do experimento mudou.")
    record_decision(PROPOSAL, body)
    return read_experiment()


def record_decision(proposal, body):
    with closing(database()) as db, db:
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute("SELECT decision,reviewer,note FROM experiment_reviews WHERE proposal=? AND revision=?",
                              (proposal, body.revision)).fetchone()
        values = (body.decision, body.reviewer, body.note)
        if existing and tuple(existing) != values:
            raise HTTPException(409, "Esta proposta já foi revisada.")
        if not existing:
            db.execute("INSERT INTO experiment_reviews(proposal,revision,decision,reviewer,note) VALUES (?,?,?,?,?)",
                       (proposal, body.revision, *values))


@router.get("/twin")
def twin_summary():
    return twin.summary()


@router.get("/twin/creators/{number}")
def creator(number: Annotated[int, Field(ge=1, le=500)]):
    return twin.creator_orders(number)


@router.post("/twin/plan")
def generate_plan():
    return twin.plan()


@router.get("/twin/proposals")
def read_proposals():
    result, _ = twin.proposals()
    with closing(database()) as db:
        decision = db.execute("SELECT decision FROM experiment_reviews WHERE proposal=? AND revision=?",
                              ("twin-v1", result["revision"])).fetchone()
    return dict(**result, decision=decision[0] if decision else None,
                replay=twin.proposals(approved=True)[1] if decision and decision[0] == "confirmado" else None)


@router.post("/twin/proposals/review")
def review_proposals(body: Review):
    result, _ = twin.proposals()
    if body.revision != result["revision"]:
        raise HTTPException(409, "A simulação mudou.")
    record_decision("twin-v1", body)
    return read_proposals()

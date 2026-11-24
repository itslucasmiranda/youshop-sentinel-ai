import os
import sqlite3
from contextlib import closing
from http.client import HTTPException as TransportError
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, StringConstraints

from .data import SCHEMA
from .evidence import explain
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
    return db


def case_details(db, order_id):
    events, journey = LAB.get(order_id, (None, None))
    if events is None:
        events = [dict(row) for row in db.execute(
            "SELECT * FROM synthetic_events WHERE order_id = ?", (order_id,))]
    if not events:
        raise HTTPException(404, "Pedido ausente.")
    case = reconcile(events, journey)
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
    evidence = {k: v for k, v in case.items() if k != "review"}
    try:
        return explain(evidence, body.question)
    except (ValueError, OSError, TransportError):
        raise HTTPException(503, "O modelo local não conseguiu gerar a explicação.")


@router.get("/validation")
def validation():
    return evaluate()
